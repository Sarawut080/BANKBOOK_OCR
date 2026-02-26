from app.services.ocr_service import (
    OCRClientError,
    extract_text_from_image,
    extract_text_from_result,
    format_ocr_output,
    main,
    run_ocr_request,
)

__all__ = [
    "OCRClientError",
    "extract_text_from_image",
    "extract_text_from_result",
    "format_ocr_output",
    "run_ocr_request",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
