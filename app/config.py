class Config:
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

    OCR_MAX_IMAGE_SIDE = 1800
    OCR_JPEG_QUALITY = 75
    OCR_CONNECT_TIMEOUT = 10.0
    OCR_READ_TIMEOUT = 120
    OCR_RETRIES = 1
