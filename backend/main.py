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

For Gen Alpha (born 2010+):
- "Skibidi rizz" = having charm or influence, especially in a social context
- "No cap" = no lie, for real
- "Cap" = lie or false statement
- "Fanum tax" = a humorous term for an unavoidable cost or consequence
- "Rizz" = charm or attractiveness, especially in a social context
- "Gyatt" = an exclamation of admiration, often for someone's appearance
- "67" = a playful term for something that is very good or impressive
- "Sus" = suspicious or untrustworthy
- "Mid" = mediocre or average, often used to describe something that is underwhelming
- "NPC" = non-player character, used to describe someone who is perceived as lacking independent thought or originality
- "Ohio" = a term used to describe something that is chaotic, strange, or out of control, often in a humorous way
- "Bro thinks he's him" = a phrase used to mock someone who is acting overly confident or arrogant, often without justification
- "Sweaty" = a term used to describe someone who is trying too hard, often in a way that is perceived as desperate or awkward
- "Chopped" = a term used to describe someone who has been rejected, defeated, or humiliated, often in a social context
- "Unc" = a term used to refer to an older
- "Lowkenuinely" = the more sarcastic, ironic way to say low-key
- "Highkenuinely" = the more sarcastic, ironic way to say high-key
- "Locked in" = being fully focused or committed to something, often in a way that is impressive or admirable
- "Goofy ahh" = a playful insult for someone acting silly or ridiculous, often in a way that is endearing or humorous
- "Sigma" = a term used to describe someone who is independent, self-reliant, and often introverted, in contrast to the more social alpha personality type
- "Alpha" = a term used to describe someone who is confident, assertive, and often socially dominant
- "Brainrot" = a state of being overwhelmed or mentally exhausted, often due to excessive exposure to information or media
- "Mog" = a term used to describe someone who has been outperformed or overshadowed by someone else, often in a way that is humiliating or demoralizing
- "Sussy baka" = a playful insult combining "sus" and "baka" (a Japanese term for "fool"), used to describe someone who is acting suspiciously foolish or naive
- "Fat chud" = a playful insult for someone who is acting lazy, unproductive, or indulgent, often used in a humorous or teasing way to describe someone who is perceived as being out of shape or lacking motivation
- "-maxxing" = a suffix added to a word to indicate that something is being done to the maximum degree, often used in a playful or exaggerated way (e.g., "stress-maxxing" to describe being extremely stressed out)
- "opp" = opponent, often used in gaming or competitive contexts to refer to someone you are competing against
- "gng" = gang, used to refer to a group of friends or associates in a playful way
- "chat is this real" = an expression of disbelief or amazement, often used in response to surprising or impressive content

