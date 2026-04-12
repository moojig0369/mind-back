import json
import time
import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.settings import get_settings
from app.schemas.analysis import LlmAnalysisResult, SeedInsightData
from app.services import prompt_builder

_log = logging.getLogger(__name__)
_settings = get_settings()


class LlmService:
    """LLM дуудалт болон хариулт боловсруулалт."""

    def __init__(self) -> None:
        base = _settings.llm_base_url
        self._client = AsyncOpenAI(
            api_key=_settings.llm_api_key,
            base_url=base if "openai.com" not in base else None,
        )

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

    # ── Private ───────────────────────────────────────────────────────────────

    async def _complete(self, messages: list[dict], caller: str = "llm") -> str:
        start = time.perf_counter()

        response = await self._client.chat.completions.create(
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
    """Markdown code block цэвэрлэж JSON parse хийнэ."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    return json.loads(text.strip())


_instance: LlmService | None = None


def get_llm_service() -> LlmService:
    global _instance
    if _instance is None:
        _instance = LlmService()
    return _instance