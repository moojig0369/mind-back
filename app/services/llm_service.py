import json
import time
import logging
import asyncio
import re
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from app.core.settings import get_settings
from app.schemas.analysis import LlmAnalysisResult, SeedInsightData
from app.services import prompt_builder

# Лог тохиргоо
_log = logging.getLogger(__name__)
_settings = get_settings()

def _is_vertex(base_url: str) -> bool:
    """URL нь Google Vertex AI endpoint мөн эсэхийг шалгах."""
    return "aiplatform.googleapis.com" in (base_url or "")

class _VertexTokenManager:
    """Google Cloud-ын access token-ийг автоматаар удирдаж, refresh хийнэ."""
    
    def __init__(self) -> None:
        try:
            import google.auth
            import google.auth.transport.requests as grequests
            # Cloud Platform scope нь Vertex AI-д хандахад шаардлагатай
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._request = grequests.Request()
        except ImportError:
            _log.error("❌ google-auth сан суугаагүй байна. 'pip install google-auth' ажиллуулна уу.")
            raise RuntimeError("Missing google-auth library.")
        self._expires_at: float = 0.0

    def token(self) -> str:
        """Хүчинтэй токен буцаана. Хугацаа дуусахаас 5 минутын өмнө шинэчилнэ."""
        if time.time() >= self._expires_at - 300:
            self._credentials.refresh(self._request)
            if self._credentials.expiry:
                self._expires_at = self._credentials.expiry.timestamp()
            else:
                self._expires_at = time.time() + 3600  # Fallback 1 цаг
            _log.debug("🔑 Vertex AI access token шинэчлэгдлээ.")
        return self._credentials.token

