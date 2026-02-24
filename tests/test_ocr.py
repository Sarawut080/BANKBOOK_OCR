import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from ocr import OCRClientError, extract_text_from_result, run_ocr_request


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", raise_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self._raise_json = raise_json

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._raise_json:
            raise ValueError("invalid json")
        return self._json_data


class TestOCRParsing(unittest.TestCase):
    def test_extract_plain_text(self):
        payload = {
            "results": [
                {
                    "message": {
                        "choices": [
                            {"message": {"content": "hello world"}}
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_text_from_result(payload), "hello world")

    def test_extract_natural_text_from_json_string(self):
        payload = {
            "results": [
                {
                    "message": {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps({"natural_text": "thai text"})
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_text_from_result(payload), "thai text")

    def test_extract_non_json_string(self):
        payload = {
            "results": [
                {
                    "message": {
                        "choices": [
                            {"message": {"content": "{not-json"}}
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_text_from_result(payload), "{not-json")


class TestOCRRequest(unittest.TestCase):
    def test_invalid_json_response_raises(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
            image_path = temp.name
        try:
            with patch("ocr.requests.post", return_value=FakeResponse(200, raise_json=True, text="oops")):
                with self.assertRaises(OCRClientError) as ctx:
                    run_ocr_request(image_path=image_path, api_key="test-key")
                self.assertEqual(ctx.exception.kind, "upstream")
        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_non_200_raises(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
            image_path = temp.name
        try:
            with patch("ocr.requests.post", return_value=FakeResponse(500, json_data={"error": "bad"})):
                with self.assertRaises(OCRClientError) as ctx:
                    run_ocr_request(image_path=image_path, api_key="test-key")
                self.assertEqual(ctx.exception.kind, "upstream")
        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_missing_api_key_raises_config(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
            image_path = temp.name
        try:
            with self.assertRaises(OCRClientError) as ctx:
                run_ocr_request(image_path=image_path, api_key="")
            self.assertEqual(ctx.exception.kind, "config")
        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_network_error_raises(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
            image_path = temp.name
        try:
            with patch("ocr.requests.post", side_effect=requests.Timeout("timeout")):
                with self.assertRaises(OCRClientError) as ctx:
                    run_ocr_request(image_path=image_path, api_key="test-key")
                self.assertEqual(ctx.exception.kind, "upstream")
        finally:
            Path(image_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
