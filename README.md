# Reframe API

> **Make news accessible, unbiased, and generationally relatable.**

Reframe is a Chrome extension designed to make news articles easier to understand across different generations. It summarizes article content and translates them into generational styles — from Gen Alpha brainrot to Boomer formal– while preserving the original meaning and key information, 

The extension works by extracting article text from a webpage, sending it to the Reframe API for processing, and then dynamically replacing the on-page content with the reframed version in the selected generational style.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13, [FastAPI](https://fastapi.tiangolo.com/) |
| **AI / LLM** | [Google Gemini 2.5 Flash](https://ai.google.dev/) via google-genai SDK |
| **Web Scraping** | BeautifulSoup, Requests |
| **Frontend** | Chrome Extension (Manifest V3), HTML/CSS/JS |
| **UI Rendering** | DOM rewriting & overlays |
| **Storage** | Chrome Storage API |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourteam/Reframe-API.git
cd Reframe-API/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the **project root**:

```env
# Single key
GEMINI_API_KEY=your_key_here

# OR multiple keys for automatic rotation
GEMINI_API_KEYS=key1,key2,key3,key4
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run the server

```bash
cd Reframe-API
python -m uvicorn backend.main:app --reload
```
The API is now live at **http://localhost:8000**.

Interative API docs can be found at **http://localhost:8000/docs**

---


## Chrome Extension Setup
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select the `extension/` folder
4. Navigate to any news article and click the Reframe icon

The Reframe extension should now appear in your toolbar.

---

## Using the Extension
1. Open any news article webpage
2. Click the Reframe extension icon
3. Press “Analyze Current Page”
4. Choose a translation style: Neutral Summary, Gen Alpha, Gen Z, Millennial, Gen X, Boomer

The page content will be dynamically reframed in the selected style.

The extension also includes a contextual chat tool for article-specific questions, which can be accessed by scrolling to **Follow-Up Chatter**.

---

## API Key Rotation

The API supports automatic key rotation across multiple Gemini API keys. When one key hits the free-tier rate limit (err 429), it automatically tries the next key.

```env
GEMINI_API_KEYS=key1,key2,key3,key4
```

With four keys, you get **80 requests/day** on the free tier (20 RPD per key).

---

## Error Handling

Errors may originate from either the backend API or the Chrome extension. Identifying where the error appears helps diagnose issues quickly.

**Common API Errors**

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": 422,
    "type": "validation_error",
    "message": "Human-readable description of what went wrong"
  }
}
```

| Code | When |
|---|---|
| `400` | Bad request / extraction failed |
| `404` | Analysis ID not found |
| `422` | Invalid URL format or no text found |
| `429` | All API keys rate-limited |
| `500` | Internal LLM error |
| `502` | LLM returned unparseable response |

**How to Debug Issues (Recommended Workflow)**
1) Confirm server is running
2) Test endpoint independently (via API docs or Postman)
3) Inspect browser console for extension errors
4) Check backend terminal logs for stack traces
This layered workflow makes it easy to isolate whether the issue originates from the Chrome extension, the backend API, or external services.

---




## License

MIT