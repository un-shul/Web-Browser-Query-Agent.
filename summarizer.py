import contextlib
import os
import sys
import re
import warnings
import logging
from collections import Counter
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

def clean_and_preprocess_text(text):
    """
    Advanced text cleaning and preprocessing
    """
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    
    # Remove navigation and menu items
    text = re.sub(r'\b(Home|About|Contact|Menu|Navigation|Login|Register|Subscribe|Follow|Share)\b', '', text, flags=re.I)
    
    # Remove repetitive website elements
    text = re.sub(r'\b(Copyright|All rights reserved|Privacy Policy|Terms of Service)\b.*', '', text, flags=re.I)
    
    # Remove social media and promotional text
    text = re.sub(r'\b(Follow us|Like us|Subscribe|Book now|Call now|WhatsApp)\b.*', '', text, flags=re.I)
    
    # Remove phone numbers and emails
    text = re.sub(r'\b\d{10,}\b', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    
    # Clean up punctuation
    text = re.sub(r'[^\w\s,.!?()-]', '', text)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\,{2,}', ',', text)
    
    return text.strip()

def extract_sentences(text):
    """
    Extract meaningful sentences from text
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    valid_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Filter out short or meaningless sentences
        if len(sentence) < 20 or len(sentence.split()) < 4:
            continue
            
        # Filter out repetitive or promotional sentences
        if any(pattern in sentence.lower() for pattern in [
            'best time to visit', 'click here', 'read more', 'book now',
            'call us', 'contact us', 'follow us', 'subscribe'
        ]) and sentence.count('.') > 3:
            continue
            
        # Keep sentences with useful information
        valid_sentences.append(sentence)
    
    return valid_sentences

def remove_duplicate_sentences(sentences):
    """
    Remove duplicate and very similar sentences
    """
    unique_sentences = []
    seen_content = []
    
    for sentence in sentences:
        # Create a normalized version for comparison
        normalized = re.sub(r'\W+', ' ', sentence.lower()).strip()
        words = set(normalized.split())
        
        # Skip if we've seen very similar content
        is_duplicate = False
        for seen_words in seen_content:
            overlap = len(words.intersection(seen_words)) / max(len(words), len(seen_words))
            if overlap > 0.7:  # 70% similarity threshold
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_sentences.append(sentence)
            seen_content.append(words)
            
        # Limit to prevent overly long summaries
        if len(unique_sentences) >= 15:
            break
    
    return unique_sentences

def extract_key_information(sentences, query_words=None):
    """
    Extract the most relevant sentences based on key information
    """
    if query_words is None:
        query_words = set()
    else:
        query_words = set(word.lower() for word in query_words)
    
    scored_sentences = []
    
    for sentence in sentences:
        score = 0
        words = sentence.lower().split()
        
        # Score based on query relevance
        if query_words:
            query_matches = sum(1 for word in words if word in query_words)
            score += query_matches * 3
        
        # Score based on information density
        info_words = ['best', 'time', 'visit', 'month', 'season', 'weather', 'temperature', 
                     'cost', 'price', 'tips', 'guide', 'how', 'when', 'where', 'what']
        info_matches = sum(1 for word in words if word in info_words)
        score += info_matches
        
        # Score based on numbers (dates, temperatures, etc.)
        numbers = len(re.findall(r'\b\d+\b', sentence))
        score += numbers * 2
        
        # Penalize very long sentences
        if len(words) > 30:
            score -= 2
            
        # Penalize sentences with too many repeated words
        word_freq = Counter(words)
        repeated_words = sum(1 for count in word_freq.values() if count > 2)
        score -= repeated_words
        
        scored_sentences.append((sentence, score))
    
    # Sort by score and return top sentences
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    return [sentence for sentence, score in scored_sentences[:10]]

def create_coherent_summary(sentences):
    """
    Organize sentences into a coherent summary
    """
    if not sentences:
        return ""
    
    # Group sentences by topic/theme
    intro_sentences = []
    detail_sentences = []
    
    for sentence in sentences:
        words = sentence.lower()
        if any(word in words for word in ['best time', 'ideal time', 'perfect time', 'recommended']):
            intro_sentences.append(sentence)
        else:
            detail_sentences.append(sentence)
    
    # Combine in logical order
    final_sentences = intro_sentences[:3] + detail_sentences[:7]
    
    # Join with proper spacing
    summary = ' '.join(final_sentences)
    
    # Final cleanup
    summary = re.sub(r'\s+', ' ', summary)
    summary = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', summary)
    
    return summary.strip()

def summarize_with_ai(text, max_length=150):
    """
    Use AI summarization as a fallback or enhancement
    """
    try:
        with suppress_warnings():
            # Split into smaller chunks if too long
            if len(text.split()) > 500:
                words = text.split()
                text = ' '.join(words[:500])
            
            result = summarizer(text, max_length=max_length, min_length=50, do_sample=False)
            return result[0]['summary_text']
    except Exception as e:
        print(f"⚠️ AI summarization failed: {e}")
        return text[:500] + "..." if len(text) > 500 else text

def summarize_text(text, query=None):
    """
    Main summarization function with improved quality
    """
    if not text or len(text.strip()) < 100:
        return "Insufficient content to summarize."
    
    # Extract query words for relevance scoring
    query_words = query.split() if query else []
    
    # Step 1: Clean and preprocess text
    cleaned_text = clean_and_preprocess_text(text)
    
    # Step 2: Extract meaningful sentences
    sentences = extract_sentences(cleaned_text)
    
    if len(sentences) < 3:
        # If we have very few sentences, use AI summarization
        return summarize_with_ai(cleaned_text)
    
    # Step 3: Remove duplicates
    unique_sentences = remove_duplicate_sentences(sentences)
    
    # Step 4: Extract key information
    key_sentences = extract_key_information(unique_sentences, query_words)
    
    # Step 5: Create coherent summary
    summary = create_coherent_summary(key_sentences)
    
    # Step 6: Final validation and enhancement
    if len(summary.split()) < 30:
        # If summary is too short, enhance with AI
        enhanced = summarize_with_ai(cleaned_text, max_length=200)
        if len(enhanced) > len(summary):
            summary = enhanced
    
    # Ensure summary isn't too long
    if len(summary) > 2000:
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        summary = ' '.join(sentences[:8])
    
    return summary if summary else "Unable to generate summary from the provided content."
