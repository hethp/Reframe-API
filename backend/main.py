import os
import re
import json
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from dotenv import load_dotenv

from google import genai

# Load environment variables
load_dotenv()

# Configure Gemini with key rotation
# Add keys as comma-separated in .env: GEMINI_API_KEYS=key1,key2,key3,key4
# Falls back to single GEMINI_API_KEY if GEMINI_API_KEYS is not set
_keys_str = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", ""))
API_KEYS = [k.strip() for k in _keys_str.split(",") if k.strip()]
current_key_index = 0
MODEL_ID = "gemini-2.5-flash"

def get_client():
    """Get a genai client with the current API key."""
    return genai.Client(api_key=API_KEYS[current_key_index])

def call_gemini(prompt: str) -> str:
    """Call Gemini with automatic key rotation on rate limit errors."""
    global current_key_index
    attempts = 0
    last_error = None

    while attempts < len(API_KEYS):
        try:
            client = get_client()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                last_error = e
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                attempts += 1
                print(f"Key {current_key_index} rate limited, rotating to key {current_key_index + 1}/{len(API_KEYS)}")
            else:
                raise e

    raise Exception(f"All {len(API_KEYS)} API keys exhausted. Last error: {last_error}")

# In-memory article store (replaces ChromaDB to avoid C++ build issues)
article_store: Dict[str, str] = {}

app = FastAPI(title="Reframe API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's a Chrome Extension testing everywhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    url: Optional[str] = None
    query: Optional[str] = None

class ChatRequest(BaseModel):
    url: str
    message: str

def extract_article_text(url: str) -> str:
    """Scrapes paragraph text from a given URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text from URL: {str(e)}")

def process_with_llm(article_text: str) -> Dict:
    """Runs the LLM tasks using few-shot prompting."""
    
    prompt = f"""
You are an expert AI journalist and linguist. Analyze the following news article text and perform three tasks.
Return the output STRICTLY as a valid JSON object. Do NOT include markdown formatting like ```json.

Article Text: "{article_text[:4000]}"

Task 1: Bias Analysis
Evaluate the article's political/ideological leaning. Look for loaded adjectives and omitted context.
Score from -100 (Extreme Left) to 100 (Extreme Right), where 0 is Neutral.
Assign a label: "Left", "Leans Left", "Neutral", "Leans Right", or "Right".
Explanation: Give a 1-sentence explanation of why.

Task 2: Neutral Summarization
Strip all polarized language to output a purely factual, unbiased summary (approx 3 sentences).

Task 3: Generational Translation

Here are some words/phrases to translate:
- "Skibidi rizz" = having charm or influence, especially in a social context
- "No cap" = no lie, for real
- "Fanum tax" = a humorous term for an unavoidable cost or consequence

Rewrite the headline and summary into distinct styles using the following examples as a guide:
- Gen Alpha: "Skibidi rizz on current events. No cap this fanum tax is crazy."
- Gen Z: "ngl this situation is giving major red flags. valid."
- Millennial: "Adulting is hard enough, but this news takes the cake. #relatable"
- Gen X: "Here's the deal on what happened today. Whatever."
- Boomer: "IMPORTANT UPDATE: Please read this pertinent information regarding today's events."

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
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()
            
        result = json.loads(content)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")

@app.post("/process-news")
async def process_news(req: ProcessRequest):
    if not req.url and not req.query:
        raise HTTPException(status_code=400, detail="Must provide URL or query")
    
    article_text = ""
    source_id = ""
    
    if req.url:
        article_text = extract_article_text(req.url)
        source_id = req.url
    else:
        # TODO: Implement NewsAPI fetching if query is provided.
        # For now, this focuses on the requested URL flow. 
        raise HTTPException(status_code=501, detail="Query-based fetching not yet implemented in this snippet")

    if not article_text:
        raise HTTPException(status_code=400, detail="No readable text found at URL")

    # 1. RAG Storage (in-memory)
    article_store[source_id] = article_text
    
    # 2. LLM Processing (Bias, Summary, Translations)
    results = process_with_llm(article_text)
    
    return {
        "status": "success",
        "data": results
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    """Answers follow-up questions using the RAG DB for the specific article."""
    # Retrieve context from in-memory store
    context = article_store.get(req.url)
    if not context:
        raise HTTPException(status_code=404, detail="Article context not found. Please process the article first.")
        
    prompt = f"""
You are a helpful assistant answering questions strictly based on the provided news context. 
If the answer is not in the context, say "I don't have enough information from the article to answer that."

Context: "{context[:4000]}"

Question: "{req.message}"
"""
    reply = call_gemini(prompt)
    return {"reply": reply}

@app.get("/")
def read_root():
    return {"message": "Reframe API is running"}
