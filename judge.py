import json
import requests


class Judge:
    """
    Local LLM Judge using Ollama (Qwen2.5:7B)

    Evaluates:
        - Correctness
        - Groundedness
        - Completeness
        - Hallucination Risk
        - Confidence
        - Manual Score
    """

    def __init__(
        self,
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
    ):

        self.model = model

        self.url = base_url.rstrip("/") + "/api/generate"

    # ----------------------------------------------------------

    def evaluate(
        self,
        question,
        answer,
        context,
    ):

        prompt = f"""
You are an expert evaluator for a Wikipedia RAG system.

Evaluate ONLY the quality of the answer.

Question:
{question}

Retrieved Wikipedia Context:
{context}

IMPORTANT:
The retrieved context above is the ONLY source of truth.

Evaluate the answer ONLY using this context.

Do NOT use your own knowledge.

If the answer includes information not present in the context,
reduce Groundedness.

If the answer contradicts the context,
Correctness must be below 40.

If the context itself does not contain enough information,
do NOT assume facts.

Model Answer:
{answer}

Evaluate:

1. correctness (0-100)

2. groundedness (0-100)

3. completeness (0-100)

4. hallucination

Must be exactly one of:

LOW
MEDIUM
HIGH

5. confidence (0-100)

6. manual_score

Must be:

1
2
3
4
5

7. comments

Maximum 20 words.

Respond ONLY with valid JSON.

IMPORTANT SCORING RULES

100 = Nearly perfect Wikipedia answer.

95–99 = Excellent.

85–94 = Good.

70–84 = Acceptable.

50–69 = Weak.

0–49 = Incorrect.

Never give 100 unless the answer is essentially flawless.

Most correct answers should score between 88 and 96.
"""

        payload = {

            "model": self.model,

            "prompt": prompt,

            "stream": False,

            "options": {

                "temperature": 0,

                "top_p": 0.1,

                "num_predict": 180

            }

        }

        try:

            response = requests.post(

                self.url,

                json=payload,

                timeout=120,

            )

            response.raise_for_status()

            result = response.json()

            text = result["response"].strip()
            # ------------------------------------
            # Clean markdown if the model returns it
            # ------------------------------------

            if text.startswith("```"):
                text = (
                    text.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            data = json.loads(text)

            # ------------------------------------
            # Ensure every required key exists
            # ------------------------------------

            defaults = {
                "correctness": 0,
                "groundedness": 0,
                "completeness": 0,
                "hallucination": "MEDIUM",
                "confidence": 0,
                "manual_score": 1,
                "comments": "No comments."
            }

            for key, value in defaults.items():
                if key not in data:
                    data[key] = value

            # ------------------------------------
            # Type safety
            # ------------------------------------

            data["correctness"] = int(data["correctness"])
            data["groundedness"] = int(data["groundedness"])
            data["completeness"] = int(data["completeness"])
            data["confidence"] = int(data["confidence"])
            data["manual_score"] = int(data["manual_score"])

            data["hallucination"] = str(
                data["hallucination"]
            ).upper()

            data["comments"] = str(
                data["comments"]
            )

            # ------------------------------------
            # Clamp numeric ranges
            # ------------------------------------

            data["correctness"] = max(
                0,
                min(100, data["correctness"])
            )

            data["groundedness"] = max(
                0,
                min(100, data["groundedness"])
            )

            data["completeness"] = max(
                0,
                min(100, data["completeness"])
            )

            data["confidence"] = max(
                0,
                min(100, data["confidence"])
            )

            data["manual_score"] = max(
                1,
                min(5, data["manual_score"])
            )

            if data["hallucination"] not in [
                "LOW",
                "MEDIUM",
                "HIGH"
            ]:
                data["hallucination"] = "MEDIUM"

            return data

        except Exception as e:

            return {

                "correctness": 0,

                "groundedness": 0,

                "completeness": 0,

                "hallucination": "HIGH",

                "confidence": 0,

                "manual_score": 1,

                "comments": f"Judge Error: {e}"

            }