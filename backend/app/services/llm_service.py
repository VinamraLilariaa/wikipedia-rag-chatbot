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
You are an Iron-Clad Wikipedia Research Analyst. 

Your ONLY mission is to answer the question using ONLY the provided Wikipedia context.

STRICT OPERATING PROCEDURES:
1. ANSWER ONLY from the provided snippets below.
2. If the info is present, extract it precisely and explain it thoroughly.
3. If the info is NOT present in the snippets, you MUST reply exactly:
   "I could not find a specific answer in the retrieved Wikipedia article."
4. DO NOT use your own training data or outside knowledge.
5. DO NOT connect dots that are not explicitly written in the text.
6. If the question is about 'him/her', ensure you are referring to the subject described in the Main Section of the context.

Context Snippets:
{context}

User Question:
{question}

Final Answer:
"""

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a restricted research AI. You cannot speak without context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0, # Complete factual lockdown
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