from groq import Groq
import logging
from backend.app.config.settings import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, question: str, context: str, history: list = None) -> str:
        """
        Grounded RAG answer generation.
        Returns the answer string, or raises on Groq failure.
        """
        # Hard cap context to stay within Groq token limits
        safe_context = context[:5000]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a factual research assistant. "
                    "Answer questions using ONLY the provided Wikipedia context. "
                    "Be direct and factual. If the answer is not in the context, say: "
                    "'This information was not found in the retrieved Wikipedia article.'"
                ),
            },
            {
                "role": "user",
                "content": f"Wikipedia Context:\n{safe_context}\n\nQuestion: {question}",
            },
        ]

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()

    def simple_generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_MODEL,
                temperature=0.1,
                max_tokens=50,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""