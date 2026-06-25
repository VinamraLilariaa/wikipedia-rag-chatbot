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
You are a Professional Wikipedia Researcher. 

STRICT RULES for your answer:
1. Use ONLY the provided Wikipedia context (Summary and Sections) to answer.
2. If the answer is present, extract it precisely and answer thoroughly.
3. If the answer is NOT present in the provided context, you MUST reply exactly with:
   "I could not find a specific answer in the retrieved Wikipedia article."
4. DO NOT use outside knowledge. DO NOT make up details.
5. Keep your tone professional and objective.

Context from Wikipedia:
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
                    "content": "You are a professional research assistant grounded strictly in Wikipedia data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0, # Zero temperature for maximum factual reliability
            max_tokens=600,
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