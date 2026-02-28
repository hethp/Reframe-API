import os
import re
import json
import hashlib
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, List
from dotenv import load_dotenv

from google import genai

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Gemini Configuration with Key Rotation
# ---------------------------------------------------------------------------
# Add keys as comma-separated: GEMINI_API_KEYS=key1,key2,key3,key4
# Falls back to GEMINI_API_KEY if GEMINI_API_KEYS not set
_keys_str = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", ""))
API_KEYS = [k.strip() for k in _keys_str.split(",") if k.strip()]
current_key_index = 0
MODEL_ID = "gemini-2.5-flash"


def get_client():
    """Get a genai client with the current API key."""
    return genai.Client(api_key=API_KEYS[current_key_index])


def call_gemini(prompt: str) -> str:
    """Call Gemini with automatic key rotation on rate limit (429) errors."""
    global current_key_index
    attempts = 0
    last_error = None

    while attempts < len(API_KEYS):
        try:
            client = get_client()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                last_error = e
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                attempts += 1
                print(
                    f"Key {current_key_index} rate-limited, rotating to key "
                    f"{current_key_index + 1}/{len(API_KEYS)}"
                )
            else:
                raise e

    raise Exception(
        f"All {len(API_KEYS)} API keys exhausted. Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# In-memory data store
# ---------------------------------------------------------------------------
# Stores analyses keyed by a short hash ID
analyses_store: Dict[str, dict] = {}
# Stores reframed page results keyed by hash of (paragraphs + generation)
reframe_cache: Dict[str, dict] = {}


def _make_id(url: str) -> str:
    """Deterministic short ID from URL so re-analyzing the same URL is idempotent."""
    return hashlib.sha256(url.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Reframe API",
    description=(
        "Make news accessible, unbiased, and generationally relatable. "
        "Submit a news article URL to receive bias analysis, a neutral summary, "
        "and generational translations (Gen Alpha → Boomer). "
        "Supports follow-up Q&A powered by Gemini."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic Models (request / response)
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Request body for creating a new analysis."""
    url: str = Field(..., description="Full URL of the news article to analyze.", examples=["https://www.bbc.com/news/articles/c1d5r7z7z7ro"])

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.bbc.com/news/articles/c1d5r7z7z7ro"
            }
        }


class BiasResult(BaseModel):
    score: int = Field(..., description="Bias score from -100 (Far Left) to 100 (Far Right), 0 = Neutral")
    label: str = Field(..., description="Human-readable label: Left, Leans Left, Neutral, Leans Right, Right")
    explanation: str = Field(..., description="One-sentence explanation of the bias rating")


class Translations(BaseModel):
    Gen_Alpha: str = Field(..., alias="Gen Alpha")
    Gen_Z: str = Field(..., alias="Gen Z")
    Millennial: str
    Gen_X: str = Field(..., alias="Gen X")
    Boomer: str

    class Config:
        populate_by_name = True


class AnalysisData(BaseModel):
    bias: BiasResult
    summary: str = Field(..., description="Neutral, factual summary stripped of polarized language")
    translations: Translations


class AnalysisResponse(BaseModel):
    id: str = Field(..., description="Unique analysis identifier")
    url: str = Field(..., description="URL of the analyzed article")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    data: AnalysisData


class AnalysisListItem(BaseModel):
    id: str
    url: str
    created_at: str
    bias_label: str
    bias_score: int


class AnalysisListResponse(BaseModel):
    count: int
    analyses: List[AnalysisListItem]


class ChatRequest(BaseModel):
    """Request body for follow-up chat questions."""
    message: str = Field(..., description="Your question about the article.", examples=["What are the key claims in this article?"])

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the key claims in this article?"
            }
        }


class ChatResponse(BaseModel):
    analysis_id: str
    question: str
    reply: str
    retrieval_method: str = Field(..., description="'rag' if semantic retrieval was used, 'fallback' if raw text was used")


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    api_keys_configured: int
    analyses_stored: int


class ErrorResponse(BaseModel):
    error: dict = Field(..., description="Error details with code, type, and message")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_article_text(url: str) -> str:
    """Scrapes paragraph text from a given URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        return text.strip()
    except requests.exceptions.MissingSchema:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": 422,
                    "type": "validation_error",
                    "message": f"Invalid URL format: '{url}'. Must start with http:// or https://",
                }
            },
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": 422,
                    "type": "connection_error",
                    "message": f"Could not connect to URL: '{url}'. Check that it is reachable.",
                }
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": 400,
                    "type": "extraction_error",
                    "message": f"Failed to extract text from URL: {str(e)}",
                }
            },
        )


