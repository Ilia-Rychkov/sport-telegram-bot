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

        # 3 попытки с паузой
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config
                    ),
                    timeout=60.0
                )
                return response.text
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут (попытка {attempt + 1}/3)")
                if attempt == 2:
                    return None
                await asyncio.sleep(3)
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    logger.warning(f"Google перегружен (503). Попытка {attempt + 1}/3")
                    if attempt == 2:
                        return None
                    await asyncio.sleep(5)  # Ждем 5 секунд перед повтором
                else:
                    logger.error(f"Ошибка Gemini: {e}")
                    return None