import contextlib
import os
import sys
import re
from transformers import pipeline

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Silence Hugging Face warnings like: "Your max_length is set to..."
@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def clean_text(text):
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[^\w\s,.!?]", "", text)
    text = re.sub(r"\b(where is|list of|all [a-z]+ countries|city of [a-z]+)\b.*", "", text, flags=re.I)
    return text.strip()

def split_text(text, max_words=400):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

def trim_to_sentence_boundary(text, max_chars=3000):
    if len(text) <= max_chars:
        return text

    sentences = re.split(r'(?<=[.!?]) +', text)
    trimmed = ''
    for sentence in sentences:
        if len(trimmed) + len(sentence) <= max_chars:
            trimmed += sentence + ' '
        else:
            break
    return trimmed.strip()

def summarize_text(text, max_chunk_words=380):
    text = clean_text(text)
    chunks = list(split_text(text, max_chunk_words))

    summaries = []
    for chunk in chunks:
        try:
            summary = summarizer(chunk, max_length=120, min_length=40, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        except Exception as e:
            print(f"⚠️ Skipping chunk due to error: {e}")
            continue

    final_summary = "\n\n".join(summaries)
    return trim_to_sentence_boundary(final_summary)
