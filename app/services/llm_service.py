import json
import time
import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.settings import get_settings
from app.schemas.analysis import LlmAnalysisResult, SeedInsightData
from app.services import prompt_builder
import re  # Файлын хамгийн дээр import re нэмэхээ мартав аа!

_log = logging.getLogger(__name__)
_settings = get_settings()

# Vertex AI OpenAI-compatible endpoint format
_VERTEX_BASE = (
    "https://{region}-aiplatform.googleapis.com/v1beta1/projects/"
    "{project}/locations/{region}/endpoints/openapi"
)


def _is_vertex(base_url: str) -> bool:
    return "aiplatform.googleapis.com" in (base_url or "")


class _VertexTokenManager:
    """Google access token-ийг авч, хугацаа дуусахад refresh хийнэ."""

    def __init__(self) -> None:
        try:
            import google.auth
            import google.auth.transport.requests as grequests
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._request = grequests.Request()
        except ImportError:
            raise RuntimeError(
                "google-auth байхгүй байна. "
                "`pip install google-auth` ажиллуулна уу."
            )
        self._expires_at: float = 0.0

    def token(self) -> str:
        """Token буцаана; хугацаа дуусахаас 5 мин өмнө refresh хийнэ."""
        if time.time() >= self._expires_at - 300:
            self._credentials.refresh(self._request)
            # google-auth expiry нь datetime эсвэл None байж болно
            if self._credentials.expiry:
                self._expires_at = self._credentials.expiry.timestamp()
            else:
                self._expires_at = time.time() + 3600  # fallback 1 цаг
            _log.debug("🔑 Vertex AI token refresh хийлээ")
        return self._credentials.token


class LlmService:
    """LLM дуудалт болон хариулт боловсруулалт."""

    def __init__(self) -> None:
        self._base = _settings.llm_base_url
        self._vertex = _is_vertex(self._base)

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
        return AsyncOpenAI(
            api_key=self._token_mgr.token(),
            base_url=self._base,
        )

    def _get_client(self) -> AsyncOpenAI:
        """Vertex бол token шинэчлэгдсэн client буцаана."""
        if self._vertex:
            # Token шинэчлэгдсэн бол client-ийг дахин үүсгэнэ
            new_token = self._token_mgr.token()
            if new_token != self._client.api_key:
                self._client = AsyncOpenAI(
                    api_key=new_token,
                    base_url=self._base,
                )
        return self._client

    # ── Seed Insight ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(1), wait=wait_exponential(min=2, max=8))
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
            _log.warning("⚠️  summary дутуу — mirror-ээс авлаа")

        return SeedInsightData(**parsed)

    # ── Analysis ──────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(1), wait=wait_exponential(min=2, max=8))
    async def run_analysis(
        self,
        surface: str,
        inner: str,
        meaning: str,
        ewma_previous: float | None = None,
    ) -> LlmAnalysisResult:
        messages = prompt_builder.build_analysis_messages(
            surface, inner, meaning, ewma_previous
        )
        raw = await self._complete(messages, caller="analysis")
        data = _parse_json(raw)
        prompt_builder.apply_ewma(data, ewma_previous)
        return LlmAnalysisResult(**data)

    # ── Deep Insight ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(1), wait=wait_exponential(min=2, max=8))
    async def generate_deep_insight(
        self, graph_summary: dict, entry_count: int
    ) -> dict:
        messages = prompt_builder.build_deep_insight_messages(
            graph_summary, entry_count
        )
        raw = await self._complete(messages, caller="deep_insight")
        return _parse_json(raw)

    @retry(stop=stop_after_attempt(1), wait=wait_exponential(min=2, max=8))
    async def generate_human_insight(self, patterns: list[dict]) -> dict:
        """
        Pattern жагсаалтаас монгол хэлний human insight үүсгэнэ.
        {"insight_text": str, "highlight_type": str, "strength_score": float}
        """
        messages = prompt_builder.build_human_insight_messages(patterns)
        raw = await self._complete(messages, caller="human_insight")
        parsed = _parse_json(raw)
        return {
            "insight_text":   parsed.get("insight_text", ""),
            "highlight_type": parsed.get("highlight_type", ""),
            "strength_score": float(parsed.get("strength_score", 0.0)),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _complete(self, messages: list[dict], caller: str = "llm") -> str:
        start = time.perf_counter()

        response = await self._get_client().chat.completions.create(
            model=_settings.llm_model,
            messages=messages,
            temperature=_settings.llm_temperature,
            max_tokens=_settings.llm_max_tokens,
            response_format={"type": "json_object"},
        )

        elapsed = time.perf_counter() - start
        u = response.usage

        _log.info(
            f"🤖 [{caller}] model={_settings.llm_model} | "
            f"prompt={u.prompt_tokens} | "
            f"completion={u.completion_tokens} | "
            f"total={u.total_tokens} | "
            f"time={elapsed:.2f}s"
        )

        content = response.choices[0].message.content
        _log.debug(f"📥 [{caller}] raw response: {content}")

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