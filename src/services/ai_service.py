import logging

from openai import AsyncOpenAI

from src.services.vector_store import VectorStore
from src.utils.text import clean_llm_output

logger = logging.getLogger(__name__)


class AIService:
    """Сервис редактирования объявлений с помощью LLM + RAG."""

    def __init__(
        self,
        llm: AsyncOpenAI,
        vector_store: VectorStore,
        rules: str,
        model_name: str,
        temperature: float = 0.3,
        max_tokens: int = 200,
    ):
        self._llm = llm
        self._vector_store = vector_store
        self._rules = rules
        self._model = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def edit_text(self, text: str) -> str:
        text = text.strip()

        if not text or all(not c.isalnum() and not c.isspace() for c in text):
            return "ОТКАЗ: Пустой запрос или мусор"

        try:
            examples = await self._build_examples_block(text)
            prompt = self._build_prompt(text, examples)

            response = await self._llm.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Ты ИИ-редактор объявлений."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                extra_body={"enable_thinking": False},
                stream=False,
            )

            result = clean_llm_output(response.choices[0].message.content)
            logger.info("[AI output]: %.100s…", result)
            return result

        except Exception as e:
            logger.error("LLM error: %s", e, exc_info=True)
            return text  # fail-safe: возвращаем оригинал

    # ── private ──────────────────────────────────────────────

    async def _build_examples_block(self, query: str) -> str:
        similar = await self._vector_store.find_similar(query)
        if not similar:
            logger.info("No similar examples above threshold.")
            return ""

        logger.info("Found %d similar examples for context.", len(similar))

        lines = []
        for item in similar:
            msgs = item.get("messages", [])
            user = next((m["content"] for m in msgs if m["role"] == "user"), "")
            model = next((m["content"] for m in msgs if m["role"] == "model"), "")
            lines.append(
                f"<input>{user}</input>\n<correct_output>{model}</correct_output>"
            )

        return (
            "\n<examples>\n"
            "Ниже приведены примеры того, как надо редактировать похожие объявления:\n"
            + "\n".join(lines)
            + "\n</examples>\n"
        )

    def _build_prompt(self, text: str, examples_block: str) -> str:
        return (
            f"{self._rules}\n"
            f"{examples_block}\n"
            f"<instruction>\n"
            f"Отредактируй следующий текст пользователя согласно правилам выше.\n"
            f"Входящий текст: {text}\n"
            f"Верни ТОЛЬКО отредактированный текст или причину отказа. "
            f"Никаких кавычек, markdown блоков или лишних слов.\n"
            f"</instruction>"
        )
