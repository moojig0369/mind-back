"""
AI/LLM infrastructure client.
Handles LLM API calls with retry logic and token management.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.settings import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """LLM client for OpenAI-compatible APIs."""
    
    def __init__(self):
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url if self.base_url else None,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=8),
        reraise=True,
    )
    async def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Generate JSON response from LLM."""
        import json
        import re
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that responds in JSON format."},
            {"role": "user", "content": prompt},
        ]
        
        start_time = time.perf_counter()
        
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            response_format={"type": "json_object"},
        )
        
        elapsed = time.perf_counter() - start_time
        usage = response.usage
        
        logger.info(
            f"🤖 LLM call | model={model or self.model} | "
            f"prompt_tokens={usage.prompt_tokens} | "
            f"completion_tokens={usage.completion_tokens} | "
            f"time={elapsed:.2f}s"
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown or text
            match = re.search(r"({.*})", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Failed to parse JSON from LLM response: {e}")
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text response from LLM."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
        
        start_time = time.perf_counter()
        
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        
        elapsed = time.perf_counter() - start_time
        usage = response.usage
        
        logger.info(
            f"🤖 LLM text call | model={model or self.model} | "
            f"tokens={usage.total_tokens} | "
            f"time={elapsed:.2f}s"
        )
        
        return response.choices[0].message.content.strip()
    
    async def analyze_psychometrics(
        self,
        surface: str,
        inner: str,
        meaning: str,
        ewma_previous: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Психометрик шинжилгээ хийх:
        - Hawkins level (20-700)
        - Plutchik emotions (primary + dyad)
        - Maslow categories (top 3)
        - Crisis flag
        """
        prompt = f"""
Анализ хийх өгөгдөл:
- Surface (гадаргуу бодол): {surface}
- Inner Reaction (дотоод урвал): {inner}
- Meaning (утга учир): {meaning}
- Өмнөх EWMA: {ewma_previous if ewma_previous else 'байхгүй'}

Дараах JSON форматтай хариул:
{{
  "hawkins_level": <int 20-700>,
  "hawkins_label_en": "<string>",
  "hawkins_label_mn": "<string>",
  "plutchik_primary": "<emotion_key: joy, trust, fear, surprise, sadness, anger, disgust, anticipation>",
  "plutchik_dyad": "<dyad_name эсвэл null>",
  "maslow_categories": ["<code1>", "<code2>", "<code3>"],
  "crisis_flag": <boolean>,
  "confidence": <float 0-1>,
  "reasoning": "<товч тайлбар>"
}}

Hawkins түвшин:
- 20-175: Эго (ichih, gem, apati, uy gashuu, aidas, husel, uur, bardamnal)
- 200-499: Ажиглагч (zorig, tenthver, huvtsel, huuleh zovshuuruh, oyuun uhaan)
- 500-700: Гэгээрсэн (hair, bayar hohor, amar taivan, gegeerel)

Хэрэв хэрэглэгч амиа хорлох, өөртөө болон бусдад хор хөнөөл учруулах тухай ярьсан бол crisis_flag = true.

Maslow codes: physiological, safety, social, esteem, self_actualization
Plutchik emotions: joy, trust, fear, surprise, sadness, anger, disgust, anticipation
"""
        
        return await self.generate_json(prompt, max_tokens=500)
