# BANKBOOK_OCR

Typhoon OCR web app built with Flask.

## Project Structure

```text
app/
  __init__.py              # Flask app factory
  config.py                # Central app config
  routes/
    web.py                 # Web page route
    ocr.py                 # OCR API route
  services/
    image_service.py       # Image optimize/repair helpers
    ocr_service.py         # OCR client + text extraction/formatting
  templates/
    index.html             # Main UI
  static/
    app.js                 # Frontend logic
    styles.css             # Frontend styles
app.py                     # Runtime entrypoint
ocr.py                     # Backward-compatible OCR module wrapper
```

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.env`:

```env
TYPHOON_API_KEY=your_api_key_here
```

3. Start server:

```bash
python app.py
```

4. Open browser:

`http://localhost:5000`
