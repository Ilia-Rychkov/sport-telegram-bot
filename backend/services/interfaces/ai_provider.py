from abc import ABC, abstractmethod
from typing import Optional

class IAIProvider(ABC):
    """Интерфейс для любого AI-провайдера (Gemini, OpenAI, Claude)."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None
    ) -> Optional[str]:
        """Возвращает сырой текстовый ответ от нейросети."""
        pass