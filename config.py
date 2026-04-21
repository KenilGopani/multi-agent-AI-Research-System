import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "gemini-1.5-flash"
TEMPERATURE = 0.1
MAX_TOKENS = 4000

SCRAPE_TIMEOUT = 10
MAX_CONTENT_LEN = 3000
MAX_URLS = 5

MAX_REVISIONS = 2
LLM_RETRIES = 3
SEARCH_RETRIES = 3
SCRAPER_DELAY_SECONDS = 1

LOW_QUALITY_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "quora.com",
    "reddit.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
}
