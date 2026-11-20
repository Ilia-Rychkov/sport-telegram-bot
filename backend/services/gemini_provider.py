import os
import logging
import asyncio
from google import genai
from google.genai import types
from backend.services.interfaces.ai_provider import IAIProvider

logger = logging.getLogger(__name__)

class GeminiProvider(IAIProvider):
    """Провайдер для работы с Gemini через воркер."""

    def __init__(self, api_key: str, base_url: str, model: str = "gemini-3.5-flash-lite"):
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(base_url=base_url)
        )
        self.model = model

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_mime_type: str | None = None
    ) -> str | None:
        config = types.GenerateContentConfig(temperature=temperature)
        if max_tokens:
            config.max_output_tokens = max_tokens
        if response_mime_type:
            config.response_mime_type = response_mime_type

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                ),
                timeout=30.0
            )
            return response.text
        except asyncio.TimeoutError:
            logger.error("Таймаут при запросе к Gemini")
            return None
        except Exception as e:
            logger.error(f"Ошибка Gemini: {e}")
            return None