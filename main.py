import streamlit as st
from PIL import Image
import requests
import os
import time
import json
from datetime import datetime
import google.generativeai as genai

try:
    from style_css import set_background_image, add_corner_gif, set_global_style
except ImportError:
    def set_background_image(x): pass
    def add_corner_gif(): pass
    def set_global_style(x): pass

try:
    from genre_service import get_genre_map
except ImportError:
    try:
        from services.genre_service import get_genre_map
    except ImportError:
        def get_genre_map(type): return {}

try:
    from jikan_service import get_character_data, get_one_character_data, get_random_manga_data
except ImportError:
    try:
        from jikan_services import get_character_data, get_one_character_data, get_random_manga_data
    except ImportError:
        try:
            from services.jikan_service import get_character_data, get_one_character_data, get_random_manga_data
        except ImportError:
            def get_character_data(q): return []
            def get_one_character_data(q): return None
            def get_random_manga_data(): return None

try:
    from ai_service import ai_vision_detect, generate_ai_stream
except ImportError:
    def ai_vision_detect(img): return "Unknown"
    def generate_ai_stream(info): return []

def get_ai_recommendations(age, interests, mood, style, content_type):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Act as an Anime/Manga expert. Recommend 3 {content_type} titles.
        User Info: {age} years old.
        Mood: {mood}.
        Preferred Style: {style}.
        Interests: {interests}.
        
        Format JSON list strictly:
        [
            {{"title": "Name", "genre": "Genre", "reason": "Why it fits"}}
        ]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        return json.loads(text)
    except Exception:
        return []

st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

st.markdown("""
<style>
    .loading-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.9);
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        z-index: 99999;
        animation: fadeOutOverlay 0.5s ease-out 1.5s forwards;
        pointer-events: none;
    }
    .loading-content { text-align: center; }
    .loading-title { font-size: 2rem; font-weight: bold; color: #ff7f50; margin-bottom: 20px; }
    .progress-bar {
        width: 300px; height: 6px; background: linear-gradient(90deg, #ff7f50 0%, #ff6b6b 100%);
        border-radius: 10px; animation: loadProgress 1.5s ease-out forwards;
    }
    @keyframes loadProgress { 0% { width: 0%; } 100% { width: 100%; } }
    @keyframes fadeOutOverlay { to { opacity: 0; visibility: hidden; } }
</style>
<div class="loading-overlay">
    <div class="loading-content">
        <div class="loading-title">ITOOK LIBRARY</div>
        <div class="progress-bar"></div>
        <div style="color:white; margin-top:10px">Loading Resources...</div>
    </div>
</div>
""", unsafe_allow_html=True)

if 'current_page' not in st.session_state: st.session_state.current_page = 'home'
if 'show_upgrade_modal' not in st.session_state: st.session_state.show_upgrade_modal = False
if 'favorites' not in st.session_state: st.session_state.favorites = {'media': [], 'characters': []}
if 'search_history' not in st.session_state: st.session_state.search_history = []
if 'random_manga_item' not in st.session_state: st.session_state.random_manga_item = None
if 'recommendations' not in st.session_state: st.session_state.recommendations = None

def navigate_to(page):
    st.session_state.show_upgrade_modal = False
    if page == 'wiki':
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
    st.session_state.current_page = page
    st.rerun()

def add_to_history(action_type, query, details=None):
    entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': action_type, 'query': query, 'details': details
    }
    st.session_state.search_history.insert(0, entry)
    if len(st.session_state.search_history) > 50: st.session_state.search_history = st.session_state.search_history[:50]

def is_favorited(item_id, category):
    for item in st.session_state.favorites[category]:
        current_id = item.get('mal_id') or item.get('id')
        if str(current_id) == str(item_id): return True
    return False

def toggle_favorite(data, category='media'):
    item_id = data.get('mal_id') or data.get('id')
    title = data.get('title') or data.get('name')
    
    if is_favorited(item_id, category):
        st.session_state.favorites[category] = [i for i in st.session_state.favorites[category] if str(i.get('mal_id') or i.get('id')) != str(item_id)]
        st.toast(f"💔 Removed '{title}'")
    else:
        fav_item = {
            'mal_id': item_id, 'title': title,
            'image_url': data.get('images', {}).get('jpg', {}).get('image_url'),
            'score': data.get('score'), 'url': data.get('url'),
            'type': category
        }
        st.session_state.favorites[category].append(fav_item)
        st.toast(f"❤️ Added '{title}'")

def show_navbar():
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 0.8], vertical_alignment="center")
        with c1: st.markdown('<p class="logo-text">ITOOK Library</p>', unsafe_allow_html=True)
        with c2: 
            if st.button("HOME", use_container_width=True): navigate_to('home')
        with c3:
            with st.popover("SERVICES", use_container_width=True):
                if st.button("🕵️ Wiki Search", use_container_width=True): navigate_to('wiki')
                if st.button("📂 Genre Explorer", use_container_width=True): navigate_to('genre')
                if st.button("🤖 AI Recommend", use_container_width=True): navigate_to('recommend')
        with c4: 
            if st.button("FAVORITES", use_container_width=True): navigate_to('favorites')
        with c5: 
            if st.button("ADVANCES", use_container_width=True): 
                st.session_state.show_upgrade_modal = True
                st.rerun()
        with c6: 
            if st.button("CONTACT", use_container_width=True): navigate_to('contact')

