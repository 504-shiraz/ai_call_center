from ollama import Client
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:

    def __init__(self):
        self.client = Client(host=settings.OLLAMA_HOST)

    def chat(self, messages:list[dict]) -> str:
        started_at = time.perf_counter()
        logger.info("LLM request started model=%s messages=%d", settings.OLLAMA_MODEL, len(messages))
        try:
            response = self.client.chat(
                model=settings.OLLAMA_MODEL,
                messages=messages,
            )
            content = response["message"]["content"]
            logger.info("LLM request completed elapsed_ms=%.0f response_chars=%d", (time.perf_counter() - started_at) * 1000, len(content))
            return content
        except Exception:
            logger.exception("LLM request failed elapsed_ms=%.0f", (time.perf_counter() - started_at) * 1000)
            raise