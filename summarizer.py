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

# Comprehensive patterns for filtering unwanted content
UNWANTED_PATTERNS = [
    # Ads and promotional content
    r'(?i)\b(advertisement|sponsored|promo|click here|buy now|shop now|order now|get yours|limited time|special offer|discount|save \d+%)\b',
    
    # Subscription and newsletter prompts
    r'(?i)\b(subscribe|newsletter|follow us|join us|sign up for|get updates|email updates|notifications)\b',
    
    # Social media and sharing
    r'(?i)\b(share this|like us on|follow us on|tweet this|facebook|twitter|instagram|linkedin|social media)\b',
    
    # Login and account related
    r'(?i)\b(log in|sign in|sign up|register|create account|login|signin|account|password|username|email address)\b',
    
    # Cookie and privacy notices
    r'(?i)\b(cookie policy|privacy policy|terms of service|accept cookies|gdpr|consent|data protection|we use cookies)\b',
    
    # Navigation and UI elements
    r'(?i)\b(home|about|contact|menu|search|previous|next|page \d+|go to|back to|return to)\b',
    
    # App download prompts
    r'(?i)\b(download app|get the app|install|app store|google play|mobile app|download now)\b',
    
    # Comments and user interaction
    r'(?i)\b(comments|leave a comment|post a comment|reply|reviews|rate this|rating|stars|thumbs up)\b',
    
    # Generic website elements
    r'(?i)\b(loading|please wait|error|404|page not found|access denied|javascript|enable javascript)\b',
    
    # Time stamps and metadata that don't add value
    r'\b\d{1,2}:\d{2}\s*(am|pm|AM|PM)\b',
    r'\b(updated|published|posted|created):\s*\d',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    
    # Empty or low-content phrases
    r'(?i)\b(read more|see more|view all|show all|load more|continue reading|full article)\b',
    
    # Legal and compliance text
    r'(?i)\b(copyright|all rights reserved|trademark|terms and conditions|disclaimer|legal notice)\b'
]

def clean_text(text):
    """Enhanced text cleaning to remove unwanted content patterns"""
    if not text:
        return ""
    
    # First, normalize whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove unwanted patterns
    for pattern in UNWANTED_PATTERNS:
        text = re.sub(pattern, '', text)
    
    # Remove sentences that are likely navigation or ads
    sentences = re.split(r'(?<=[.!?])\s+', text)
    filtered_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Skip very short sentences (likely navigation)
        if len(sentence) < 15:
            continue
            
        # Skip sentences with too many capital letters (likely headings/ads)
        if len(sentence) > 10:
            caps_ratio = sum(1 for c in sentence if c.isupper()) / len(sentence)
            if caps_ratio > 0.3:
                continue
        
        # Skip sentences with suspicious patterns
        suspicious_patterns = [
            r'\b(click|tap|download|subscribe|buy|shop|order)\b.*\b(here|now|today)\b',
            r'\b\d+%\s*(off|discount|save)',
            r'\$\d+',  # Price mentions
            r'\b(free|deal|offer|sale)\b.*\b(limited|today|now)\b'
        ]
        
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in suspicious_patterns):
            continue
            
        # Skip sentences that are mostly punctuation or special characters
        if len(re.sub(r'[a-zA-Z\s]', '', sentence)) / len(sentence) > 0.2:
            continue
            
        filtered_sentences.append(sentence)
    
    # Rejoin sentences
    text = ' '.join(filtered_sentences)
    
    # Final cleanup - remove excessive punctuation and normalize
    text = re.sub(r'[^\w\s,.!?;:-]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common website boilerplate
    boilerplate_patterns = [
        r'(?i)this website uses cookies.*?(?=\.|$)',
        r'(?i)by continuing to use.*?(?=\.|$)',
        r'(?i)for the best experience.*?(?=\.|$)',
        r'(?i)javascript must be enabled.*?(?=\.|$)'
    ]
    
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text)
    
    return text.strip()

def filter_content_relevance(text: str, min_sentence_length: int = 20) -> str:
    """Filter content to keep only relevant, substantial sentences"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    relevant_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Must be substantial length
        if len(sentence) < min_sentence_length:
            continue
            
        # Must contain primarily alphabetic content
        alpha_ratio = sum(1 for c in sentence if c.isalpha()) / len(sentence) if sentence else 0
        if alpha_ratio < 0.6:
            continue
            
        # Should not be a question about user action
        action_questions = [
            r'(?i)what would you like to',
            r'(?i)where would you like to',
            r'(?i)would you like to',
            r'(?i)do you want to'
        ]
        
        if any(re.search(pattern, sentence) for pattern in action_questions):
            continue
            
        relevant_sentences.append(sentence)
    
    return ' '.join(relevant_sentences)

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
    """Enhanced summarization with better content filtering"""
    # Clean the text thoroughly
    text = clean_text(text)
    
    # Filter for content relevance
    text = filter_content_relevance(text)
    
    # If text is too short after filtering, return it as-is
    if len(text.split()) < 50:
        return text
    
    chunks = list(split_text(text, max_chunk_words))
    
    if not chunks:
        return "No substantial content found after filtering."

    summaries = []
    for chunk in chunks:
        # Skip chunks that are too short or low quality
        if len(chunk.split()) < 30:
            continue
            
        try:
            with suppress_stdout():
                summary = summarizer(chunk, max_length=120, min_length=40, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        except Exception as e:
            print(f"⚠️ Skipping chunk due to error: {e}")
            continue

    if not summaries:
        return "Unable to generate summary from available content."
    
    final_summary = "\n\n".join(summaries)
    return trim_to_sentence_boundary(final_summary)
