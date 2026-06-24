from groq import Groq

from backend.app.config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
)


class LLMService:

    def __init__(self):

        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY not found in .env"
            )

        self.client = Groq(
            api_key=GROQ_API_KEY
        )

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

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful Wikipedia assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=512,
        )

        return response.choices[0].message.content.strip()