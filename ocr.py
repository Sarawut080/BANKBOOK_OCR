import argparse
import html
import json
import os
import re
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
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_RETRIES = 1
HTTP_SESSION = requests.Session()


class OCRClientError(Exception):
    def __init__(self, message: str, kind: str = "upstream", details: Any = None):
        super().__init__(message)
        self.kind = kind
        self.details = details


def _normalize_line_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_html_tags(text: str) -> str:
    return re.sub(r"(?is)<[^>]+>", " ", text)


def _format_table_html(text: str) -> str:
    def replace_table(match: re.Match[str]) -> str:
        table_html = match.group(0)
        row_matches = re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", table_html)
        rows: list[str] = []

        for row_html in row_matches:
            cell_matches = re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", row_html)
            cells: list[str] = []
            for cell in cell_matches:
                clean_cell = html.unescape(_strip_html_tags(cell))
                clean_cell = _normalize_line_spaces(clean_cell)
                if clean_cell:
                    cells.append(clean_cell)
            if cells:
                rows.append(" | ".join(cells))

        return "\n".join(rows)

    return re.sub(r"(?is)<table\b[^>]*>.*?</table>", replace_table, text)


def format_ocr_output(text: str) -> str:
    formatted = _format_table_html(text)
    formatted = re.sub(r"(?is)<br\s*/?>", "\n", formatted)
    formatted = re.sub(r"(?is)</p\s*>", "\n", formatted)
    formatted = re.sub(r"(?is)</div\s*>", "\n", formatted)
    formatted = html.unescape(_strip_html_tags(formatted))

    lines = [_normalize_line_spaces(line) for line in formatted.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


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
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
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

    response = None
    timeout_tuple = (connect_timeout, timeout)
    attempts = max(1, retries + 1)
    last_error: requests.RequestException | None = None

    for attempt in range(attempts):
        try:
            with open(image_file, "rb") as file_obj:
                response = HTTP_SESSION.post(
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
                    timeout=timeout_tuple,
                )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < attempts - 1:
                continue
            raise OCRClientError("OCR request failed", kind="upstream", details=str(exc)) from exc

        if response.status_code >= 500 and attempt < attempts - 1:
            continue
        break

    if response is None:
        detail = str(last_error) if last_error else "No response"
        raise OCRClientError("OCR request failed", kind="upstream", details=detail)

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
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
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
        connect_timeout=connect_timeout,
        retries=retries,
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
    parser.add_argument("--connect-timeout", type=float, default=DEFAULT_CONNECT_TIMEOUT)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
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
            connect_timeout=args.connect_timeout,
            retries=args.retries,
        )
        print(format_ocr_output(text or ""))
        return 0
    except OCRClientError as exc:
        print(f"Error: {exc}")
        if exc.details:
            print(exc.details)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
