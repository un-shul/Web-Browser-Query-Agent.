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

def aggressive_text_cleaning(text):
    """
    Aggressively clean text to remove promotional and irrelevant content
    """
    # Remove package pricing and booking content
    text = re.sub(r'\b\d+[,.]?\d*\s*(Rs|INR|₹|onwards|person|off|discount)\b.*?(?=\.|$)', '', text, flags=re.I)
    text = re.sub(r'\b(Get Offers|Book Now|View Packages|Compare quotes|Customized|Package|Tour|Days|Nights)\b.*?(?=\.|$)', '', text, flags=re.I)
    
    # Remove navigation and website elements
    text = re.sub(r'\b(Skip to|Main Content|Screen Reader|Welcome to|Discover|Destinations)\b.*?(?=\.|$)', '', text, flags=re.I)
    
    # Remove lists of places without context
    text = re.sub(r'\b(Ajmer|Alwar|Banswara|Baran|Barmer|Bharatpur|Bhilwara|Bikaner|Bundi|Chittorgarh|Dausa|Dholpur|Dungarpur|Hanumangarh|Jalore|Jhalawar|Karauli|Kota|Nagaur|Pali|Pratapgarh|Sawaimadhopur|Shekhawati|Sriganganagar|Tonk|Rajsamand)\b(?:\s+\b(?:Ajmer|Alwar|Banswara|Baran|Barmer|Bharatpur|Bhilwara|Bikaner|Bundi|Chittorgarh|Dausa|Dholpur|Dungarpur|Hanumangarh|Jalore|Jhalawar|Karauli|Kota|Nagaur|Pali|Pratapgarh|Sawaimadhopur|Shekhawati|Sriganganagar|Tonk|Rajsamand)\b){3,}', '', text, flags=re.I)
    
    # Remove promotional phrases
    text = re.sub(r'\b(Call now|WhatsApp|Subscribe|Follow us|Book early|Perfect for|Highlights|Tips)\b.*?(?=\.|$)', '', text, flags=re.I)
    
    # Remove contact info and social media
    text = re.sub(r'\b\d{10,}\b', '', text)  # Phone numbers
    text = re.sub(r'\S+@\S+\.\S+', '', text)  # Emails
    
    # Clean up extra spaces and punctuation
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.!?,-]', '', text)
    
    return text.strip()

def extract_meaningful_sentences(text, query_words=None):
    """
    Extract only meaningful, complete sentences related to the query
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    good_sentences = []
    query_terms = set(query_words.lower().split()) if query_words else set()
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Skip short sentences
        if len(sentence) < 30 or len(sentence.split()) < 5:
            continue
            
        # Skip sentences with too many numbers (likely pricing/data)
        numbers = len(re.findall(r'\b\d+\b', sentence))
        if numbers > 3:
            continue
            
        # Skip sentences that are mostly promotional
        promo_words = ['book', 'package', 'offer', 'discount', 'call', 'contact', 'get']
        promo_count = sum(1 for word in promo_words if word in sentence.lower())
        if promo_count > 2:
            continue
            
        # Prefer sentences that contain query terms
        sentence_words = set(sentence.lower().split())
        relevance_score = len(query_terms.intersection(sentence_words))
        
        # Keep sentences with good relevance or general travel info
        if relevance_score > 0 or any(word in sentence.lower() for word in ['weather', 'temperature', 'season', 'month', 'time', 'best']):
            good_sentences.append((sentence, relevance_score))
    
    # Sort by relevance and return top sentences
    good_sentences.sort(key=lambda x: x[1], reverse=True)
    return [sentence for sentence, score in good_sentences[:8]]

def create_readable_summary(sentences):
    """
    Create a well-formatted summary with proper paragraphs
    """
    if not sentences:
        return "No relevant information found."
    
    # Group sentences by topic
    weather_sentences = []
    time_sentences = []
    general_sentences = []
    
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ['weather', 'temperature', 'climate', 'hot', 'cold', 'rain']):
            weather_sentences.append(sentence)
        elif any(word in lower for word in ['best time', 'ideal', 'perfect', 'recommended', 'visit']):
            time_sentences.append(sentence)
        else:
            general_sentences.append(sentence)
    
    # Build summary with paragraphs
    summary_parts = []
    
    # Best time paragraph
    if time_sentences:
        summary_parts.append(' '.join(time_sentences[:2]))
    
    # Weather paragraph  
    if weather_sentences:
        summary_parts.append(' '.join(weather_sentences[:2]))
    
    # Additional info paragraph
    if general_sentences:
        summary_parts.append(' '.join(general_sentences[:2]))
    
    # Join with double newlines for paragraphs
    final_summary = '\n\n'.join(summary_parts)
    
    # Clean up any remaining issues
    final_summary = re.sub(r'\s+', ' ', final_summary)
    final_summary = re.sub(r'\n\n+', '\n\n', final_summary)
    
    return final_summary.strip()

def fallback_ai_summary(text, query=None):
    """
    Simple AI summarization fallback
    """
    try:
        # Clean text first
        cleaned = aggressive_text_cleaning(text)
        
        # Limit text size
        words = cleaned.split()
        if len(words) > 400:
            cleaned = ' '.join(words[:400])
        
        with suppress_warnings():
            result = summarizer(cleaned, max_length=100, min_length=30, do_sample=False)
            return result[0]['summary_text']
    except Exception as e:
        print(f"⚠️ AI summarization failed: {e}")
        return "Unable to generate summary."

def summarize_text(text, query=None):
    """
    Main summarization function - simple and effective
    """
    if not text or len(text.strip()) < 100:
        return "Insufficient content to summarize."
    
    # Step 1: Aggressive cleaning
    cleaned_text = aggressive_text_cleaning(text)
    
    if len(cleaned_text) < 200:
        return fallback_ai_summary(text, query)
    
    # Step 2: Extract meaningful sentences
    sentences = extract_meaningful_sentences(cleaned_text, query)
    
    if len(sentences) < 2:
        return fallback_ai_summary(cleaned_text, query)
    
    # Step 3: Create readable summary
    summary = create_readable_summary(sentences)
    
    # Step 4: Final validation
    if len(summary.split()) < 20:
        return fallback_ai_summary(cleaned_text, query)
    
    # Ensure summary isn't too long
    if len(summary) > 1000:
        paragraphs = summary.split('\n\n')
        summary = '\n\n'.join(paragraphs[:2])
    
    return summary if summary else "Unable to generate a meaningful summary."
