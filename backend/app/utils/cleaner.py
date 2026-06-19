import re


class TextCleaner:
    """
    Cleans raw Wikipedia text before chunking.
    """

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Remove citation numbers like [1], [23]
        text = re.sub(r"\[\d+\]", "", text)

        # Replace multiple newlines with a single newline
        text = re.sub(r"\n+", "\n", text)

        # Replace multiple spaces with a single space
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()