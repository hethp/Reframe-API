# Reframe-API
This project is a Chrome extension and backend API designed to make news more accessible, understandable, and unbiased. It fetches current news articles, analyzes them for bias, and uses AI to generate neutral summaries. It also features a translation mode that rewrites headlines into generation-specific dialects.

It was originally conceptualized as a hackathon project targeting categories like the Stripe track, most creative, and beginner hack.

Core Features
Bias and Sentiment Analyzer: Uses NLP to evaluate the original article and determine its political or ideological leaning. It returns a scale indicating what percentage the article leans toward a specific bias or if it is neutral.

Unbiased AI Summaries: Takes polarized news blurbs and uses an LLM to strip the bias, generating a neutral, factual summary.

Generational Translation: Rephrases news titles and blurbs to match specific generational reading styles:

Gen Alpha: Heavy internet slang (level 6 to 7 brainrot).

Gen Z: Modern internet terminology.

Millennial: Standard modern conversational tone.

Gen X: Traditional, straightforward newspaper style.

Boomer: Traditional phrasing with large font accessibility implemented on the frontend.

Interactive Clarification: Users can query the API directly to ask the LLM for further clarification or extended summaries of the current article.

Example Framing
Original Context: Trump orders government to stop using Anthropic in battle over AI use

Left-leaning framing: Donald Trump orders government to blacklist Anthropic, intensifying crackdown on AI industry rivals.

Neutral framing: Trump directs federal agencies to stop using Anthropic amid dispute over government AI deployment.

Right-leaning framing: Trump moves to bar Anthropic from federal use, emphasizing oversight and security concerns around AI.

Architecture
Frontend: Chrome Extension (HTML, CSS, JavaScript)

Backend: Python (Flask or FastAPI)

Data Sources: News APIs like NewsData.io, NewsAPI.org, GNews, or standard RSS feeds.

AI/NLP: LLM integration for summarization, generation, bias detection, and interactive Q&A.

Installation and Setup
Prerequisites

You will need Python installed on your machine and an active API key from a news provider like NewsAPI.org.

Backend Setup

Clone the repository to your local machine.

Install the required Python dependencies.

Add your external News API key to your environment variables.

Example backend structure for fetching the news data:

Python
import requests

def fetch_headlines():
    url = "https://newsapi.org/v2/top-headlines"
    params = {
       "country": "us",
       "apiKey": "YOUR_KEY" # Replace with environment variable
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Process articles, pass to LLM for transformation, and return structured response
    return data
Frontend Setup

Open Google Chrome and navigate to chrome://extensions/.

Enable "Developer mode" in the top right corner.

Click "Load unpacked" and select the extension folder from this repository.

Usage
Once the extension is installed and your backend server is running locally, click the extension icon in your browser. The tool will parse the current news data, display the NLP bias score, offer an unbiased summary, and allow the user to toggle through the generational framing options.