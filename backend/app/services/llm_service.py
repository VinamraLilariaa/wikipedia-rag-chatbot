from groq import Groq
from backend.app.config.settings import GROQ_API_KEY, GROQ_MODEL

class LLMService:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self, question: str, context: str, history: list = None) -> str:
        """
        Grounded generation with history support.
        """
        # 1. Construct the RAG Prompt
        prompt = f"""
You are an Iron-Clad Wikipedia Research Analyst. 
Answer using ONLY the provided Wikipedia context.

STRICT OPERATING PROCEDURES:
1. ANSWER ONLY from the snippets below.
2. If info is NOT present, state: "I could not find a specific answer in the retrieved Wikipedia article."
3. DO NOT use outside knowledge.

Context Snippets:
{context}

User Question:
{question}

Final Answer:
"""
        
        # 2. Build the Message Chain (including history)
        messages = [{"role": "system", "content": "You are a restricted research AI."}]
        
        # Convert history objects to Groq format
        if history:
            for msg in history[-4:]:
                role = "assistant" if msg.get("role") == "bot" else "user"
                content = msg.get("content") or msg.get("text") or ""
                if content:
                    messages.append({"role": role, "content": content})
        
        # Add the current RAG prompt
        messages.append({"role": "user", "content": prompt})

        # 3. Call Groq
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            from backend.app.utils.logger import logger
            logger.error(f"Groq generation failed: {e}")
            return "I could retrieve the data but had trouble synthesizing the answer. Here is the context: " + context[:300]

    def simple_generate(self, prompt: str) -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_MODEL,
                temperature=0.1,
                max_tokens=100,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return ""