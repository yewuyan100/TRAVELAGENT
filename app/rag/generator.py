from openai import OpenAI

from app.config import settings


class LLMGenerator:
    def __init__(self):
        self.client = None
        if settings.llm_api_key:
            self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def generate(self, prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("缺少 LLM_API_KEY，无法调用大模型。请在 .env 中配置后再生成回答。")

        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content
