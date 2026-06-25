from groq import Groq
from backend.app.config.settings import GROQ_API_KEY, GROQ_MODEL

class LLMService:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, question: str, context: str, history: list = None) -> str:
        """
        Grounded RAG generation. Answers only from provided Wikipedia context.
        """
        system_prompt = (
            "You are a Wikipedia research assistant. "
            "Answer the user's question using ONLY the provided Wikipedia context. "
            "If the answer is not in the context, say so clearly. "
            "Be concise and factual."
        )

        user_prompt = (
            f"Wikipedia Context:\n{context[:6000]}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=800,
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