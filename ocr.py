import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

OCR_API_URL = "https://api.opentyphoon.ai/v1/ocr"
DEFAULT_MODEL = "typhoon-ocr"
DEFAULT_TASK_TYPE = "default"
DEFAULT_MAX_TOKENS = 16000
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TOP_P = 0.6
DEFAULT_REPETITION_PENALTY = 1.1
DEFAULT_TIMEOUT = 120


class OCRClientError(Exception):
    def __init__(self, message: str, kind: str = "upstream", details: Any = None):
        super().__init__(message)
        self.kind = kind
        self.details = details



def _extract_content_text(page_result: dict[str, Any]) -> str:
    try:
        content = page_result["message"]["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""

    if not isinstance(content, str):
        return str(content)

    try:
        parsed_content = json.loads(content)
        if isinstance(parsed_content, dict) and "natural_text" in parsed_content:
            natural_text = parsed_content.get("natural_text")
            if natural_text is not None:
                return str(natural_text)
    except json.JSONDecodeError:
        pass

    return content



def extract_text_from_result(payload: dict[str, Any]) -> str:
    extracted_texts: list[str] = []
    for page_result in payload.get("results", []):
        text = _extract_content_text(page_result)
        if text:
            extracted_texts.append(text)
    return "\n".join(extracted_texts)



def run_ocr_request(
    image_path: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    task_type: str = DEFAULT_TASK_TYPE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    repetition_penalty: float = DEFAULT_REPETITION_PENALTY,
    pages: list[int] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    if not api_key:
        raise OCRClientError("TYPHOON_API_KEY is not set", kind="config")

    image_file = Path(image_path)
    if not image_file.exists() or not image_file.is_file():
        raise OCRClientError(f"Image file not found: {image_path}", kind="client")

    data: dict[str, str] = {
        "model": model,
        "task_type": task_type,
        "max_tokens": str(max_tokens),
        "temperature": str(temperature),
        "top_p": str(top_p),
        "repetition_penalty": str(repetition_penalty),
    }
    if pages is not None:
        data["pages"] = json.dumps(pages)

    try:
        with open(image_file, "rb") as file_obj:
            response = requests.post(
                OCR_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files={
                    "file": (
                        image_file.name,
                        file_obj,
                        "application/octet-stream",
                    )
                },
                timeout=timeout,
            )
    except requests.RequestException as exc:
        raise OCRClientError("OCR request failed", kind="upstream", details=str(exc)) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise OCRClientError(
            "Invalid OCR response",
            kind="upstream",
            details=response.text,
        ) from exc

    if not response.ok:
        raise OCRClientError("OCR failed", kind="upstream", details=payload)

    return payload



def extract_text_from_image(
    image_path: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    task_type: str = DEFAULT_TASK_TYPE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    repetition_penalty: float = DEFAULT_REPETITION_PENALTY,
    pages: list[int] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    payload = run_ocr_request(
        image_path=image_path,
        api_key=api_key,
        model=model,
        task_type=task_type,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        pages=pages,
        timeout=timeout,
    )
    return extract_text_from_result(payload)



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Typhoon OCR on an image file")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("--api-key", default=os.getenv("TYPHOON_API_KEY"), help="Typhoon API key")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--task-type", default=DEFAULT_TASK_TYPE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--repetition-penalty", type=float, default=DEFAULT_REPETITION_PENALTY)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return parser



def main() -> int:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args()

    try:
        text = extract_text_from_image(
            image_path=args.image_path,
            api_key=args.api_key,
            model=args.model,
            task_type=args.task_type,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
            timeout=args.timeout,
        )
        print(text or "")
        return 0
    except OCRClientError as exc:
        print(f"Error: {exc}")
        if exc.details:
            print(exc.details)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
