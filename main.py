import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import os
import time
from datetime import datetime, date
from style_css import set_global_style

# ============================================
# IMPORT ĐÚNG CÁCH - Đặt ở đầu file
# ============================================
from jikan_services import (
    get_genre_map, 
    get_character_data, 
    get_one_character_data, 
    get_daily_manga,
    force_refresh_daily_manga,
    get_jikan_stats
)

from ai_service import (
    ai_vision_detect, 
    generate_ai_stream, 
    get_ai_recommendations,
    get_api_stats,
    clear_analysis_cache
)

st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

# --- CONFIGURATION ---
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_API_KEY"]
else:
    st.error("API Key is missing. Please check secrets.toml.")
    st.stop()

genai.configure(api_key=API_KEY)

# --- SESSION STATE INITIALIZATION ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'show_upgrade_modal' not in st.session_state:
    st.session_state.show_upgrade_modal = False

if 'favorites' not in st.session_state:
    st.session_state.favorites = {'media': [], 'characters': []}
elif isinstance(st.session_state.favorites, list):
    old_favs = st.session_state.favorites
    st.session_state.favorites = {'media': [], 'characters': []}
    for item in old_favs:
        if item.get('type') == 'Character':
            st.session_state.favorites['characters'].append(item)
        else:
            st.session_state.favorites['media'].append(item)

if 'search_history' not in st.session_state:
    st.session_state.search_history = []

if 'random_manga_item' not in st.session_state:
    st.session_state.random_manga_item = None

if 'manga_date' not in st.session_state:
    st.session_state.manga_date = None

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

if 'character_analysis_cache' not in st.session_state:
    st.session_state.character_analysis_cache = {}

# --- HELPER FUNCTIONS ---
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
        'type': action_type,
        'query': query,
        'details': details
    }
    st.session_state.search_history.insert(0, entry)
    if len(st.session_state.search_history) > 50:
        st.session_state.search_history = st.session_state.search_history[:50]

def is_favorited(item_id, category):
    for item in st.session_state.favorites[category]:
        current_id = item.get('mal_id') or item.get('id')
        if str(current_id) == str(item_id):
            return True
    return False

def toggle_favorite(data, category='media'):
    item_id = data.get('mal_id') or data.get('id')
    title_name = data.get('title') or data.get('name') or data.get('title_english')
    
    if is_favorited(item_id, category):
        st.session_state.favorites[category] = [
            i for i in st.session_state.favorites[category] 
            if str(i.get('mal_id') or i.get('id')) != str(item_id)
        ]
        st.toast(f"💔 Removed '{title_name}' from Favorites", icon="🗑️")
    else:
        fav_item = {
            'mal_id': item_id,
            'title': title_name,
            'image_url': data.get('images', {}).get('jpg', {}).get('image_url') or data.get('image_url'),
            'score': data.get('score'),
            'url': data.get('url'),
            'type': data.get('type', 'Unknown'),
            'added_at': datetime.now().strftime("%Y-%m-%d")
        }
        st.session_state.favorites[category].append(fav_item)
        st.toast(f"❤️ Added '{title_name}' to Favorites", icon="✅")

# --- UI COMPONENTS ---
def show_navbar():
    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 0.8], gap="small", vertical_alignment="center")
        
        with col1: 
            st.markdown('<p class="logo-text">ITOOK Library</p>', unsafe_allow_html=True)
        
        with col2: 
            if st.button("HOME", use_container_width=True): navigate_to('home')
        
        with col3:
            with st.popover("SERVICES", use_container_width=True):
                if st.button("🕵️ Wiki Search", use_container_width=True): navigate_to('wiki')
                if st.button("📂 Genre Explorer", use_container_width=True): navigate_to('genre')
                if st.button("🤖 AI Recommend", use_container_width=True): navigate_to('recommend')
        
        with col4:
            if st.button("FAVORITES", use_container_width=True): navigate_to('favorites')
        
        with col5:
            if st.button("ADVANCES", use_container_width=True, key="advances_btn"):
                st.session_state.show_upgrade_modal = True
                st.rerun()
        
        with col6:
            if st.button("CONTACT", use_container_width=True): navigate_to('contact')
    
    # API Stats Monitor
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        ai_stats = get_api_stats()
        color = "🔴" if ai_stats['calls_last_minute'] >= 10 else "🟡" if ai_stats['calls_last_minute'] >= 8 else "🟢"
        st.caption(f"{color} AI: {ai_stats['limit']}")
    
    with col_stats2:
        jikan_stats = get_jikan_stats()
        st.caption(f"📊 Jikan: {jikan_stats['total_calls']} calls")
    
    st.write("")

