import httpx

from backend.app.config.settings import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)


class LLMService:

    def __init__(self):
        self.url = f"{OLLAMA_BASE_URL}/api/generate"

    def generate(
        self,
        question: str,
        context: str,
    ) -> str:

        prompt = f"""
You are a Wikipedia assistant.

Use ONLY the retrieved context below to answer the user's question.

If the answer is not explicitly present in the context, reply exactly:

"I could not find the answer in the retrieved Wikipedia article."

Do not use outside knowledge.
Do not make up facts.
Answer in a concise paragraph.

Context:
{context}

Question:
{question}

Answer:
"""

        response = httpx.post(
            self.url,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        try:
            data = response.json()
        except Exception:
            raise Exception(
                f"Ollama did not return valid JSON.\nResponse:\n{response.text}"
            )

        return data.get("response", "").strip()