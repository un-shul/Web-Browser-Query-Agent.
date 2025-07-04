import contextlib
import os
import sys
import re
import warnings
import logging
from transformers import pipeline

# Suppress transformers warnings and logging
logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Silence ALL output (both stdout and stderr) including Hugging Face warnings
@contextlib.contextmanager
def suppress_warnings():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def clean_text(text):
    # Remove login/registration prompts and website clutter
    text = re.sub(r"\b(You are already registered|Please login|Dont have an account|Sign up|Facebook user|Facebook account)\b.*?(?=\.|$)", "", text, flags=re.I)
    text = re.sub(r"\b(Mr Mrs Ms Dr Master Miss|Contains between|alphanumeric characters|special character|not mandatory)\b.*?(?=\.|$)", "", text, flags=re.I)
    
    # Remove social media and promotional content
    text = re.sub(r"\b(Follow us|Like us|Subscribe|Share|Tweet|Facebook|Instagram|Twitter)\b.*?(?=\.|$)", "", text, flags=re.I)
    
    # Remove booking and commercial content
    text = re.sub(r"\b(Book now|Call now|Contact us|Get quotes|Price|Package|Offer|Discount)\b.*?(?=\.|$)", "", text, flags=re.I)
    
    # Remove navigation and website elements
    text = re.sub(r"\b(Menu|Navigation|Home|About|Contact|Privacy Policy|Terms|Cookies)\b.*?(?=\.|$)", "", text, flags=re.I)
    
    # Original cleaning
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[^\w\s,.!?]", "", text)
    text = re.sub(r"\b(where is|list of|all [a-z]+ countries|city of [a-z]+)\b.*", "", text, flags=re.I)
    
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()

def fix_punctuation(text):
    """
    Fix punctuation issues like extra spaces before periods, commas, etc.
    """
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.!?,:;])', r'\1', text)
    
    # Ensure single space after punctuation
    text = re.sub(r'([.!?])\s*', r'\1 ', text)
    text = re.sub(r'([,:;])\s*', r'\1 ', text)
    
    # Fix multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove trailing spaces and fix paragraph spacing
    text = text.strip()
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text

def split_text(text, max_words=400):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

def trim_to_sentence_boundary(text, max_chars=4500):
    """
    Increased max_chars from 3000 to 4500 for longer summaries
    """
    # First fix punctuation
    text = fix_punctuation(text)
    
    if len(text) <= max_chars:
        return text

    sentences = re.split(r'(?<=[.!?]) +', text)
    trimmed = ''
    for sentence in sentences:
        if len(trimmed) + len(sentence) <= max_chars:
            trimmed += sentence + ' '
        else:
            break
    
    # Final punctuation fix
    return fix_punctuation(trimmed.strip())

def summarize_text(text, query=None, max_chunk_words=380):
    """
    Main summarization function - your original approach with improvements
    """
    text = clean_text(text)
    chunks = list(split_text(text, max_chunk_words))

    summaries = []
    for chunk in chunks:
        try:
            # Use the context manager to suppress warnings
            with suppress_warnings():
                # Increased max_length from 120 to 160 for longer summaries (3-4 more lines)
                summary = summarizer(chunk, max_length=160, min_length=50, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        except Exception as e:
            print(f"⚠️ Skipping chunk due to error: {e}")
            continue

    if not summaries:
        return "Unable to generate summary."
    
    # Join summaries with proper spacing
    final_summary = "\n\n".join(summaries)
    
    # Apply punctuation fixes to the final result
    final_summary = fix_punctuation(final_summary)
    
    return trim_to_sentence_boundary(final_summary)