@st.dialog("🚀 Upgrade Your Experience", width="large")
def show_upgrade_dialog():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');
        
        .upgrade-content {
            font-family: 'Poppins', sans-serif;
            text-align: center;
            padding: 10px;
        }
        
        .upgrade-message {
            font-size: 16px;
            color: #4a5568;
            line-height: 2;
            margin: 20px 0 30px 0;
            padding: 30px;
            background: linear-gradient(135deg, #f0f4ff 0%, #fff0f7 100%);
            border-radius: 20px;
            border-left: 5px solid #667eea;
        }
        
        .upgrade-message p {
            margin: 8px 0;
        }
        
        .highlight-text {
            font-weight: 600;
            color: #667eea;
            font-size: 17px;
        }
        </style>
        
        <div class="upgrade-content">
            <div class="upgrade-message">
                <p>Bạn chưa hài lòng với trải nghiệm hiện tại?</p>
                <p>Bạn muốn sử dụng dịch vụ tốt hơn?</p>
                <p class="highlight-text">Đừng lo! Chúng tôi sẽ đưa bạn đến 1 công cụ mạnh mẽ hơn!</p>
                <p style="font-size: 18px; margin-top: 15px;"><strong>Follow us ✨</strong></p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button(
            "🚀 GO TO ADVANCED VERSION",
            "https://itookwusadvances.streamlit.app/",
            use_container_width=True,
            type="primary"
        )
    
    st.session_state.show_upgrade_modal = False

# --- PAGES ---
def show_homepage():
    set_global_style("test.jpg") 
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog() 
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');
        .hero-title {
            font-family: 'Pacifico', cursive !important;
            font-size: 80px !important;
            color: #ff7f50 !important; 
            text-align: center;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.8) !important; 
            margin-top: 20px;
        }
        .hero-subtitle {
            font-family: 'Montserrat', sans-serif; font-size: 24px !important; color: #e0e0e0 !important;
            text-align: center; margin-top: -20px; margin-bottom: 40px; font-style: italic;
            text-shadow: 2px 2px 4px #000000;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="hero-title">Welcome to ITOOK Library!</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Your gateway to infinite worlds.</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2:
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3:
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')

    # Daily Manga Section
    today = date.today().isoformat()
    
    if st.session_state.manga_date != today or st.session_state.random_manga_item is None:
        st.session_state.random_manga_item = get_daily_manga()
        st.session_state.manga_date = today

    def shuffle_manga():
        st.session_state.random_manga_item = force_refresh_daily_manga()
        st.session_state.manga_date = date.today().isoformat()

    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_title, col_date = st.columns([3, 1])
        with col_title:
            st.markdown('<h3 style="text-align:center; color: #ffd700;">✨ Manga of the Day</h3>', unsafe_allow_html=True)
        with col_date:
            today_display = date.today().strftime("%B %d, %Y")
            st.markdown(f'<p style="text-align:center; color: #aaa; font-size: 14px;">📅 {today_display}</p>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3], gap="large")
            with col_img:
                img_url = manga.get('images', {}).get('jpg', {}).get('large_image_url')
                if img_url: st.image(img_url, use_container_width=True)
                
                if st.button("🔄 Shuffle New", on_click=shuffle_manga, use_container_width=True):
                    pass
                
                manga_id = manga.get('mal_id')
                in_fav = is_favorited(manga_id, 'media')
                btn_label = "💔 Remove" if in_fav else "❤️ Add"
                if st.button(btn_label, key="daily_fav_btn", use_container_width=True):
                    toggle_favorite(manga, 'media')
                    st.rerun()

            with col_info:
                title = manga.get('title_english') or manga.get('title')
                st.markdown(f"## {title}")
                st.markdown(f"**⭐ Score:** {manga.get('score', 'N/A')} | **📌 Status:** {manga.get('status', 'Unknown')}")
                
                synopsis = manga.get('synopsis')
                if synopsis and len(synopsis) > 600: synopsis = synopsis[:600] + "..."
                st.write(synopsis)
                
                if manga.get('url'): st.markdown(f"[📖 Read more]({manga.get('url')})")
        
        st.info("💡 This manga will stay the same all day. Come back tomorrow!")

# Giữ nguyên các hàm khác: show_recommend_page, show_genre_page, show_favorites_page, show_history_page, show_contact_page

# --- MAIN ROUTER ---
if st.session_state.current_page == 'home': 
    show_homepage()
elif st.session_state.current_page == 'wiki': 
    show_wiki_page()
elif st.session_state.current_page == 'genre': 
    show_genre_page()
elif st.session_state.current_page == 'recommend': 
    show_recommend_page()
elif st.session_state.current_page == 'favorites': 
    show_favorites_page()
elif st.session_state.current_page == 'history':
    show_history_page()
elif st.session_state.current_page == 'contact': 
    show_contact_page()