For Gen Z (born 1997-2012):
- "chat is this real" = an expression of disbelief or amazement, often used in response to surprising or impressive content
- "smh" = shaking my head, used to express disbelief or disappointment
- "ngl" = not gonna lie
- "red flags" = warning signs
- "valid" = true, accurate, or relatable
- "Ate no crumbs" or "left no crumbs" = Did an excellent job or looked amazing.
- "Aura" = Personal vibe, energy, or respect level (e.g."+100 aura").
- "Beige flag" = A quirky or neutral habit, neither good nor bad.
- "Bet" = Yes, okay, or I agree.
- "Cap" = Lie or false statement.
- "No cap" = no lie, for real
- "Glow Up" = A major positive transformation in appearance or confidence.
- "GOAT" = "Greatest of All Time".
- "Simp" = Someone who does way too much for someone they like.
- "Stan" = To be an obsessive fan of a celebrity or fictional character.
- "Tea" = Gossip or personal information belonging to someone else.
- "Thirsty" = Desperate for attention or approval, often in a romantic context.
- "Woke" = Being aware of social injustices and issues, often used sarcastically to criticize performative activism.
- "High-Key" = Very obvious or intense.
- "Low-Key" = Subtle or not obvious, often used to describe feelings or desires that are kept quiet.
- "Take the L" = to experience a loss or failure, often used humorously
- "Hits different" = Something that is unique, special, or better than usual.
- "Living rent-free" When a thought or person is constantly on your mind.
- "Spill the tea" = share gossip or personal information
- "Clock it" = to notice or realize something, often used when someone is being shady or deceptive
- "Overstimulated" = feeling overwhelmed by too much sensory input, often used to describe the effects of social media or technology
- "Tuff" = a term of approval or admiration, often used to describe something that is impressive or cool
- "Bruh" = an exclamation of disbelief, frustration, or disappointment, often used in response to something that is perceived as ridiculous or unfair
- "Cringe" = something that is embarrassing or awkward, often used to describe content on social media that is perceived as trying too hard or being out of touch
- "Unc" = a term used to refer to an older person, teasingly implying they are out of touch with current trends, often used in a playful or ironic way
- "Flow state" = a mental state of being fully immersed and focused on an activity, often leading to high productivity or creativity
- "Glow up" = a major positive transformation in appearance or confidence
- "Cooked" = a term used to describe someone who is overwhelmed, defeated, or in a bad state, often due to stress or exhaustion
- "Locked in" = a term used to describe someone who is fully focused or committed to something, often in a way that is impressive or admirable
- "Performative" = actions that are done for show rather than genuine intent, often used to criticize superficial displays of activism or virtue signaling
- "Pookie" = a term of endearment for a close friend or romantic partner, often used in a playful or affectionate way
- "Simp" = someone who does way too much for someone they like, often used in a teasing or critical way to describe someone who is perceived as being overly submissive or desperate for attention from a romantic interest
- "Stan" = to be an obsessive fan of a celebrity or fictional character, often used in a playful or self-deprecating way to describe intense fandom or admiration for someone or something
- "Sus" = suspicious or untrustworthy, often used to describe someone who is acting in a way that raises doubts about their intentions or honesty
- "Mogged" = a term used to describe someone who has been outperformed or overshadowed by someone else, often in a way that is humiliating or demoralizing
- "Lore" = the backstory, history, or mythology surrounding a particular subject, often used in the context of fictional universes or complex narratives to refer to the detailed information that enriches the understanding of the story or world-building elements
- "Pick-me" = a term used to describe someone who is perceived as trying too hard to gain approval or attention, often in a way that is seen as desperate or insincere, especially in social or romantic contexts
- "Fade" = to leave or exit a situation, often used in a social context to describe someone who is trying to avoid confrontation or awkwardness by quietly removing themselves from the scene
- "Fat Chud" = a playful insult for someone who is acting lazy, unproductive, or indulgent, often used in a humorous or teasing way to describe someone who is perceived as being out of shape or lacking motivation
- "Tripping" = acting irrationally or overreacting, often used to describe someone who is perceived as being overly sensitive or dramatic about a situation
- "-maxxing" = a suffix added to a word to indicate that something is being done to the maximum degree, often used in a playful or exaggerated way (e.g., "stress-maxxing" to describe being extremely stressed out)
- "Cooking" = a term used to describe someone who is doing very well or succeeding at something, often in a way that is impressive or admirable, especially in the context of gaming or creative endeavors
- "opp" = opponent, often used in gaming or competitive contexts to refer to someone you are competing against
- "Karen" = a pejorative term for a middle-aged white woman perceived as entitled or demanding beyond the scope of what is normal, often used in a humorous or critical way to describe someone who is acting in a way that is seen as unreasonable or privileged
- "Looks-maxxing" = taking actions to improve one's physical appearance, often through grooming, fashion, or fitness, with the goal of maximizing attractiveness
- "it's giving ... " = a phrase used to describe the vibe, energy, or impression that something is conveying, often followed by a specific description (e.g., "it's giving vintage vibes" to describe something that has a retro aesthetic)
- "Serving" = to present oneself in a way that is impressive or attention-grabbing, often used in the context of fashion, performance, or social media to describe someone who is showcasing their style, talent, or personality in a way that is meant to captivate an audience
- "Giving" = a term used to describe the vibe, energy, or impression that someone or something is projecting, often used in the context of fashion, performance, or social media to describe the overall aesthetic or mood that is being conveyed (e.g., "it's giving vintage vibes" to describe something that evokes a retro style or feeling)
- "gagged" = a term used to describe someone who is extremely impressed, surprised, or overwhelmed by something, often in a way that is positive or admiring, especially in the context of fashion, performance, or social media where it can be used to express strong approval or admiration for someone's style, talent, or personality
- "delulu" = a playful term for someone who is being delusional or unrealistic, often used in a teasing or affectionate way to describe someone who is holding onto fantasies or misconceptions about a situation, person, or outcome
- "main character energy" = a term used to describe someone who is acting as if they are the protagonist of a story, often in a way that is confident, self-assured, or attention-seeking, especially in social media contexts where it can be used to describe someone who is presenting themselves as the center of attention or the most important person in a given situation
- "-core" = a suffix used to describe a particular aesthetic, style, or subculture, often used in fashion, music, or social media contexts to categorize and identify specific trends or themes (e.g., "cottagecore" to describe a romanticized rural lifestyle aesthetic)
- "mid" = mediocre or average, often used to describe something that is underwhelming or not up to expectations