def process_with_llm(article_text: str) -> Dict:
    """Runs the three LLM tasks using few-shot prompting."""

    prompt = f"""
You are an expert AI journalist and linguist. Analyze the following news article text and perform three tasks.
Return the output STRICTLY as a valid JSON object. Do NOT include markdown formatting like ```json.

Article Text: \"{article_text[:4000]}\"

Task 1: Bias Analysis
Evaluate the article's political/ideological leaning. Look for loaded adjectives and omitted context.
Score from -100 (Extreme Left) to 100 (Extreme Right), where 0 is Neutral.
Assign a label: "Left", "Leans Left", "Neutral", "Leans Right", or "Right".
Explanation: Give a 1-sentence explanation of why.

Task 2: Neutral Summarization
Strip all polarized language to output a purely factual, unbiased summary (approx 3 sentences).

Task 3: Generational Translation

Important: Be sensitive to topics that may involve victims, violence, or trauma. In such cases, prioritize empathy and respect in all translations, and avoid slang that could be perceived as insensitive.

Here are some words/phrases to translate:

For Gen Alpha (born 2010+):
These phrases are very slang-heavy and often used in online contexts, so the translation will focus on a casual, conversational tone with popular slang from the late 2010s and early 2020s, with a heavy emphasis on social media and meme culture:
- "Skibidi rizz" = having charm or influence, especially in a social context
- "No cap" = no lie, for real
- "Cap" = lie or false statement
- "Fanum tax" = a humorous term for an unavoidable cost or consequence
- "Rizz" = charm or attractiveness, especially in a social context
- "Gyatt" = an exclamation of admiration, often for someone's appearance
- "Sus" = suspicious or untrustworthy
- "Mid" = mediocre or average, often used to describe something that is underwhelming
- "NPC" = non-player character, used to describe someone who is perceived as lacking independent thought or originality
- "Ohio" = a term used to describe something that is chaotic, strange, or out of control
- "Sigma" = independent, self-reliant, and often introverted
- "Brainrot" = overwhelmed or mentally exhausted from excessive media consumption
- "Mog" = to outperform or overshadow someone else
- "-maxxing" = doing something to the maximum degree
- "gng" = gang, group of friends
- "chat is this real" = expression of disbelief or amazement
- "ts pmo" = expression of frustration or annoyance, often in response to something perceived as unfair or irritating
- "ragebait" = content designed to provoke an angry response

For Gen Z (born 1997-2012):
CRITICAL STYLE RULE: write in lowercase with auto-capitalization OFF (unless proper nouns like countries or names require capitalization. also leave direct quotes with original capitalization).
These phrases are more slang-heavy and often used in online contexts, so the translation will focus on a casual, conversational tone with popular slang from the late 2010s and early 2020s:
- "ragebait" = content designed to provoke an angry response
- "ts pmo" = expression of frustration or annoyance, often in response to something perceived as unfair or irritating
- "ngl" = not gonna lie
- "red flags" = warning signs
- "valid" = true, accurate, or relatable
- "Ate and left no crumbs" = Did an excellent job
- "Aura" = Personal vibe or energy
- "Bet" = Yes, okay, or I agree
- "GOAT" = Greatest of All Time
- "Stan" = obsessive fan
- "Tea" = Gossip
- "Hits different" = unique, special, or better than usual
- "Living rent-free" = constantly on your mind
- "it's giving ..." = describes the vibe something conveys
- "delulu" = being delusional or unrealistic
- "main character energy" = acting as if you are the protagonist
- "-core" = suffix for a particular aesthetic or style
- "mid" = mediocre or average
- "slimed" = killed, died

For Millennials (born 1981-1996):
These phrases are more casual and slang-heavy, so the translation will focus on a conversational tone with popular slang from the 2000s and 2010s:
- "Adulting" = performing responsible adult tasks
- "#relatable" = resonates with common experiences
- "#unpopularopinion" = a view that may not be widely accepted
- "#blessed" = feeling fortunate or grateful
- "#goals" = aspirational qualities or achievements
- "FOMO" = Fear Of Missing Out
- "YOLO" = You Only Live Once
- "Slay" = do something exceptionally well
- "Squad" = group of friends
- "Extra" = over the top, dramatic
- "Ghosting" = cutting off all communication
- "Salty" = bitter or upset
- "Lit" = exciting, fun, excellent
- "Vibes" = emotional atmosphere or feeling

For Gen X (born 1965-1980):
These phrases are more straightforward and less slang-heavy, so the translation will focus on clear, direct language with a slightly informal tone:
- "Here's the deal" = introduction to an explanation
- "Whatever" = expression of indifference
- "It is what it is" = acceptance of an unchangeable situation
- "Take a chill pill" = calm down
- "Bummer" = disappointing situation
- "Props" = respect or credit
- "Catch you on the flip side" = goodbye

For Boomers (born 1946-1964):
These phrases are more formal and traditional, so the translation will focus on clear, direct language without slang:
- "IMPORTANT UPDATE" = phrase to signal critical information
- "pertinent information" = relevant details
- "Back in my day" = comparing to the past
- "Kids these days" = generalizing about younger generation
- "Cutting-edge" = very modern or innovative
- "Old-school" = traditional, classic

Rewrite the headline and summary into distinct styles using the following examples as a guide (feel free to be creative but keep the core meaning and facts intact). Also, diversify the openings and tones for each generation to avoid repetition:
- Gen Alpha: 
    - Original headline: "Iran strikes were launched without approval from Congress, deeply dividing lawmakers" = "Chat is this real? Strikes launched against Iran, Congress not in the chat. Major red flags, ngl."
- Gen Z: 
    - Original headline: "Iran strikes were launched without approval from Congress, deeply dividing lawmakers" = "It's giving unauthorized strikes. Congress not in the loop, and lawmakers are throwing major shade."
- Millennial: 
    - Original headline: "Iran strikes were launched without approval from Congress, deeply dividing lawmakers" = "Adulting fail: Strikes against Iran launched without Congress approval, leaving lawmakers salty and divided."
- Gen X: 
    - Original headline: "Iran strikes were launched without approval from Congress, deeply dividing lawmakers" = "Here's the deal: Strikes were launched against Iran without Congress's OK, and it's causing a major rift among lawmakers."
- Boomer: 
    - Original headline: "Iran strikes were launched without approval from Congress, deeply dividing lawmakers" = "IMPORTANT UPDATE: Strikes against Iran were launched without the approval of Congress, leading to a deep divide among lawmakers. This is a significant development that underscores the importance of adhering to established protocols for military action."

Output JSON Format Required:
{{
  "bias": {{
    "score": 0,
    "label": "Neutral",
    "explanation": "..."
  }},
  "summary": "...",
  "translations": {{
    "Gen Alpha": "...",
    "Gen Z": "...",
    "Millennial": "...",
    "Gen X": "...",
    "Boomer": "..."
  }}
}}
"""
    try:
        content = call_gemini(prompt)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        result = json.loads(content)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": 502,
                    "type": "llm_parse_error",
                    "message": f"LLM returned invalid JSON: {str(e)}",
                }
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": 500,
                    "type": "llm_error",
                    "message": f"LLM processing failed: {str(e)}",
                }
            },
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health and configuration",
)
def health_check():
    """Returns the current status of the API, including model info and key count."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model": MODEL_ID,
        "api_keys_configured": len(API_KEYS),
        "analyses_stored": len(analyses_store),
    }


@app.post(
    "/api/v1/analyses",
    response_model=AnalysisResponse,
    status_code=200,
    tags=["Analyses"],
    summary="Analyze a news article",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid URL format"},
        500: {"model": ErrorResponse, "description": "LLM processing error"},
    },
)
async def create_analysis(req: AnalysisRequest):
    """
    Submit a news article URL for analysis.

    The API will:
    1. Scrape the article text
    2. Evaluate political bias (Left ↔ Right scale)
    3. Generate a neutral, fact-based summary
    4. Translate the summary into 5 generational styles

    **Idempotent**: re-submitting the same URL returns the cached result.
    """
    analysis_id = _make_id(req.url)

    # Idempotent — return cached result if already analyzed
    if analysis_id in analyses_store:
        return analyses_store[analysis_id]

    article_text = extract_article_text(req.url)

    if not article_text:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": 422,
                    "type": "extraction_error",
                    "message": "No readable text found at the provided URL.",
                }
            },
        )

    llm_results = process_with_llm(article_text)

    analysis = {
        "id": analysis_id,
        "url": req.url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": llm_results,
        "_article_text": article_text,  # internal, not returned
    }

    analyses_store[analysis_id] = analysis

    # Return without internal field
    return {k: v for k, v in analysis.items() if not k.startswith("_")}


@app.get(
    "/api/v1/analyses",
    response_model=AnalysisListResponse,
    tags=["Analyses"],
    summary="List all analyses",
)
def list_analyses(
    bias: Optional[str] = Query(
        None,
        description="Filter by bias label (e.g. Left, Neutral, Right, Leans Left, Leans Right)",
        examples=["Neutral", "Left"],
    ),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    Retrieve a paginated list of all previously analyzed articles.

    Supports optional filtering by bias label and pagination via `limit` and `offset`.
    """
    items = []
    for aid, a in analyses_store.items():
        if a.get("_article_text"):  # skip internal check
            entry = {
                "id": a["id"],
                "url": a["url"],
                "created_at": a["created_at"],
                "bias_label": a["data"]["bias"]["label"],
                "bias_score": a["data"]["bias"]["score"],
            }
            if bias and entry["bias_label"].lower() != bias.lower():
                continue
            items.append(entry)

    # Pagination
    paginated = items[offset: offset + limit]

    return {"count": len(items), "analyses": paginated}


