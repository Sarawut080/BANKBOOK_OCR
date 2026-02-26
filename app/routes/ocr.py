import os
import tempfile
import traceback
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from app.services.image_service import (
    allowed_file,
    is_truncated_image_error,
    optimize_image_for_ocr,
    repair_image_for_ocr,
)
from app.services.ocr_service import (
    OCRClientError,
    extract_text_from_result,
    format_ocr_output,
    run_ocr_request,
)

bp = Blueprint("ocr", __name__)


@bp.post("/ocr")
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    image = request.files["image"]
    if not image.filename:
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(image.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "Unsupported file type"}), 400

    suffix = Path(image.filename).suffix or ".jpg"
    temp_path = None
    optimized_path = None
    repaired_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            image.save(temp_file.name)
            temp_path = temp_file.name

        optimized_path = optimize_image_for_ocr(
            image_path=temp_path,
            max_image_side=current_app.config["OCR_MAX_IMAGE_SIDE"],
            jpeg_quality=current_app.config["OCR_JPEG_QUALITY"],
        )

        try:
            payload = run_ocr_request(
                image_path=optimized_path,
                api_key=os.getenv("TYPHOON_API_KEY", ""),
                timeout=current_app.config["OCR_READ_TIMEOUT"],
                connect_timeout=current_app.config["OCR_CONNECT_TIMEOUT"],
                retries=current_app.config["OCR_RETRIES"],
            )
        except OCRClientError as exc:
            if not is_truncated_image_error(exc.details):
                raise
            repaired_path = repair_image_for_ocr(temp_path)
            if repaired_path == temp_path:
                raise
            payload = run_ocr_request(
                image_path=repaired_path,
                api_key=os.getenv("TYPHOON_API_KEY", ""),
                timeout=current_app.config["OCR_READ_TIMEOUT"],
                connect_timeout=current_app.config["OCR_CONNECT_TIMEOUT"],
                retries=current_app.config["OCR_RETRIES"],
            )

        raw_text = extract_text_from_result(payload)
        if not raw_text.strip() and optimized_path != temp_path:
            payload = run_ocr_request(
                image_path=temp_path,
                api_key=os.getenv("TYPHOON_API_KEY", ""),
                timeout=current_app.config["OCR_READ_TIMEOUT"],
                connect_timeout=current_app.config["OCR_CONNECT_TIMEOUT"],
                retries=current_app.config["OCR_RETRIES"],
            )
            raw_text = extract_text_from_result(payload)

        response_data = {"formatted_text": format_ocr_output(raw_text)}
        if request.args.get("debug") == "1":
            response_data["raw_text"] = raw_text
            response_data["payload"] = payload

        return jsonify(response_data)
    except OCRClientError as exc:
        status_code = 502
        if exc.kind == "client":
            status_code = 400
        elif exc.kind == "config":
            status_code = 500
        return jsonify({"error": str(exc), "details": exc.details}), status_code
    except Exception as exc:  # pragma: no cover - defensive fallback for unexpected errors
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(exc)}), 500
    finally:
        if repaired_path and repaired_path not in {temp_path, optimized_path} and os.path.exists(repaired_path):
            os.remove(repaired_path)
        if optimized_path and optimized_path != temp_path and os.path.exists(optimized_path):
            os.remove(optimized_path)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
