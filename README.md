# Reframe API

> Make news accessible, unbiased, and generationally relatable.

Reframe is a Chrome extension designed to make news articles easier to understand across different generations. It summarizes article content and translates them into generational styles — from Gen Alpha brainrot to Boomer formal– while preserving the original meaning and key information.

The extension works by extracting article text from a webpage, sending it to the Reframe API for processing, and then dynamically replacing the on-page content with the reframed version in the selected generational style.

---

## Features

* Bias and tone analysis for online articles
* Multi-style generational rewriting (Gen Alpha → Boomer)
* Persistent storage of analyses with retrieval & deletion
* Conversational follow-up questions about analyzed content
* Predictable RESTful JSON responses
* Consistent structured error messages
* Fully testable via HTTP (cURL/Postman)
* Automatic API key rotation for reliability

---

## Tech Stack

| Layer                    | Technology                                 |
| ------------------------ | ------------------------------------------ |
| **Backend Framework**    | FastAPI (built on Starlette), Python 3.11  |
| **Validation & Schemas** | Pydantic                                   |
| **Language Model**       | Google Gemini 2.5 Flash (google-genai SDK) |
| **Web Scraping**         | BeautifulSoup, Requests                    |
| **Frontend Client**      | Chrome Extension (Manifest V3)             |
| **UI Rendering**         | DOM rewriting & overlays                   |
| **Storage**              | Chrome Storage API                         |

---

## Running Locally

### 1. Clone repository

```bash
git clone https://github.com/yourteam/Reframe-API.git
cd Reframe-API/backend
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Single API key
GEMINI_API_KEY=your_key_here

# OR multiple keys for automatic rotation
GEMINI_API_KEYS=key1,key2,key3,key4
```

Get a free API key from: https://aistudio.google.com/apikey

### 5. Run the API server

```bash
python -m uvicorn backend.main:app --reload
```

The API will be available at:

* Base URL: http://localhost:8000
* Interactive Docs (Swagger): http://localhost:8000/docs

---

## Base URL

```
http://localhost:8000/api/v1
```

All endpoints are prefixed with `/api/v1`.

---

## API Endpoints

### Health Check

**GET /api/v1/health**
Returns server status information.

---

### Submit Article for Analysis

**POST /api/v1/analyses**

Analyzes a news article URL for bias, summary, and generational rewriting.

Request:

```json
{
  "url": "https://example.com/news-article"
}
```

Success Response:

```json
{
  "analysis_id": "abc123",
  "summary": "...",
  "bias": "center",
  "reframes": {
    "gen_z": "...",
    "boomer": "..."
  }
}
```

---

### List Stored Analyses

**GET /api/v1/analyses**

Optional query parameters:

* `bias` (filter by bias label)
* `limit` (pagination size)
* `offset` (pagination offset)

---

### Fetch Single Analysis

**GET /api/v1/analyses/{analysis_id}**

Retrieves a previously stored analysis by ID.

---

### Delete Analysis

**DELETE /api/v1/analyses/{analysis_id}**

Removes a stored analysis from the system.

Returns:

* `200 OK` if deletion succeeds
* `404 Not Found` if the ID does not exist

---

### Follow-up Chat on Analysis

**POST /api/v1/analyses/{analysis_id}/chat**

Ask contextual questions about an already analyzed article.

Request:

```json
{
  "question": "What bias does this article show?"
}
```

---

### Reframe Page Content

**POST /api/v1/reframe-page**

Rewrites an array of paragraph texts into a selected generational style.

Request:

```json
{
  "paragraphs": ["Paragraph one...", "Paragraph two..."],
  "style": "gen_z"
}
```

---

## Example cURL Usage

### Analyze an article

```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### Fetch an analysis

```bash
curl http://localhost:8000/api/v1/analyses/abc123
```

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

These examples confirm the API is fully queryable over HTTP and testable via cURL/Postman.

---

## Error Handling

All errors follow a consistent JSON structure:

```json
{
  "error": {
    "code": 422,
    "type": "validation_error",
    "message": "Human-readable explanation of what went wrong"
  }
}
```

### Common Status Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 200  | Successful request                |
| 400  | Bad request / extraction failure  |
| 404  | Analysis ID not found             |
| 422  | Invalid URL or missing text       |
| 429  | All API keys rate-limited         |
| 500  | Internal model processing error   |
| 502  | Model returned unparseable output |

---

## Debugging Workflow

1. Ensure the server is running on localhost
2. Test endpoints using Swagger docs or Postman
3. Inspect Chrome extension console for frontend errors
4. Check backend terminal logs for stack traces

This layered approach isolates whether issues originate from:

* Client (extension)
* API server
* External LLM services

---

## API Design Highlights

* Fully RESTful architecture using GET, POST, and DELETE
* Persistent state: analyses can be stored, retrieved, deleted, and queried conversationally
* Predictable JSON responses and structured errors
* Built for excellent developer experience and clarity
* Operational entirely on localhost and testable via standard HTTP tools

---

## Chrome Extension (Optional Client)

The Chrome extension extracts webpage content, sends it to the API, and dynamically rewrites the DOM using overlays with the reframed content.

Setup:

1. Navigate to `chrome://extensions/`
2. Enable Developer Mode
3. Click “Load unpacked” and select the `extension/` folder
4. Open a news article and use the Reframe toolbar popup

---

## License

MIT
