import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import os
import time
from datetime import datetime
# Giả định bạn đã có các file này trong thư mục dự án
from style_css import set_global_style
from jikan_services import get_genre_map, get_character_data, get_one_character_data, get_random_manga_data
from ai_service import ai_vision_detect, generate_ai_stream, get_ai_recommendations

# --- 1. PAGE CONFIG & LOADING SCREEN ---
st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

# Thêm hiệu ứng Loading Screen từ đoạn code cũ vào
st.markdown("""
<style>
    /* Overlay che phủ toàn màn hình */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 99999;
        animation: fadeOutOverlay 0.5s ease-out 2.5s forwards;
        pointer-events: none; /* Cho phép click xuyên qua sau khi ẩn */
    }
    
    .loading-content { text-align: center; }
    
    .loading-title {
        font-family: 'Pacifico', cursive;
        font-size: 2.5rem;
        color: #ff7f50;
        margin-bottom: 30px;
        text-shadow: 0 0 10px rgba(255, 127, 80, 0.5);
    }
    
    /* Progress bar container */
    .progress-container {
        width: 300px;
        height: 6px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    
    /* Progress bar fill */
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #ff7f50 0%, #ff6b6b 100%);
        border-radius: 10px;
        animation: loadProgress 2.2s ease-out forwards;
    }
    
    @keyframes loadProgress {
        0% { width: 0%; }
        100% { width: 100%; }
    }
    
    /* Animation ẩn overlay */
    @keyframes fadeOutOverlay {
        0% { opacity: 1; visibility: visible; }
        99% { opacity: 0; visibility: visible; }
        100% { opacity: 0; visibility: hidden; }
    }
    
    /* Hiệu ứng mờ nội dung chính khi mới vào */
    .main, .stApp > header {
        animation: clearContent 1s ease-in-out 2.2s forwards;
    }
    
    @keyframes clearContent {
        0% { opacity: 0; filter: blur(5px); }
        100% { opacity: 1; filter: blur(0px); }
    }
</style>

<div class="loading-overlay">
    <div class="loading-content">
        <div class="loading-title">ITOOK Library</div>
        <div class="progress-container">
            <div class="progress-bar"></div>
        </div>
        <div style="color: white; font-family: monospace;">Loading Assets...</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- CONFIGURATION API ---
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
    # Migration logic cũ (nếu có)
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
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# --- HELPER FUNCTIONS ---
def navigate_to(page):
    st.session_state.show_upgrade_modal = False
    if page == 'wiki':
        # Reset state wiki khi vào mới để tránh lỗi hiển thị cũ
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
        # Điều chỉnh tỷ lệ cột navbar
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
    
    st.write("")

@st.dialog("🚀 Upgrade Your Experience", width="large")
def show_upgrade_dialog():
    st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h3>Discover More with Advanced Version</h3>
            <p>Trải nghiệm phiên bản nâng cao với nhiều tính năng độc quyền hơn.</p>
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

# --- PAGE: HOMEPAGE ---
def show_homepage():
    # Sử dụng ảnh nền đẹp
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
    st.markdown('<p class="hero-subtitle">Find your Waifu, Discover new Worlds.</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2:
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3:
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')

    # Random Manga Section
    if st.session_state.random_manga_item is None:
        st.session_state.random_manga_item = get_random_manga_data()

    def shuffle_manga():
        st.session_state.random_manga_item = get_random_manga_data()

    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color: #ffd700;">✨ Manga of the Day</h3>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3], gap="large")
            with col_img:
                img_url = manga.get('images', {}).get('jpg', {}).get('large_image_url')
                if img_url: st.image(img_url, use_container_width=True)
                st.button("🔄 Shuffle New", on_click=shuffle_manga, use_container_width=True)
                
                manga_id = manga.get('mal_id')
                in_fav = is_favorited(manga_id, 'media')
                btn_label = "💔 Remove Favorite" if in_fav else "❤️ Add to Favorites"
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
                if manga.get('url'): st.markdown(f"[📖 Read more on MyAnimeList]({manga.get('url')})")

# --- PAGE: AI RECOMMENDATION ---
def show_recommend_page():
    set_global_style("test1.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🤖 AI Personal Recommendation")
    st.markdown("Let our AI analyze your preferences and suggest your next obsession!")
    
    with st.container(border=True):
        with st.form("ai_rec_form"):
            c1, c2 = st.columns(2)
            with c1:
                age = st.slider("🎂 Age:", 10, 80, 20)
                mood = st.selectbox("🎭 Mood:", ["Happy", "Sad", "Adventurous", "Chill", "Dark/Mysterious", "Romantic"])
            with c2:
                content_type = st.selectbox("📺 Looking for:", ["Anime", "Manga", "Light Novel"])
                style = st.selectbox("🎨 Style:", ["Action Packed", "Slow Life", "Mind Bending", "Emotional", "Horror/Thriller"])
            
            interests = st.text_area("💭 Describe your hobbies/interests:", placeholder="E.g. I like coding, cyberpunk themes, complex villains, and cats...")
            
            submit = st.form_submit_button("✨ Generate Recommendations", type="primary", use_container_width=True)
            
        if submit and interests:
            with st.spinner("AI is thinking..."):
                recs = get_ai_recommendations(age, interests, mood, style, content_type)
                if recs:
                    st.session_state.recommendations = recs
                    add_to_history("AI_Recommend", f"{content_type} for {mood} mood", f"Generated {len(recs)} items")
                    st.rerun()
                else:
                    st.error("AI could not generate a response. Please try again.")

    if st.session_state.recommendations:
        st.markdown("### 🎯 Your Results:")
        for idx, item in enumerate(st.session_state.recommendations):
            with st.container(border=True):
                c_a, c_b = st.columns([1, 4])
                with c_a:
                    st.markdown(f"## #{idx+1}")
                with c_b:
                    st.header(item['title'])
                    st.caption(f"Genre: {item.get('genre', 'N/A')}")
                    st.info(item['reason'])
                    search_url = f"https://myanimelist.net/search/all?q={item['title'].replace(' ', '%20')}"
                    st.markdown(f"[🔍 Search on Database]({search_url})")

# --- PAGE: GENRE EXPLORER ---
def show_genre_page():
    set_global_style("test4.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("📂 Genre Explorer")
    
    col_type, col_sort = st.columns(2)
    with col_type: content_type = st.selectbox("📖 Content type:", ["anime", "manga"])
    with col_sort: order_by = st.selectbox("📅 Sort by:", ["Newest", "Oldest", "Most Popular"])

    with st.spinner(f"Loading genre list for {content_type}..."):
        genre_map = get_genre_map(content_type)
    
    if genre_map:
        excluded = ["Hentai", "Ecchi", "Erotica", "Harem"]
        genre_map = {k: v for k, v in genre_map.items() if k not in excluded}
        selected_names = st.multiselect("📚 Choose genres:", sorted(genre_map.keys()))
        
        if st.button("🔍 Start Searching", type="primary", use_container_width=True):
            if not selected_names: st.warning("⚠️ Please choose at least one genre.")
            else:
                selected_ids = [str(genre_map[name]) for name in selected_names]
                genre_params = ",".join(selected_ids)
                sort_param, order_param = "desc", "score"
                if order_by == "Newest": order_param, sort_param = "start_date", "desc"
                elif order_by == "Oldest": order_param, sort_param = "start_date", "asc"
                
                url = f"https://api.jikan.moe/v4/{content_type}?genres={genre_params}&order_by={order_param}&sort={sort_param}&limit=10"
                add_to_history("Genre_Search", f"{content_type}: {', '.join(selected_names)}", f"Sort: {order_by}")
                
                with st.spinner("Fetching data..."):
                    try:
                        r = requests.get(url)
                        if r.status_code == 200:
                            data = r.json().get('data', [])
                            if data:
                                st.success(f"✅ Found {len(data)} results!")
                                st.markdown("---")
                                for item in data:
                                    with st.container(border=True):
                                        c1, c2 = st.columns([1, 4])
                                        with c1: 
                                            st.image(item.get('images', {}).get('jpg', {}).get('image_url'), use_container_width=True)
                                            manga_id = item.get('mal_id')
                                            in_fav = is_favorited(manga_id, 'media')
                                            btn_label = "💔" if in_fav else "❤️ Add"
                                            if st.button(btn_label, key=f"fav_btn_{manga_id}", use_container_width=True):
                                                toggle_favorite(item, 'media')
                                                st.rerun()
                                        with c2:
                                            st.subheader(f"📺 {item.get('title_english') or item.get('title')}")
                                            st.write(f"**Summary:** {item.get('synopsis', 'No summary')[:250]}...")
                                            st.markdown(f"[🔗 View on MyAnimeList]({item.get('url', '#')})")
                            else: st.warning("No results found.")
                    except: st.error("Connection Error")

# --- PAGE: FAVORITES ---
def show_favorites_page():
    set_global_style("test2.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.title("❤️ My Favorites Collection")
    
    tab1, tab2 = st.tabs(["📚 Animes & Mangas", "🦸 Characters"])
    
    with tab1:
        media_list = st.session_state.favorites['media']
        if not media_list:
            st.info("No Animes/Mangas in favorites yet.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(media_list):
                with cols[i % 3]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                        st.subheader(item.get('title'))
                        st.caption(f"Score: {item.get('score', 'N/A')}")
                        if st.button("💔 Remove", key=f"rm_media_{item['mal_id']}", use_container_width=True):
                            toggle_favorite(item, 'media')
                            st.rerun()
                            
    with tab2:
        char_list = st.session_state.favorites['characters']
        if not char_list:
            st.info("No Characters in favorites yet.")
        else:
            cols = st.columns(4)
            for i, item in enumerate(char_list):
                with cols[i % 4]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                        st.subheader(item.get('title'))
                        if st.button("💔 Remove", key=f"rm_char_{item['mal_id']}", use_container_width=True):
                            toggle_favorite(item, 'characters')
                            st.rerun()

# --- PAGE: WIKI CHARACTER ---
def show_wiki_page():
    set_global_style("test3.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🕵️ Character Wiki & Vision")
    
    # State initialization for wiki
    if 'wiki_search_results' not in st.session_state: st.session_state.wiki_search_results = None
    if 'wiki_ai_analysis' not in st.session_state: st.session_state.wiki_ai_analysis = None
    if 'wiki_selected_char' not in st.session_state: st.session_state.wiki_selected_char = None
    if 'search_source' not in st.session_state: st.session_state.search_source = None

    def clear_previous_results():
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None

    def display_final_result():
        if st.session_state.wiki_ai_analysis and st.session_state.wiki_selected_char:
            info = st.session_state.wiki_selected_char
            ai_text = st.session_state.wiki_ai_analysis
            st.markdown("---")
            c_img, c_info = st.columns([1, 2])
            with c_img: 
                st.image(info['images']['jpg']['image_url'], use_container_width=True)
                
                char_id = info['mal_id']
                in_fav = is_favorited(char_id, 'characters')
                btn_label = "💔 Unfavorite" if in_fav else "❤️ Favorite Character"
                if st.button(btn_label, key="wiki_char_fav"):
                    toggle_favorite(info, 'characters')
                    st.rerun()
                    
            with c_info:
                st.header(info['name'])
                st.subheader(f"Japanese: {info.get('name_kanji', '')}")
                st.success(ai_text, icon="📝")

    tab1, tab2 = st.tabs(["🔤 Search by Name", "📸 Search by Image"])
    
    with tab1:
        def execute_text_search():
            query = st.session_state.search_input
            if query:
                clear_previous_results()
                st.session_state.search_source = "text"
                st.session_state.wiki_search_results = get_character_data(query)
                add_to_history("Wiki_Search_Text", query, "Searched by name")

        st.text_input("Enter Character Name:", placeholder="E.g: Naruto...", key="search_input", on_change=execute_text_search)

        if st.session_state.wiki_search_results:
            results = st.session_state.wiki_search_results
            if len(results) > 0:
                char_opts = {f"{c['name']} (ID: {c['mal_id']})": c for c in results}
                selected_key = st.selectbox("Select character:", list(char_opts.keys()), key="char_select_box")
                
                if st.button("🚀 Analyze Profile", type="primary", use_container_width=True):
                    selected_info = char_opts[selected_key]
                    st.session_state.wiki_selected_char = selected_info
                    st.session_state.search_source = "text"
                    
                    st.markdown("---")
                    c1, c2 = st.columns([1, 2])
                    with c1: st.image(selected_info['images']['jpg']['image_url'], use_container_width=True)
                    with c2:
                        st.header(selected_info['name'])
                        placeholder = st.empty()
                        full_text = ""
                        try:
                            stream_response = generate_ai_stream(selected_info)
                            for chunk in stream_response:
                                if hasattr(chunk, 'text'):
                                    full_text += chunk.text
                                    placeholder.success(full_text + "▌", icon="📝") 
                            placeholder.success(full_text, icon="📝")
                            st.session_state.wiki_ai_analysis = full_text
                            add_to_history("Wiki_Analysis", selected_info['name'], "AI Profile Generated")
                        except Exception as e: st.error(f"AI Error: {e}")
            else: st.warning("No character found.")
        elif st.session_state.search_source == "text" and st.session_state.wiki_ai_analysis:
            display_final_result()

    with tab2:
        st.info("Upload an anime screenshot.")
        uploaded = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"], key="vision_uploader")
        
        if uploaded:
            st.image(uploaded, width=150, caption="Preview")
            if st.button("🚀 Scan Character", key="btn_scan_vision", type="primary"):
                clear_previous_results()
                st.session_state.search_source = "image"
                with st.spinner("Gemini is Identifying..."):
                    name = ai_vision_detect(uploaded)
                    add_to_history("Wiki_Vision", "Image Upload", f"Detected: {name}")
                if name and name != "Unknown":
                    st.success(f"Detected: **{name}**")
                    info = get_one_character_data(name)
                    if info:
                        st.session_state.wiki_selected_char = info
                        # Tự động trigger phân tích
                        st.markdown("---")
                        c1, c2 = st.columns([1, 2])
                        with c1: st.image(info['images']['jpg']['image_url'], use_container_width=True)
                        with c2:
                            st.header(info['name'])
                            placeholder = st.empty()
                            full_text = ""
                            try:
                                stream_response = generate_ai_stream(info)
                                for chunk in stream_response:
                                    if hasattr(chunk, 'text'):
                                        full_text += chunk.text
                                        placeholder.success(full_text + "▌", icon="📝")
                                placeholder.success(full_text, icon="📝")
                                st.session_state.wiki_ai_analysis = full_text
                            except Exception as e: st.error(f"AI Error: {e}")
                    else: st.warning(f"Found '{name}' but no info on MyAnimeList.")
                else: st.error("Cannot identify character.")
        elif st.session_state.search_source == "image" and st.session_state.wiki_ai_analysis:
            display_final_result()

def show_contact_page():
    set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
        return
    
    st.markdown('<div class="content-box"><h2>📞 Contact Us</h2><p>Email: admin@itooklibrary.com</p></div>', unsafe_allow_html=True)

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
elif st.session_state.current_page == 'contact': 
    show_contact_page()
