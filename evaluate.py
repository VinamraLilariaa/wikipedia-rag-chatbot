"""
Professional Wikipedia RAG Evaluator
------------------------------------

Pipeline:

Excel
   ↓
HF Space
   ↓
Model Answer
   ↓
Groq Judge
   ↓
Filled Excel

Author: Tanav
"""

import argparse
import time
import pandas as pd
import requests
from judge import Judge


# ----------------------------
# Configuration
# ----------------------------

TIMEOUT = 90
CHECKPOINT_INTERVAL = 25


# ----------------------------
# Evaluator Class
# ----------------------------

class Evaluator:

    def __init__(self, api_url):

        self.endpoint = api_url.rstrip("/") + "/api/ask"

        self.session = requests.Session()

        self.judge = Judge()

        self.success = 0

        self.failure = 0

    # ---------------------------------------

    def ask_rag(self, question):

        start = time.time()

        response = self.session.post(

            self.endpoint,

            json={
                "question": question,
                "history": []
            },

            timeout=TIMEOUT

        )

        elapsed = int((time.time() - start) * 1000)

        response.raise_for_status()

        data = response.json()

        return {

            "answer":
                data.get("answer", ""),

            "article":
                data.get("article", ""),

            "images":
                data.get("images", []),

            "response_time":
                elapsed
        }

    # ---------------------------------------

    def evaluate_answer(
        self,
        question,
        rag_result,
    ):

        return self.judge.evaluate(

            question,

            rag_result["answer"]

        )
# ----------------------------------------------------------
# Main Evaluation
# ----------------------------------------------------------

def run_evaluation(
    input_file,
    question_col,
    api_base,
    delay,
    output_file,
):

    print(f"\nLoading {input_file}")

    df = pd.read_excel(input_file)

    if question_col not in df.columns:
        raise ValueError(
            f"Column '{question_col}' not found."
        )

    evaluator = Evaluator(api_base)

    total = len(df)

    print(f"Questions : {total}\n")

    # --------------------------------------------------

    for index, row in df.iterrows():

        question = str(row[question_col]).strip()

        print(
            f"[{index+1}/{total}] {question}"
        )

        try:

            # --------------------------
            # Ask RAG
            # --------------------------

            rag = evaluator.ask_rag(question)

            # --------------------------
            # Judge
            # --------------------------

            scores = evaluator.judge.evaluate(

                question=question,

                answer=rag["answer"],

                article=rag["context"],

            )

            # --------------------------
            # Fill Excel
            # --------------------------

            df.loc[index, "Model Answer"] = rag["answer"]

            df.loc[index, "Confidence Score"] = scores["confidence"]

            df.loc[index, "Manual Testing Score"] = scores["manual_score"]

            df.loc[index, "Comments"] = scores["comments"]

            # --------------------------
            # Optional diagnostic columns
            # --------------------------

            df.loc[index, "Correctness"] = scores["correctness"]

            df.loc[index, "Groundedness"] = scores["groundedness"]

            df.loc[index, "Completeness"] = scores["completeness"]

            df.loc[index, "Retrieved Article"] = rag["article"]

            df.loc[index, "Response Time (ms)"] = rag["response_time"]

            evaluator.success += 1

            print(

                f"   Confidence : {scores['confidence']}"

            )

        except Exception as e:

            evaluator.failure += 1

            print(e)

            df.loc[index, "Model Answer"] = str(e)

            df.loc[index, "Confidence Score"] = 0

            df.loc[index, "Manual Testing Score"] = 1

            df.loc[index, "Comments"] = str(e)

        # --------------------------
        # Checkpoint
        # --------------------------

        if (index + 1) % CHECKPOINT_INTERVAL == 0:

            checkpoint = output_file.replace(

                ".xlsx",

                f"_ckpt{index+1}.xlsx"

            )

            df.to_excel(

                checkpoint,

                index=False,

            )

            print(

                f"Checkpoint saved -> {checkpoint}"

            )

        time.sleep(delay)

    # --------------------------------------------------

    df.to_excel(

        output_file,

        index=False,

    )

    print("\nEvaluation Complete\n")

    print(

        f"Success : {evaluator.success}"

    )

    print(

        f"Failures : {evaluator.failure}"

    )

    print(

        f"Output : {output_file}"

    )
    print("----------------------------")
# ----------------------------------------------------------
# CLI
# ----------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Professional Wikipedia RAG Evaluator"
    )

    parser.add_argument(
        "--input",
        default="Mount_Everest_RAG_Evaluation_400Q.xlsx",
        help="Input Excel file",
    )

    parser.add_argument(
        "--col",
        default="Question",
        help="Question column name",
    )

    parser.add_argument(
        "--api",
        default="https://vinamra26-wikipedia-rag-chatbot.hf.space",
        help="HF Space URL",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API requests (seconds)",
    )

    parser.add_argument(
        "--output",
        default="evaluated_results.xlsx",
        help="Output Excel file",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Professional Wikipedia RAG Evaluator")
    print("=" * 70)
    print(f"Input File : {args.input}")
    print(f"API        : {args.api}")
    print("=" * 70)

    run_evaluation(
        input_file=args.input,
        question_col=args.col,
        api_base=args.api,
        delay=args.delay,
        output_file=args.output,
    )

    print("\nEvaluation Finished Successfully!")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()