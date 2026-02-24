import io
import unittest
from unittest.mock import patch

from app import app
from ocr import OCRClientError


class TestAppOCRRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_no_file_returns_400(self):
        response = self.client.post("/ocr", data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "No file uploaded")

    def test_unsupported_extension_returns_400(self):
        data = {"image": (io.BytesIO(b"fake"), "file.txt")}
        response = self.client.post("/ocr", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Unsupported file type")

    @patch("app.run_ocr_request")
    def test_missing_api_key_returns_500(self, mock_run):
        mock_run.side_effect = OCRClientError("TYPHOON_API_KEY is not set", kind="config")
        data = {"image": (io.BytesIO(b"fake"), "file.jpg")}
        response = self.client.post("/ocr", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"], "TYPHOON_API_KEY is not set")

    @patch("app.run_ocr_request")
    def test_upstream_error_returns_502(self, mock_run):
        mock_run.side_effect = OCRClientError("OCR failed", kind="upstream", details={"x": "y"})
        data = {"image": (io.BytesIO(b"fake"), "file.jpg")}
        response = self.client.post("/ocr", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "OCR failed")

    @patch("app.run_ocr_request")
    def test_success_returns_payload(self, mock_run):
        mock_payload = {
            "results": [
                {"message": {"choices": [{"message": {"content": "hello"}}]}}
            ]
        }
        mock_run.return_value = mock_payload
        data = {"image": (io.BytesIO(b"fake"), "file.jpg")}
        response = self.client.post("/ocr", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), mock_payload)


if __name__ == "__main__":
    unittest.main()
