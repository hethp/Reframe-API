# Reframe API

> **Make news accessible, unbiased, and generationally relatable.**

Reframe is a Chrome extension + FastAPI backend that analyzes news articles for political bias, generates neutral summaries, and translates them into generational styles — from Gen Alpha brainrot to Boomer formal.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, [FastAPI](https://fastapi.tiangolo.com/) |
| **AI / LLM** | [Google Gemini 2.5 Flash](https://ai.google.dev/) via `google-genai` SDK |
| **Web Scraping** | BeautifulSoup4, Requests |
| **Frontend** | Chrome Extension (Manifest V3), vanilla HTML/CSS/JS |
| **Data Store** | In-memory dict (article text + analysis results) |

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

# Or multiple keys for automatic rotation (4 keys = 80 RPD)
GEMINI_API_KEYS=key1,key2,key3,key4
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run the server

```bash
cd Reframe-API
python -m uvicorn backend.main:app --reload
```

The API is now live at **http://localhost:8000**.

### 4. Explore the docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Health Check

```
GET /api/v1/health
```

```bash
curl http://localhost:8000/api/v1/health
```

**Response** `200 OK`:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model": "gemini-2.5-flash",
  "api_keys_configured": 2,
  "analyses_stored": 3
}
```

---

### Analyze an Article

```
POST /api/v1/analyses
```

Submit a news article URL. Returns bias score, neutral summary, and 5 generational translations.

**Idempotent** — re-submitting the same URL returns the cached result.

```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bbc.com/news/articles/c1d5r7z7z7ro"}'
```

**Response** `200 OK`:
```json
{
  "id": "a1b2c3d4e5f6",
  "url": "https://www.bbc.com/news/articles/c1d5r7z7z7ro",
  "created_at": "2026-02-28T05:14:00+00:00",
  "data": {
    "bias": {
      "score": -15,
      "label": "Leans Left",
      "explanation": "The article uses emotionally loaded language favoring progressive viewpoints."
    },
    "summary": "A factual, unbiased summary of the article...",
    "translations": {
      "Gen Alpha": "No cap this is lowkenuinely crazy...",
      "Gen Z": "ngl this situation is giving major red flags...",
      "Millennial": "Adulting is hard enough, but this news takes the cake. #relatable",
      "Gen X": "Here's the deal on what happened. Whatever.",
      "Boomer": "IMPORTANT UPDATE: Please read this pertinent information."
    }
  }
}
```

**Error** `422 Unprocessable Entity`:
```json
{
  "error": {
    "code": 422,
    "type": "validation_error",
    "message": "Invalid URL format: 'not-a-url'. Must start with http:// or https://"
  }
}
```

---

### List All Analyses

```
GET /api/v1/analyses
```

Returns a paginated list of all previously analyzed articles. Supports filtering by bias label.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `bias` | string | — | Filter by bias label (`Left`, `Leans Left`, `Neutral`, `Leans Right`, `Right`) |
| `limit` | int | 20 | Max results (1–100) |
| `offset` | int | 0 | Results to skip |

```bash
# List all
curl http://localhost:8000/api/v1/analyses

# Filter by bias
curl "http://localhost:8000/api/v1/analyses?bias=Neutral&limit=5"
```

**Response** `200 OK`:
```json
{
  "count": 3,
  "analyses": [
    {
      "id": "a1b2c3d4e5f6",
      "url": "https://www.bbc.com/news/...",
      "created_at": "2026-02-28T05:14:00+00:00",
      "bias_label": "Leans Left",
      "bias_score": -15
    }
  ]
}
```

---

### Get Analysis by ID

```
GET /api/v1/analyses/{analysis_id}
```

```bash
curl http://localhost:8000/api/v1/analyses/a1b2c3d4e5f6
```

**Response** `200 OK`: Same shape as the POST response.

**Error** `404 Not Found`:
```json
{
  "error": {
    "code": 404,
    "type": "not_found",
    "message": "No analysis found with id 'abc123'. Use POST /api/v1/analyses to create one."
  }
}
```

---

### Delete an Analysis

```
DELETE /api/v1/analyses/{analysis_id}
```

```bash
curl -X DELETE http://localhost:8000/api/v1/analyses/a1b2c3d4e5f6
```

**Response** `200 OK`:
```json
{
  "message": "Analysis 'a1b2c3d4e5f6' deleted successfully."
}
```

---

### Follow-up Chat

```
POST /api/v1/analyses/{analysis_id}/chat
```

Ask follow-up questions about a previously analyzed article. The LLM answers strictly from the article's context.

```bash
curl -X POST http://localhost:8000/api/v1/analyses/a1b2c3d4e5f6/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the key claims in this article?"}'
```

**Response** `200 OK`:
```json
{
  "analysis_id": "a1b2c3d4e5f6",
  "question": "What are the key claims in this article?",
  "reply": "The article makes three key claims..."
}
```

---

## Error Handling

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

---

## Chrome Extension Setup

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select the `extension/` folder
4. Navigate to any news article and click the Reframe icon

---

## API Key Rotation

The API supports automatic key rotation across multiple Gemini API keys. When one key hits the free-tier rate limit (429), it automatically tries the next key.

```env
GEMINI_API_KEYS=key1,key2,key3,key4
```

With 4 keys, you get **80 requests/day** on the free tier (20 RPD per key).

---

## License

MIT