import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageFile, ImageOps
except ImportError:  # pragma: no cover - optional dependency fallback
    Image = None
    ImageFile = None
    ImageOps = None


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return Path(filename).suffix.lower() in allowed_extensions


def optimize_image_for_ocr(image_path: str, max_image_side: int, jpeg_quality: int) -> str:
    if Image is None or ImageOps is None:
        return image_path

    if ImageFile is not None:
        ImageFile.LOAD_TRUNCATED_IMAGES = True

    source = Path(image_path)
    source_suffix = source.suffix.lower()

    try:
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
            largest_side = max(width, height)
            should_resize = largest_side > max_image_side
            should_convert = source_suffix not in {".jpg", ".jpeg"}

            if not should_resize and not should_convert:
                return image_path

            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")

            if should_resize:
                scale = max_image_side / float(largest_side)
                new_size = (
                    max(1, int(round(width * scale))),
                    max(1, int(round(height * scale))),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as out_file:
                img.save(out_file.name, format="JPEG", quality=jpeg_quality, optimize=True)
                return out_file.name
    except Exception:
        # If preprocessing fails (e.g. truncated image), continue with original file.
        return image_path


def repair_image_for_ocr(image_path: str) -> str:
    if Image is None or ImageOps is None:
        return image_path

    if ImageFile is not None:
        ImageFile.LOAD_TRUNCATED_IMAGES = True

    source = Path(image_path)
    try:
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as out_file:
                img.save(out_file.name, format="JPEG", quality=90, optimize=False)
                return out_file.name
    except Exception:
        return image_path


def is_truncated_image_error(details: object) -> bool:
    text = str(details).lower()
    return "truncated" in text and "image" in text
