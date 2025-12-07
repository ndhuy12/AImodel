import google.generativeai as genai
import time
import json
from PIL import Image

def get_ai_recommendations(age, interests, mood, style, content_type):
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Act as an expert OTAKU. Recommend 5 {content_type} series.
    User Info: {age} years old.
    Interests: {interests}
    Current Mood: {mood}
    Preferred Style: {style}
    
    Requirement: Return ONLY a valid JSON list (no markdown, no extra text) with this format:
    [
        {{"title": "Name", "genre": "Genre1, Genre2", "reason": "Short explanation why it fits"}}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        
        return json.loads(text)
    except Exception as e:
        return []

def ai_vision_detect(image_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    try:
        img = Image.open(image_file)
        prompt = "Look at this anime character. Return ONLY the full name of the character. If not sure, return 'Unknown'."
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        return "Unknown"

def generate_ai_stream(info):
    model = genai.GenerativeModel('gemini-1.5-flash-8b')
    
    name = info.get('name', 'N/A')
    about = info.get('about', 'N/A')
    
    if about and len(about) > 2000: about = about[:2000] + "..."

    prompt = f"""
    You are an expert Anime Otaku. Write an engaging profile for this character in ENGLISH.
    Character Name: {name}
    Bio Data: {about}

    Requirements:
    1. Catchy Title.
    2. Fun and enthusiastic tone (use emojis 🌟🔥).
    3. Analyze personality & powers.
    4. Keep it under 200 words.
    """
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, stream=True)
            return response
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    class ErrorChunk:
                        def __init__(self, text): self.text = text
                    return [ErrorChunk(f"Server Busy (429). Please try again later.")]
            else:
                class ErrorChunk:
                    def __init__(self, text): self.text = text
                return [ErrorChunk(f"Error: {error_msg}")]

    return []