For Millennials (born 1981-1996):
- "#firstworldproblems" = a hashtag used to mock or highlight trivial complaints that are only relevant to people in wealthy, developed countries
- "#goals" = a hashtag used to express admiration for something that is seen as desirable or aspirational, often used in the context of relationships, lifestyle, or achievements
- "Adulting" = performing tasks associated with being a responsible adult
- "#relatable" = something that resonates with common experiences
- "FOMO" = Fear Of Missing Out, anxiety that an exciting event may be happening elsewhere
- "High-Key" = Very obvious or intense.
- "Spill the tea" = share gossip or personal information
- "YOLO" = You Only Live Once, used to justify impulsive or adventurous behavior
- "Take the L" = to experience a loss or failure, often used humorously
- "Throw shade" = to subtly insult or criticize someone
- "Yas" = an enthusiastic way to say "yes", often used to express excitement or approval
- "Slay" = to do something exceptionally well or to look amazing while doing it
- "Squad" = a group of friends or associates
- "Extra" = over the top, excessive, or dramatic behavior
- "Epic fail" = a complete and often humorous failure
- "Ghosting" = suddenly cutting off all communication with someone, often in a dating context
- "Fugly" = a slang term for something that is unattractive or unpleasant to look at
- "Bae" = a term of endearment for a significant other, derived from
- "Salty" = being bitter or upset about something, often used in a playful or teasing way
- "Woke" = being aware of social injustices and issues, often used in a positive sense but sometimes sarcastically to criticize performative activism
- "Basic" = a term used to describe someone or something that is unoriginal, mainstream, or conformist, often used in a playful or teasing way
- "Chill" = to relax or calm down, often used in a casual or friendly way
- "Lit" = exciting, fun, or excellent, often used to describe parties or events
- "Tripping" = acting irrationally or overreacting, often used to describe someone who is perceived as being overly sensitive or dramatic about a situation
- "Cringe" = something that is embarrassing or awkward, often used to describe content on social media that is perceived as trying too hard or being out of touch
- "Peace out" = a casual way to say goodbye, often associated with the counterculture of the 1960s and 1970s, and sometimes used by older generations in a playful or nostalgic way.
- "Vibes" = the emotional atmosphere or feeling that a person, place, or thing gives off, often used in a casual or social media context to describe the overall mood or energy of a situation (e.g., "good vibes" to describe a positive and enjoyable atmosphere)


For Gen X (born 1965-1980):
- "Here's the deal" = an introduction to an explanation or summary
- "Whatever" = an expression of indifference or dismissal
- "Not my circus, not my monkeys" = a way to say that a situation is not one's responsibility or concern
- "It is what it is" = an acceptance of a situation that cannot be changed
- "Dude/Dudette" = informal terms for a person, often used to address someone in a casual way
- "Duh" = an expression used to indicate that something is obvious or should be common knowledge
- "Take a chill pill" = a way to tell someone to calm down or relax
- "Bummer" = a term used to describe a disappointing or unfortunate situation
- "Clutch" = something that is done successfully under pressure, often in a critical moment
- "On point" = something that is accurate, well-executed, or perfectly suited
- "Binge-watch" = to watch multiple episodes of a TV show in one sitting
- "Beat around the bush" = to avoid getting to the point or discussing something directly
- "Break the internet" = to cause a huge sensation online, often by posting something that goes viral
- "Burnout" = a state of physical, emotional, and mental exhaustion caused by prolonged
- "Couch potato" = a person who spends a lot of time sitting and watching TV, often used to describe someone who is lazy or inactive
- "Hangry" = a state of being irritable or angry due to hunger
- "Diss" = to disrespect or criticize someone, often in a public way
- "Props" = respect or credit for something well done
- "Catch you on the flip side" = a way to say goodbye, implying that you will see someone again later, often used in a casual or friendly way.

For Boomers (born 1946-1964):
- "IMPORTANT UPDATE" = a phrase to signal critical information
- "pertinent information" = relevant details that are important to know
- "regarding today's events" = about what is happening currently in the news or world affairs
- "Back in my day" = a phrase used to compare current events or situations to the past, often implying that things were better or simpler before
- "Kids these days" = a phrase used to generalize about the younger generation, often in a critical or dismissive way
- "In my experience" = a way to preface advice or opinions based on personal history
- "You can't teach an old dog new tricks" = an expression meaning that it's difficult to change someone's habits or ways of thinking, especially as they get older
- "Get off my lawn" = a humorous way to tell others to stay away or stop bothering you, often used by older people in a playful or exaggerated manner
- "Don't let the name throw you" = a phrase used to caution someone not to make assumptions based on a title or label, often implying that something may be different than it appears.
- "Cutting-edge" = a term used to describe something that is very modern, innovative, or advanced, often in technology or science contexts.
- "Old-school" = a term used to describe something that is traditional, classic, or from an earlier era, often with a sense of nostalgia or respect for the past.
- "Silver surfer" = a humorous term for an older person who is adept at using the internet and technology, often used in a lighthearted or self-deprecating way.
- "Boomerang" = a term used to describe a situation where something comes back to affect the person who initiated it, often used in the context of social media or online behavior.
- "Groovy" = a term from the 1960s and 1970s used to describe something that is cool, fashionable, or enjoyable, often associated with the counterculture of that era.
- "Far out" = an expression from the 1960s and 1970s used to describe something that is impressive, unusual, or exciting, often associated with the counterculture of that era.
- "Right on" = an expression of agreement or approval, often used in the 1960s and 1970s, associated with the counterculture of that era.


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
