import os
from typing import Any

from ..llm import get_llm


def _load_prompt_template() -> str:
    prompt_file = os.path.join(os.path.dirname(__file__), "..", "prompts", "basic_chat.txt")
    prompt_file = os.path.normpath(prompt_file)
    with open(prompt_file, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def _build_prompt(user_message: str, user_email: str) -> str:
    template = _load_prompt_template()
    return template.replace("{user_message}", user_message).replace("{user_email}", user_email)


def _parse_assistant_response(response_text: str) -> str:
    return response_text.strip()


def run_chat_chain(user_message: str, user_email: str = "") -> str:
    prompt = _build_prompt(user_message=user_message, user_email=user_email)

    llm = get_llm()
    raw_result = llm.generate([prompt])

    output_text = raw_result.generations[0][0].text if raw_result.generations else ""
    return _parse_assistant_response(output_text)
