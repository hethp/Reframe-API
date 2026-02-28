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

import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

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
        response = model.generate_content(prompt)
        # Parse JSON from response
        # Sometimes the model still outputs markdown ```json
        content = response.text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()
            
        result = json.loads(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}\nRaw Response: {response.text if 'response' in locals() else 'None'}")

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
    response = model.generate_content(prompt)
    return {"reply": response.text}

@app.get("/")
def read_root():
    return {"message": "Reframe API is running"}
