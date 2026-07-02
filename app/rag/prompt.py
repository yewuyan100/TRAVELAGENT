from app.config import settings
from app.schemas import SourceRef


def build_reference_text(sources: list[SourceRef]) -> str:
    if not sources:
        return "本次没有可用来源。"

    lines = []
    for index, source in enumerate(sources, start=1):
        lines.append(
            f"{index}. {source.title}"
            f"（ID：{source.id}，城市：{source.city}，类别：{source.category}，分数：{source.score:.3f}）"
        )
    return "\n".join(lines)


def build_prompt(contexts: list[str], question: str, sources: list[SourceRef]) -> str:
    context_text = "\n\n".join(contexts)
    reference_text = build_reference_text(sources)

    return f"""
{settings.system_prompt}

【旅游资料】
{context_text}

【资料来源】
{reference_text}

【用户问题】
{question}

请根据资料直接回答用户问题。回答要自然、简洁，并在最后保留“依据：”列出使用到的来源标题。
""".strip()
