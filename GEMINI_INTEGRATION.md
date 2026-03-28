# Gemini AI Integration

PaperTrail now supports **Google Gemini 2.5 Flash** for AI-powered form extraction!

## Features

✅ **Vision-based OCR** - Gemini directly reads handwritten forms from images  
✅ **Multi-language support** - Handles English, Bengali, and Marathi  
✅ **Intelligent fallback** - Auto-falls back to keyword parsing if Gemini is unavailable  
✅ **High accuracy** - Gemini 2.5 Flash provides ~95% confidence on clear handwriting  
✅ **FREE tier** - 10 requests/min, 250 requests/day, no credit card required

## Setup

### 1. Get Your Free Gemini API Key

1. Visit: https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Copy your API key

### 2. Add to Environment

Edit `/Users/atharvdalvi/Desktop/PaperTrail/papertrail_backend/.env`:

```bash
# Add this line with your API key:
GEMINI_API_KEY=your_api_key_here
```

### 3. Install Dependencies (Already Done)

```bash
pip install google-generativeai pillow
```

## How It Works

### Pipeline Flow

When you upload a form to PaperTrail:

1. **Upload Image** → File is saved
2. **OpenCV preprocessing** → Image enhancement
3. **Gemini Vision OCR** → Gemini 2.5 Flash analyzes the image
4. **Field extraction** → AI extracts handwritten values
5. **Fallback** → If Gemini fails, uses keyword parsing
6. **Confidence scoring** → Returns extracted data with confidence scores

### Supported Forms

- ✅ West Bengal Birth Certificate (English + Bengali)
- ✅ Maharashtra Residence Certificate (English + Marathi)

## Usage

### Via Frontend

1. Go to http://127.0.0.1:8000
2. Upload a filled government form
3. Watch the pipeline steps - you'll see "Gemini Vision OCR"
4. Review extracted fields on the verification page
5. The OCR method banner will show: **"Gemini Vision (gemini-2.5-flash)"**

### Via Python Script

```bash
cd /Users/atharvdalvi/Desktop/PaperTrail/papertrail_backend
python extract_forms.py path/to/form.jpg
```

### Via API Endpoint

```bash
curl -X POST http://127.0.0.1:8000/api/upload-form \
  -F "file=@/path/to/form.jpg"
```

Response includes:
```json
{
  "success": true,
  "ocr_method": "Gemini Vision (gemini-2.5-flash)",
  "extracted_data": {
    "name": "...",
    "date_of_birth": "...",
    ...
  },
  "ocr_confidence": 0.95
}
```

## Technical Details

### Backend Files

- `papertrail_backend/gemini_extractor.py` - Main Gemini integration module
- `papertrail_backend/routes/upload_routes.py` - Modified to try Gemini first
- `papertrail_backend/extract_forms.py` - Standalone CLI script

### Prompts

Gemini uses specialized prompts for each form type:
- **Birth Certificate Prompt**: Extracts 12 fields including Bengali text
- **Residence Certificate Prompt**: Extracts 8 fields with address parsing

### Error Handling

If Gemini is unavailable or fails:
- ✅ Automatically falls back to keyword-based parsing
- ✅ Logs the error reason
- ✅ Frontend still shows extracted data

## Free Tier Limits

- **10 requests per minute**
- **250 requests per day**
- No credit card required
- Gemini 2.5 Flash model

## Troubleshooting

### "google-generativeai package not installed"

```bash
cd /Users/atharvdalvi/Desktop/PaperTrail
source .venv/bin/activate
pip install google-generativeai pillow
```

### "GEMINI_API_KEY not configured"

Add your API key to `.env`:
```bash
echo "GEMINI_API_KEY=your_key_here" >> papertrail_backend/.env
```

Then restart:
```bash
kill $(lsof -tiTCP:8000) && ./run_backend.sh
```

### Check Logs

```bash
tail -f /tmp/papertrail_backend.log
```

## Deprecation Warning

You may see a warning about `google.generativeai` being deprecated in favor of `google.genai`. The integration still works perfectly - we'll update to the new package in a future release.

## Next Steps

Want to add more form types? Edit the prompts in `papertrail_backend/gemini_extractor.py`:

1. Add a new `YOUR_FORM_PROMPT` constant
2. Update the `extract_with_gemini()` function to handle the new form type
3. Test with your form images!

---

**Powered by Google Gemini 2.5 Flash** 🚀
