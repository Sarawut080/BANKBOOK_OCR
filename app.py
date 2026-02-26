import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from ocr import OCRClientError, extract_text_from_result, format_ocr_output, run_ocr_request

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional dependency fallback
    Image = None
    ImageOps = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
OCR_MAX_IMAGE_SIDE = 1800
OCR_JPEG_QUALITY = 75
OCR_CONNECT_TIMEOUT = 10.0
OCR_READ_TIMEOUT = 120
OCR_RETRIES = 1

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _optimize_image_for_ocr(image_path: str) -> str:
    if Image is None or ImageOps is None:
        return image_path

    source = Path(image_path)
    source_suffix = source.suffix.lower()

    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        largest_side = max(width, height)
        should_resize = largest_side > OCR_MAX_IMAGE_SIDE
        should_convert = source_suffix not in {".jpg", ".jpeg"}

        if not should_resize and not should_convert:
            return image_path

        if img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        if should_resize:
            scale = OCR_MAX_IMAGE_SIDE / float(largest_side)
            new_size = (
                max(1, int(round(width * scale))),
                max(1, int(round(height * scale))),
            )
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as out_file:
            img.save(out_file.name, format="JPEG", quality=OCR_JPEG_QUALITY, optimize=True)
            return out_file.name


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/ocr")
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    image = request.files["image"]
    if not image.filename:
        return jsonify({"error": "Empty filename"}), 400

    if not _allowed_file(image.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    suffix = Path(image.filename).suffix or ".jpg"
    temp_path = None
    optimized_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            image.save(temp_file.name)
            temp_path = temp_file.name

        optimized_path = _optimize_image_for_ocr(temp_path)

        payload = run_ocr_request(
            image_path=optimized_path,
            api_key=os.getenv("TYPHOON_API_KEY", ""),
            timeout=OCR_READ_TIMEOUT,
            connect_timeout=OCR_CONNECT_TIMEOUT,
            retries=OCR_RETRIES,
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
    finally:
        if optimized_path and optimized_path != temp_path and os.path.exists(optimized_path):
            os.remove(optimized_path)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