class LlmService:
    """LLM API-тай харилцах үндсэн сервис (OpenAI болон Vertex AI-г дэмжинэ)."""

    def __init__(self) -> None:
        self._base = _settings.llm_base_url
        self._vertex = _is_vertex(self._base)
        
        # Traffic Smoothing: Секундэд ирэх огцом spikes-ээс сэргийлж нэгэн зэрэг 
        # гарах хүсэлтийн тоог хязгаарлана (Concurrency control).
        self._semaphore = asyncio.Semaphore(10) 

        if self._vertex:
            self._token_mgr = _VertexTokenManager()
            self._client = self._make_vertex_client()
        else:
            self._token_mgr = None
            self._client = AsyncOpenAI(
                api_key=_settings.llm_api_key,
                base_url=self._base if "openai.com" not in self._base else None,
            )

    def _make_vertex_client(self) -> AsyncOpenAI:
        """Vertex AI-д зориулсан OpenAI-compatible клиент үүсгэх."""
        return AsyncOpenAI(
            api_key=self._token_mgr.token(),
            base_url=self._base,
        )

    def _get_client(self) -> AsyncOpenAI:
        """Токен шинэчлэгдсэн бол шинэ клиент буцаах."""
        if self._vertex:
            new_token = self._token_mgr.token()
            if new_token != self._client.api_key:
                self._client = self._make_vertex_client()
        return self._client

    # 429 Resource Exhausted болон Rate Limit алдаануудыг дахин оролдох стратеги
    # Exponential backoff: 4с, 8с, 16с... гэх мэтээр хүлээх хугацааг ихэсгэнэ.
    _retry_logic = retry(
        retry=retry_if_exception_type((RateLimitError, Exception)),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(6),
        before_sleep=before_sleep_log(_log, logging.WARNING)
    )

    # ── Seed Insight ──────────────────────────────────────────────────────────

    @_retry_logic
    async def generate_seed_insight(
        self,
        surface: str,
        inner: str,
        meaning: str,
    ) -> SeedInsightData:
        messages = prompt_builder.build_seed_messages(surface, inner, meaning)
        raw = await self._complete(messages, caller="seed_insight")

        parsed = _parse_json(raw)

        if not parsed.get("summary"):
            parsed["summary"] = parsed.get("mirror", "")[:120]
            _log.warning("⚠️ summary талбар дутуу байна - mirror-ээс авлаа.")

        return SeedInsightData(**parsed)

    # ── Analysis ──────────────────────────────────────────────────────────────

    @_retry_logic
    async def run_analysis(
        self,
        surface: str,
        inner: str,
        meaning: str,
        ewma_previous: Optional[float] = None,
    ) -> LlmAnalysisResult:
        messages = prompt_builder.build_analysis_messages(
            surface, inner, meaning, ewma_previous
        )
        raw = await self._complete(messages, caller="analysis")
        data = _parse_json(raw)
        prompt_builder.apply_ewma(data, ewma_previous)
        return LlmAnalysisResult(**data)

    # ── Deep Insight ──────────────────────────────────────────────────────────

    @_retry_logic
    async def generate_deep_insight(
        self, graph_summary: Dict[str, Any], entry_count: int
    ) -> Dict[str, Any]:
        messages = prompt_builder.build_deep_insight_messages(
            graph_summary, entry_count
        )
        raw = await self._complete(messages, caller="deep_insight")
        return _parse_json(raw)

    # ── Human Insight ─────────────────────────────────────────────────────────

    @_retry_logic
    async def generate_human_insight(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pattern жагсаалтаас human insight үүсгэнэ."""
        messages = prompt_builder.build_human_insight_messages(patterns)
        raw = await self._complete(messages, caller="human_insight")
        parsed = _parse_json(raw)
        
        return {
            "insight_text":   parsed.get("insight_text", ""),
            "highlight_type": parsed.get("highlight_type", ""),
            "strength_score": float(parsed.get("strength_score", 0.0)),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _complete(self, messages: List[Dict[str, str]], caller: str = "llm") -> str:
        """LLM-рүү хүсэлт илгээх үндсэн функц."""
        async with self._semaphore: # Traffic smoothing / Concurrency control
            start = time.perf_counter()

            response = await self._get_client().chat.completions.create(
                model=_settings.llm_model,
                messages=messages,
                temperature=_settings.llm_temperature,
                max_tokens=_settings.llm_max_tokens,
                response_format={"type": "json_object"},
            )

            elapsed = time.perf_counter() - start
            usage = response.usage

            _log.info(
                f"🤖 [{caller}] model={_settings.llm_model} | "
                f"tokens: p={usage.prompt_tokens}, c={usage.completion_tokens} | "
                f"time={elapsed:.2f}s"
            )

            content = response.choices[0].message.content
            if not content:
                _log.error(f"📥 [{caller}] LLM хоосон хариу буцаалаа.")
                return ""
                
            return content



def _parse_json(raw: str) -> dict:
    """Markdown болон илүүдэл текстийг цэвэрлэж JSON parse хийнэ."""
    if not raw:
        _log.error("❌ LLM-ээс хоосон хариу ирлээ")
        return {}

    text = raw.strip()

    # 1. Хэрэв Markdown блок дотор (```json ... ```) байвал сугалж авах
    if "```" in text:
        # Регуляр илэрхийллээр хамгийн гадна талын { } хоорондохыг авна
        match = re.search(r"({.*})", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Хэрэв match олдохгүй бол хуучин аргаараа мөр мөрөөр нь цэвэрлэх
            lines = text.splitlines()
            content_lines = [l for l in lines if not l.strip().startswith("```")]
            text = "".join(content_lines)

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        _log.error(f"❌ JSON Decode Error: {e} | Raw text: {text[:200]}...")
        
        # 2. Хэрэв JSON эвдэрсэн бол (жишээ нь төгсгөл дутуу) засах оролдлого
        # Энэ нь 'Unterminated string' алдаанд тусална
        try:
            # Хаагаагүй хаалт байгаа эсэхийг шалгаад нэмэх (энгийн нөхцөлд)
            if text.count('{') > text.count('}'):
                text += '}'
            return json.loads(text.strip())
        except:
            raise e # Хэрэв засагдахгүй бол үндсэн алдаагаа шиднэ

_instance: LlmService | None = None


def get_llm_service() -> LlmService:
    global _instance
    if _instance is None:
        _instance = LlmService()
    return _instance