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
The context may include plain paragraphs as well as structured data taken
from Wikipedia infoboxes and tables (formatted as "Label: Value" lines or
as "|"-separated rows with a header row). Treat that structured data as
factual evidence, exactly like the surrounding prose.

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

    def simple_generate(self, prompt: str) -> str:
        """
        Simple prompt-to-response generation without specific RAG formatting.
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=GROQ_MODEL,
                temperature=0.1,
                max_tokens=100,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            from backend.app.utils.logger import logger
            logger.error(f"Groq simple generation failed: {e}")
            return ""