@st.dialog("🚀 Upgrade")
def show_upgrade_dialog():
    st.write("Trải nghiệm phiên bản nâng cao ngay!")
    st.link_button("GO TO ADVANCED", "https://itookwusadvances.streamlit.app/", type="primary", use_container_width=True)
    st.session_state.show_upgrade_modal = False

def show_homepage():
    set_global_style("test.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.markdown("<h1 style='text-align: center; color: #ff7f50; font-family: Pacifico;'>Welcome to ITOOK Library</h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2: 
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3: 
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')
    
    if not st.session_state.random_manga_item:
        st.session_state.random_manga_item = get_random_manga_data()
    
    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("---")
        st.subheader("✨ Manga of the Day")
        c_img, c_info = st.columns([1, 3])
        with c_img:
            st.image(manga['images']['jpg']['large_image_url'], use_container_width=True)
            if st.button("🔄 Shuffle"): 
                st.session_state.random_manga_item = get_random_manga_data()
                st.rerun()
        with c_info:
            st.header(manga.get('title'))
            st.write(manga.get('synopsis', 'No summary')[:500] + "...")
            if st.button("❤️ Favorite" if not is_favorited(manga.get('mal_id'), 'media') else "💔 Unfavorite"):
                toggle_favorite(manga, 'media')
                st.rerun()

def show_recommend_page():
    set_global_style("test1.jpg")
    show_navbar()
    st.title("🤖 AI Recommendation")
    
    with st.form("rec_form"):
        c1, c2 = st.columns(2)
        with c1:
            age = st.slider("Age", 10, 80, 20)
            mood = st.selectbox("Mood", ["Happy", "Sad", "Chill", "Dark"])
        with c2:
            ctype = st.selectbox("Type", ["Anime", "Manga"])
            style = st.selectbox("Style", ["Action", "Romance", "Horror"])
        interests = st.text_area("Interests")
        submitted = st.form_submit_button("Generate", type="primary")
    
    if submitted:
        with st.spinner("AI is thinking..."):
            recs = get_ai_recommendations(age, interests, mood, style, ctype)
            st.session_state.recommendations = recs
            
    if st.session_state.recommendations:
        for item in st.session_state.recommendations:
            with st.container(border=True):
                st.subheader(item['title'])
                st.write(f"**Genre:** {item.get('genre')}")
                st.info(item['reason'])

def show_genre_page():
    set_global_style("test4.jpg")
    show_navbar()
    st.title("📂 Genre Explorer")
    
    ctype = st.selectbox("Type", ["anime", "manga"])
    genre_map = get_genre_map(ctype)
    
    if genre_map:
        genres = sorted(genre_map.keys())
        selected = st.multiselect("Select Genres", genres)
        if st.button("Search"):
            st.success(f"Searching for {selected}")
            add_to_history("Genre", str(selected))

def show_favorites_page():
    set_global_style("#0e1117")
    show_navbar()
    st.title("❤️ Favorites")
    
    tabs = st.tabs(["Media", "Characters"])
    with tabs[0]:
        for item in st.session_state.favorites['media']:
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1: st.image(item['image_url'], width=100)
                with c2: 
                    st.subheader(item['title'])
                    if st.button("Remove", key=f"rm_{item['mal_id']}"):
                        toggle_favorite(item, 'media')
                        st.rerun()
    with tabs[1]:
        for item in st.session_state.favorites['characters']:
            with st.container(border=True):
                st.image(item['image_url'], width=100)
                st.write(item['title'])

def show_wiki_page():
    set_global_style("test3.jpg")
    show_navbar()
    st.title("🕵️ Character Wiki")
    
    tab1, tab2 = st.tabs(["Search Name", "Vision Scan"])
    
    with tab1:
        query = st.text_input("Name:")
        if query and st.button("Search"):
            results = get_character_data(query)
            if results:
                st.session_state.wiki_search_results = results
                
        if st.session_state.get('wiki_search_results'):
            results = st.session_state.wiki_search_results
            opts = {f"{c['name']}": c for c in results}
            choice = st.selectbox("Select:", list(opts.keys()))
            if st.button("Analyze"):
                char = opts[choice]
                st.session_state.wiki_selected_char = char
                st.rerun()
    
    with tab2:
        up = st.file_uploader("Image")
        if up and st.button("Scan"):
            with st.spinner("Scanning..."):
                name = ai_vision_detect(up)
                if name != "Unknown":
                    st.success(f"Detected: {name}")
                    info = get_one_character_data(name)
                    st.session_state.wiki_selected_char = info
                    st.rerun()
                else:
                    st.error("Unknown character")

    if st.session_state.get('wiki_selected_char'):
        char = st.session_state.wiki_selected_char
        st.markdown("---")
        c1, c2 = st.columns([1, 2])
        with c1: st.image(char['images']['jpg']['image_url'])
        with c2:
            st.header(char['name'])
            if st.button("Gen AI Profile"):
                with st.spinner("Generating..."):
                    stream = generate_ai_stream(char)
                    text = ""
                    box = st.empty()
                    for chunk in stream:
                        if hasattr(chunk, 'text'):
                            text += chunk.text
                            box.info(text)

def show_contact_page():
    show_navbar()
    st.title("📞 Contact")
    st.write("Email: admin@itooklibrary.com")

pages = {
    'home': show_homepage,
    'wiki': show_wiki_page,
    'genre': show_genre_page,
    'recommend': show_recommend_page,
    'favorites': show_favorites_page,
    'contact': show_contact_page
}

if st.session_state.current_page in pages:
    pages[st.session_state.current_page]()
