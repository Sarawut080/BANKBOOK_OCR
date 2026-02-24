import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from ocr import OCRClientError, run_ocr_request

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


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

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            image.save(temp_file.name)
            temp_path = temp_file.name

        payload = run_ocr_request(
            image_path=temp_path,
            api_key=os.getenv("TYPHOON_API_KEY", ""),
        )
        return jsonify(payload)
    except OCRClientError as exc:
        status_code = 502
        if exc.kind == "client":
            status_code = 400
        elif exc.kind == "config":
            status_code = 500
        return jsonify({"error": str(exc), "details": exc.details}), status_code
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
