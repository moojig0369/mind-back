"""
AI/LLM infrastructure client.
Handles LLM API calls with retry logic and token management.
"""

import time
import logging
from typing import Optional, Dict, Any
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
