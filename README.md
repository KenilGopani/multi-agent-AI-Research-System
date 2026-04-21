# Multi-Agent AI Research System

An autonomous research pipeline built with LangChain, LangGraph, Tavily, BeautifulSoup, Groq, and Gemini fallback support.

Given a user query, the system:

1. Generates optimized web search queries.
2. Searches the web with Tavily.
3. Scrapes and cleans relevant source pages.
4. Writes a structured markdown research report.
5. Reviews the report for quality and factual grounding.
6. Revises automatically until approved or the revision limit is reached.

## Tech Stack

- **Graph orchestration:** LangGraph
- **LLM orchestration:** LangChain
- **Primary LLM:** Groq `llama-3.3-70b-versatile`
- **Fallback LLM:** Google Gemini `gemini-1.5-flash`
- **Search:** Tavily Search API
- **Scraping:** requests, httpx, BeautifulSoup4, lxml
- **Schemas:** Pydantic v2, TypedDict
- **Environment:** python-dotenv

No OpenAI or Anthropic backend APIs are used.

## Project Structure

```text
multi_agent_research/
├── .env.example
├── README.md
├── requirements.txt
├── main.py
├── config.py
├── state.py
├── agents/
│   ├── __init__.py
│   ├── research_agent.py
│   ├── scraper_agent.py
│   ├── writer_agent.py
│   └── reviewer_agent.py
├── tools/
│   ├── __init__.py
│   ├── search_tool.py
│   └── scraper_tool.py
├── graph/
│   ├── __init__.py
│   └── research_graph.py
├── prompts/
│   ├── __init__.py
│   ├── research_prompts.py
│   ├── writer_prompts.py
│   └── reviewer_prompts.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

## Requirements

- Python 3.10+ recommended
- Groq API key
- Tavily API key
- Optional Google API key for Gemini fallback

The project was tested locally with Python 3.9.6, but some Google packages warn that Python 3.9 is past support. Use Python 3.10 or newer for the cleanest setup.

## Setup

From this directory:

```bash
cd /Users/spartan/Downloads/doc-ai/multi_agent_research
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

`GOOGLE_API_KEY` is optional. If it is missing, the system will use only Groq. If it is present but invalid, Gemini fallback calls will fail.

## Running

Run the full research pipeline:

```bash
.venv/bin/python main.py "Impact of AI on healthcare in 2025"
```

Another example:

```bash
.venv/bin/python main.py "Latest developments in quantum computing 2025"
```

You should see progress logs for each LangGraph node:

```text
Research agent: generating optimized search queries
Research agent: searching 3 query variants
Scraper agent: extracting source content
Writer agent: drafting report
Reviewer agent: checking report quality
```

At the end, the CLI prints the final markdown report.

## Agent Pipeline

The graph is defined in `graph/research_graph.py`.

```text
research -> scrape -> write -> review -> finalize
                         ^        |
                         |        |
                         +--------+
```

If the reviewer returns `NEEDS_REVISION`, the graph loops back to the writer. Once the report is approved or the revision limit is reached, the graph finalizes the report.

## Agents

### Research Agent

File: `agents/research_agent.py`

- Uses an LLM to generate 3 optimized search queries.
- Searches Tavily with varied phrasings.
- Deduplicates URLs.
- Filters low-quality domains such as social media and forums.
- Returns ranked `SearchResult` objects.

### Scraper Agent

File: `agents/scraper_agent.py`

- Scrapes the top search results.
- Uses `requests` first and falls back to `httpx`.
- Removes scripts, styles, nav, footer, header, forms, and other noisy elements.
- Extracts article/main/content text.
- Marks short or failed pages as unsuccessful without crashing the pipeline.

### Writer Agent

File: `agents/writer_agent.py`

- Writes a markdown report from scraped source material.
- Includes review feedback on revision passes.
- Produces executive summary, key findings, detailed analysis, conclusion, and sources.

### Reviewer Agent

File: `agents/reviewer_agent.py`

- Reviews the report against the original query and source material.
- Requests valid JSON from the LLM.
- Strips markdown JSON fences before parsing.
- Falls back to a default `ReviewResult` if parsing fails.

## Configuration

Main settings live in `config.py`:

```python
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "gemini-1.5-flash"
TEMPERATURE = 0.1
MAX_TOKENS = 4000
SCRAPE_TIMEOUT = 10
MAX_CONTENT_LEN = 3000
MAX_URLS = 5
MAX_REVISIONS = 2
```

Groq previously supported `llama-3.1-70b-versatile`, but that model has been decommissioned. This project uses `llama-3.3-70b-versatile`.

## Troubleshooting

### Groq model decommissioned

If you see:

```text
The model `llama-3.1-70b-versatile` has been decommissioned
```

Make sure `config.py` uses:

```python
PRIMARY_MODEL = "llama-3.3-70b-versatile"
```

### Gemini API key invalid

If you see:

```text
API key not valid. Please pass a valid API key.
```

Fix `GOOGLE_API_KEY` in `.env`, or remove it if you only want to use Groq.

### Tavily key missing

If you see:

```text
TAVILY_API_KEY is not set
```

Add your Tavily key to `.env`:

```env
TAVILY_API_KEY=your_tavily_api_key_here
```

### NotOpenSSLWarning on macOS

You may see:

```text
urllib3 v2 only supports OpenSSL 1.1.1+
```

This warning usually appears with the system Python on macOS. The project may still run, but using a newer Python installation from Homebrew or pyenv is recommended.

### Python 3.9 support warnings

Google packages may warn that Python 3.9 is no longer supported. Upgrade to Python 3.10+ if possible.

## Development Checks

Compile the source files:

```bash
PYTHONPYCACHEPREFIX=/tmp/doc-ai-pycache .venv/bin/python -m compileall agents graph prompts tools utils config.py state.py main.py
```

Smoke test the graph:

```bash
.venv/bin/python -c "from graph.research_graph import build_graph; build_graph(); print('graph ok')"
```

## Notes

- A single failed URL will not crash the pipeline.
- Scraping includes a small delay between requests to reduce blocking risk.
- Network, search, and LLM calls use error handling and retry logic.
- The final report is printed to stdout; it is not written to disk by default.
