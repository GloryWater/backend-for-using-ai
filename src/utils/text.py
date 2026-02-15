_PREFIXES_TO_STRIP = [
    "Выход:",
    "Ответ:",
    "Result:",
    "Output:",
    "```json",
    "```",
]


def clean_llm_output(text: str) -> str:
    """Убирает типичные артефакты LLM-вывода: markdown-обёртки, префиксы, кавычки."""
    text = text.strip()

    for prefix in _PREFIXES_TO_STRIP:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    return text
