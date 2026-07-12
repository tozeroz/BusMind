from __future__ import annotations

SYSTEM_PROMPT = (
    "你是 BusMind 的公交出行助理。"
    "请优先基于给定的结构化路线数据回答，保持简洁、清晰、可靠。"
    "当数据不足时，明确说明不确定性，不要编造路线或实时信息。"
)


def build_user_prompt(mode: str, question: str | None, context_text: str) -> str:
    question_text = question or "请根据当前路线信息给出建议。"
    return (
        f"模式: {mode}\n"
        f"用户问题: {question_text}\n"
        f"路线数据: {context_text}\n"
        "请结合路线耗时、拥挤程度、步行时间和换乘次数进行回答。"
    )
