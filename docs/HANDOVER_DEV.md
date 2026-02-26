# Developer Handover Guide

Last updated: 2026-02-24  
Stable local commit: `e582555`  
Main branch: `main`

## 1) Project Summary

This project is a Flask-based OCR web app for bankbook image text extraction using Typhoon OCR API.

- Backend: `app.py` (Flask API + static page serving)
- OCR client: `ocr.py` (HTTP client to Typhoon OCR)
- Frontend: `index.html` (simple upload UI)
- Tests: `tests/`

## 2) Prerequisites

- Python `3.12.x` (verified: `3.12.6`)
- Internet access for calling Typhoon OCR API
- Valid Typhoon API key

## 3) Environment Variables

Copy `.env.example` to `.env` and set your key:

```bash
cp .env.example .env
```

Required variables:

- `TYPHOON_API_KEY`: API key for `https://api.opentyphoon.ai/v1/ocr`

Notes:

- Do not commit `.env` (already ignored in `.gitignore`).
- Use secret manager / secure channel for sharing real keys.

## 4) Install & Run (Local)

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run app:

```bash
python app.py
```

Default server:

- URL: `http://127.0.0.1:5000`
- OCR endpoint: `POST /ocr` (multipart field: `image`)
- Max upload size: `10 MB`
- Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`

## 5) Test Commands

Run all tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -q
```

Current baseline:

- `12` tests passing (last verified on 2026-02-24)

## 6) Key Files and Responsibilities

- `app.py`
  - Serves `index.html` on `/`
  - Accepts image upload on `/ocr`
  - Validates file type and handles temporary file lifecycle
  - Maps OCR errors to HTTP status:
    - `config` -> `500`
    - `client` -> `400`
    - `upstream` -> `502`

- `ocr.py`
  - Builds request payload for Typhoon OCR
  - Calls external API with timeout handling
  - Parses OCR response and extracts text
  - Provides CLI usage:
    - `python ocr.py <image_path> --api-key <key>`

- `index.html`
  - Minimal web UI for image upload and displaying OCR result

- `tests/test_app.py`
  - API behavior tests for `/ocr`

- `tests/test_ocr.py`
  - OCR parsing and error-path unit tests

## 7) Common Issues & Quick Fix

- Error: `TYPHOON_API_KEY is not set`
  - Cause: missing/empty env var
  - Fix: set `TYPHOON_API_KEY` in `.env`, then restart app

- Error: `Unsupported file type`
  - Cause: extension not in allowlist
  - Fix: convert image to supported extension

- Error: upstream timeout / OCR failed (`502`)
  - Cause: network issue or Typhoon API issue
  - Fix: retry, check internet and API status, inspect response details

- Tests show `Ran 0 tests`
  - Cause: wrong unittest command
  - Fix: use discovery command from section 5

## 8) Security and Git Notes

- `.env` must never be committed.
- History was rewritten to remove a past commit containing `.env`.
- If pushing rewritten history to remote is needed:

```bash
git push --force-with-lease origin main
```

Use this only when coordinated with collaborators.

## 9) Handover Checklist

- [ ] New developer can install dependencies successfully
- [ ] `.env` configured with valid `TYPHOON_API_KEY`
- [ ] App starts and `/` is reachable
- [ ] OCR flow works with a sample image
- [ ] Test suite passes
- [ ] Developer understands key files (`app.py`, `ocr.py`, `tests/`)
- [ ] No secrets committed in git

## 10) First Tasks for Next Developer

1. Add structured logging for OCR request failures.
2. Add integration test with mocked API response fixtures.
3. Add production-ready WSGI entrypoint and deployment doc (Gunicorn/Uvicorn + reverse proxy).
