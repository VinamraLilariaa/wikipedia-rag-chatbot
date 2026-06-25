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

        # Collapse 3+ newlines down to a single blank line, but keep
        # paragraph/section breaks (double newlines) intact so chunking
        # still respects the article's structure (headings, tables, etc).
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Replace multiple spaces/tabs with a single space
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()