@app.get(
    "/api/v1/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    tags=["Analyses"],
    summary="Get a specific analysis by ID",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
def get_analysis(analysis_id: str):
    """Retrieve the full analysis result for a previously analyzed article."""
    if analysis_id not in analyses_store:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": 404,
                    "type": "not_found",
                    "message": f"No analysis found with id '{analysis_id}'. Use POST /api/v1/analyses to create one.",
                }
            },
        )
    a = analyses_store[analysis_id]
    return {k: v for k, v in a.items() if not k.startswith("_")}


@app.delete(
    "/api/v1/analyses/{analysis_id}",
    tags=["Analyses"],
    summary="Delete a stored analysis",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
def delete_analysis(analysis_id: str):
    """Remove an analysis from the store."""
    if analysis_id not in analyses_store:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": 404,
                    "type": "not_found",
                    "message": f"No analysis found with id '{analysis_id}'.",
                }
            },
        )
    del analyses_store[analysis_id]
    return {"message": f"Analysis '{analysis_id}' deleted successfully."}


@app.post(
    "/api/v1/analyses/{analysis_id}/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Ask a follow-up question about an analyzed article",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def chat(analysis_id: str, req: ChatRequest):
    """
    Ask a follow-up question about a previously analyzed article.

    The LLM answers strictly from the article's text context.
    You must first create an analysis via `POST /api/v1/analyses` before chatting.
    """
    if analysis_id not in analyses_store:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": 404,
                    "type": "not_found",
                    "message": (
                        f"No analysis found with id '{analysis_id}'. "
                        "Please analyze the article first via POST /api/v1/analyses."
                    ),
                }
            },
        )

    context = analyses_store[analysis_id].get("_article_text", "")

    prompt = f"""
You are a helpful assistant answering questions strictly based on the provided news context.
If the answer is not in the context, say "I don't have enough information from the article to answer that."

Context: \"{context[:4000]}\"

Question: \"{req.message}\"
"""
    reply = call_gemini(prompt)
    return {
        "analysis_id": analysis_id,
        "question": req.message,
        "reply": reply,
    }


