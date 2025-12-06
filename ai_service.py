import google.generativeai as genai
from PIL import Image

# # AI Services & Prompts

def ai_vision_detect(image_data):
    image = Image.open(image_data)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Vision Prompt
    prompt = "Look at this anime character. Return ONLY the full name. If unsure, return 'Unknown'."
    
    try:
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e: 
        print(f"Vision Error: {e}")
        return "Unknown"

def generate_ai_stream(info):
    model = genai.GenerativeModel('gemini-2.0-flash')
    name = info.get('name', 'N/A')
    about = info.get('about', 'N/A')
    if about and len(about) > 2000: about = about[:2000] + "..."

    # Character Analysis Prompt
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
    return model.generate_content(prompt, stream=True)