import asyncio
import json
import re
from typing import Any, Awaitable, Callable, Iterable, List, TypeVar

import tiktoken
from langchain_core.messages import HumanMessage

import config

T = TypeVar("T")

PERMANENT_ERROR_MARKERS = (
    "model_decommissioned",
    "invalid_api_key",
    "api_key_invalid",
    "api key not valid",
    "invalid argument provided to gemini",
    "invalid_request_error",
)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def estimate_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def trim_to_tokens(text: str, max_tokens: int) -> str:
    if estimate_tokens(text) <= max_tokens:
        return text

    words = text.split()
    low, high = 0, len(words)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = " ".join(words[:mid])
        if estimate_tokens(candidate) <= max_tokens:
            low = mid
        else:
            high = mid - 1
    return " ".join(words[:low])


def chunk_text(text: str, max_tokens: int = config.MAX_CONTENT_LEN) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    if estimate_tokens(text) <= max_tokens:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    current: List[str] = []

    for paragraph in paragraphs or [text]:
        candidate = "\n\n".join(current + [paragraph])
        if estimate_tokens(candidate) <= max_tokens:
            current.append(paragraph)
            continue

        if current:
            chunks.append("\n\n".join(current))
            current = []

        if estimate_tokens(paragraph) > max_tokens:
            chunks.append(trim_to_tokens(paragraph, max_tokens))
        else:
            current = [paragraph]

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def normalize_url(url: str) -> str:
    return (url or "").split("#", 1)[0].rstrip("/")


def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_json_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def is_permanent_provider_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in PERMANENT_ERROR_MARKERS)


async def with_retries(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    label: str = "operation",
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if is_permanent_provider_error(exc):
                raise RuntimeError(f"{label} failed with a permanent provider error: {exc}") from exc
            if attempt == retries:
                break
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  ! {label} failed on attempt {attempt}: {exc}. Retrying in {delay:.1f}s")
            await asyncio.sleep(delay)

    raise RuntimeError(f"{label} failed after {retries} attempts: {last_error}")


def source_digest(items: Iterable[Any], max_chars_per_source: int = 1800) -> str:
    lines: List[str] = []
    for index, item in enumerate(items, start=1):
        if not getattr(item, "success", False):
            continue
        content = trim_to_tokens(getattr(item, "content", ""), max_chars_per_source // 4)
        lines.append(
            f"[{index}] {getattr(item, 'title', 'Untitled')}\n"
            f"URL: {getattr(item, 'url', '')}\n"
            f"Content: {content}"
        )
    return "\n\n".join(lines)


async def ainvoke_llm(prompt: str, label: str = "LLM call") -> str:
    if not config.GROQ_API_KEY and not config.GOOGLE_API_KEY:
        raise RuntimeError("No LLM API key is set. Configure GROQ_API_KEY or GOOGLE_API_KEY.")

    async def call_primary() -> str:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model=config.PRIMARY_MODEL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return str(response.content)

    async def call_fallback() -> str:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            api_key=config.GOOGLE_API_KEY,
            model=config.FALLBACK_MODEL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return str(response.content)

    primary_error: Exception | None = None
    if config.GROQ_API_KEY:
        try:
            return await with_retries(call_primary, retries=config.LLM_RETRIES, label=f"{label} via Groq")
        except Exception as exc:
            primary_error = exc
            print(f"  ! Groq failed for {label}: {primary_error}")

    if config.GOOGLE_API_KEY:
        if primary_error:
            print("  → Trying Gemini fallback")
        try:
            return await with_retries(call_fallback, retries=2, label=f"{label} via Gemini")
        except Exception as fallback_error:
            details = f"Groq: {primary_error}; Gemini: {fallback_error}" if primary_error else str(fallback_error)
            raise RuntimeError(f"{label} failed with configured LLM providers. {details}") from fallback_error

    raise RuntimeError(f"{label} failed with Groq and no Gemini fallback key is configured. Groq: {primary_error}")