# ---------------------------------------------------------------------------
# Full-Page Reframe Endpoint
# ---------------------------------------------------------------------------


class ReframePageRequest(BaseModel):
    """Request body for full-page reframing."""
    paragraphs: List[str] = Field(..., description="Array of paragraph texts from the page")
    generation: str = Field(..., description="Target generation style", examples=["Gen Alpha"])


class ReframePageResponse(BaseModel):
    generation: str
    reframed: List[str] = Field(..., description="Reframed paragraphs in the same order")
    count: int
    cached: bool = Field(False, description="Whether the result was served from cache")


@app.post(
    "/api/v1/reframe-page",
    response_model=ReframePageResponse,
    tags=["Analyses"],
    summary="Reframe full page text into a generational style",
)
async def reframe_page(req: ReframePageRequest):
    """
    Takes an array of paragraph texts extracted from a web page and rewrites
    each one in the chosen generational style.

    **Direct quotes** (text inside quotation marks) are preserved exactly as-is.
    Each paragraph is reframed individually to maintain the article's structure.
    """
    if not req.paragraphs:
        raise HTTPException(status_code=422, detail={
            "error": {"code": 422, "type": "validation_error",
                      "message": "paragraphs array must not be empty"}
        })

    # --- Cache lookup ---
    cache_key = hashlib.sha256(
        (req.generation + "||" + "|||".join(req.paragraphs)).encode()
    ).hexdigest()[:16]

    if cache_key in reframe_cache:
        cached = reframe_cache[cache_key]
        print(f"Reframe cache HIT for {req.generation} ({cache_key})")
        return {**cached, "cached": True}

    # Build a numbered list so Gemini can return results in order
    numbered = "\n".join(
        f"[{i}] {p}" for i, p in enumerate(req.paragraphs)
    )

    prompt = f"""You are a linguist rewriting text in the "{req.generation}" generational style.

CRITICAL RULES:
1. Rewrite EVERY numbered paragraph below in the {req.generation} style.
2. NEVER change direct quotes — any text inside quotation marks ("..." or '...') must stay EXACTLY the same.
3. Keep the same factual meaning and information.
4. Return ONLY a valid JSON array of strings, one per paragraph, in the same order.
5. Do NOT include markdown formatting like ```json.

Paragraphs to rewrite:
{numbered}

Return a JSON array like: ["reframed paragraph 0", "reframed paragraph 1", ...]
"""

    try:
        content = call_gemini(prompt)
        print(f"[REFRAME DEBUG] Raw Gemini response (first 500 chars): {content[:500]}")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        reframed = json.loads(content)

        # Ensure we got a list of strings
        if not isinstance(reframed, list):
            reframed = [str(reframed)]

        # Normalize: flatten any non-string items
        reframed = [
            " ".join(v.values()) if isinstance(v, dict) else str(v)
            for v in reframed
        ]

        # Pad or trim to match input length
        while len(reframed) < len(req.paragraphs):
            reframed.append(req.paragraphs[len(reframed)])
        reframed = reframed[:len(req.paragraphs)]

        result = {
            "generation": req.generation,
            "reframed": reframed,
            "count": len(reframed),
        }

        # Store in cache for future hits
        reframe_cache[cache_key] = result
        print(f"Reframe cache STORE for {req.generation} ({cache_key})")

        return {**result, "cached": False}
    except json.JSONDecodeError as e:
        print(f"[REFRAME ERROR] JSON parse failed: {e}")
        print(f"[REFRAME ERROR] Content was: {content[:1000]}")
        raise HTTPException(status_code=502, detail={
            "error": {"code": 502, "type": "llm_parse_error",
                      "message": f"LLM returned invalid JSON for page reframe. Preview: {content[:200]}"}
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": {"code": 500, "type": "llm_error",
                      "message": f"Page reframe failed: {str(e)}"}
        })


# ---------------------------------------------------------------------------
# Legacy endpoint redirects (keep Chrome Extension working)
# ---------------------------------------------------------------------------


@app.post("/process-news", tags=["Legacy"], include_in_schema=False)
async def legacy_process_news(req: AnalysisRequest):
    """Legacy endpoint — redirects to /api/v1/analyses."""
    return await create_analysis(req)


@app.post("/chat", tags=["Legacy"], include_in_schema=False)
async def legacy_chat(req: dict):
    """Legacy endpoint — redirects to /api/v1/analyses/{id}/chat."""
    url = req.get("url", "")
    analysis_id = _make_id(url)
    chat_req = ChatRequest(message=req.get("message", ""))
    return await chat(analysis_id, chat_req)


@app.get("/", tags=["Health"], include_in_schema=False)
def read_root():
    return {"message": "Reframe API is running. Visit /docs for interactive documentation."}
