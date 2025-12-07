import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import os
import time
from datetime import datetime, date
from style_css import set_global_style

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

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_API_KEY"]
else:
    st.error("API Key is missing. Please check secrets.toml.")
    st.stop()

genai.configure(api_key=API_KEY)

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

if 'genre_search_results' not in st.session_state:
    st.session_state.genre_search_results = None

if 'genre_searching' not in st.session_state:
    st.session_state.genre_searching = False

if 'ai_recommending' not in st.session_state:
    st.session_state.ai_recommending = False

def navigate_to(page):
    st.session_state.show_upgrade_modal = False
    if page == 'wiki':
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
        st.session_state.analyzing = False
    if page == 'genre':
        st.session_state.genre_search_results = None
        st.session_state.genre_searching = False
    if page == 'recommend':
        st.session_state.recommendations = None
        st.session_state.ai_recommending = False
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

def show_recommend_page():
    set_global_style("test1.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🤖 AI Personal Recommendation")
    st.markdown("Let our AI analyze your preferences and suggest your next obsession!")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            age = st.slider("🎂 Age:", 10, 80, 20, key="rec_age")
            mood = st.selectbox("🎭 Mood:", ["Happy", "Sad", "Adventurous", "Chill", "Dark/Mysterious", "Romantic"], key="rec_mood")
        with c2:
            content_type = st.selectbox("📺 Looking for:", ["Anime", "Manga", "Light Novel"], key="rec_type")
            style = st.selectbox("🎨 Style:", ["Action Packed", "Slow Life", "Mind Bending", "Emotional", "Horror/Thriller"], key="rec_style")
        
        interests = st.text_area("💭 Describe your hobbies/interests:", 
                                placeholder="E.g. I like coding, cyberpunk themes, complex villains, and cats...",
                                key="rec_interests")
        
        submit_clicked = st.button("✨ Generate Recommendations", type="primary", use_container_width=True)
        
        if submit_clicked and interests:
            st.session_state.ai_recommending = True
            st.session_state.rec_params = {
                'age': age,
                'interests': interests,
                'mood': mood,
                'style': style,
                'content_type': content_type
            }
            st.rerun()
    
    if st.session_state.ai_recommending:
        params = st.session_state.rec_params
        
        with st.spinner("🤖 AI is thinking... (this may take 6-10 seconds)"):
            recs = get_ai_recommendations(
                params['age'], 
                params['interests'], 
                params['mood'], 
                params['style'], 
                params['content_type']
            )
        
        if recs:
            st.session_state.recommendations = recs
            st.session_state.ai_recommending = False
            add_to_history("AI_Recommend", f"{params['content_type']} for {params['mood']} mood", f"Generated {len(recs)} items")
            st.rerun()
        else:
            st.error("AI could not generate a response. Please try again.")
            st.session_state.ai_recommending = False

    if st.session_state.recommendations and not st.session_state.ai_recommending:
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

def show_genre_page():
    set_global_style("test4.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("📂 Genre Explorer")
    
    col_type, col_sort = st.columns(2)
    with col_type: 
        content_type = st.selectbox("📖 Content type:", ["anime", "manga"], key="genre_content_type")
    with col_sort: 
        order_by = st.selectbox("📅 Sort by:", ["Newest", "Oldest", "Most Popular"], key="genre_sort")

    with st.spinner(f"Loading genre list for {content_type}..."):
        genre_map = get_genre_map(content_type)
    
    if genre_map:
        excluded = ["Hentai", "Ecchi", "Erotica", "Harem"]
        genre_map = {k: v for k, v in genre_map.items() if k not in excluded}
        selected_names = st.multiselect("📚 Choose genres:", sorted(genre_map.keys()), key="genre_selection")
        
        search_clicked = st.button("🔍 Start Searching", type="primary", use_container_width=True)
        
        if search_clicked:
            if not selected_names:
                st.warning("⚠️ Please choose at least one genre.")
            else:
                st.session_state.genre_searching = True
                st.session_state.genre_params = {
                    'content_type': content_type,
                    'selected_names': selected_names,
                    'order_by': order_by,
                    'genre_map': genre_map
                }
                st.rerun()
    
    if st.session_state.genre_searching:
        params = st.session_state.genre_params
        
        selected_ids = [str(params['genre_map'][name]) for name in params['selected_names']]
        genre_params = ",".join(selected_ids)
        sort_param, order_param = "desc", "score"
        
        if params['order_by'] == "Newest": 
            order_param, sort_param = "start_date", "desc"
        elif params['order_by'] == "Oldest": 
            order_param, sort_param = "start_date", "asc"
        
        url = f"https://api.jikan.moe/v4/{params['content_type']}?genres={genre_params}&order_by={order_param}&sort={sort_param}&limit=10"
        add_to_history("Genre_Search", f"{params['content_type']}: {', '.join(params['selected_names'])}", f"Sort: {params['order_by']}")
        
        with st.spinner("Fetching data..."):
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json().get('data', [])
                    st.session_state.genre_search_results = data
                    st.session_state.genre_searching = False
                    st.rerun()
                else:
                    st.error(f"API Error: {r.status_code}")
                    st.session_state.genre_searching = False
            except Exception as e:
                st.error(f"Connection Error: {e}")
                st.session_state.genre_searching = False
    
    if st.session_state.genre_search_results and not st.session_state.genre_searching:
        data = st.session_state.genre_search_results
        
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
                        synopsis = item.get('synopsis', 'No summary')
                        if synopsis and len(synopsis) > 250:
                            synopsis = synopsis[:250] + "..."
                        st.write(f"**Summary:** {synopsis}")
                        st.markdown(f"[🔗 View on MyAnimeList]({item.get('url', '#')})")
        else:
            st.warning("No results found.")

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
            st.write(f"Count: {len(media_list)}")
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
            st.write(f"Count: {len(char_list)}")
            cols = st.columns(4)
            for i, item in enumerate(char_list):
                with cols[i % 4]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                        st.subheader(item.get('title'))
                        if st.button("💔 Remove", key=f"rm_char_{item['mal_id']}", use_container_width=True):
                            toggle_favorite(item, 'characters')
                            st.rerun()

def show_history_page():
    set_global_style("test1.png") 
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.title("📜 Activity History")
    
    if st.button("🗑️ Clear History"):
        st.session_state.search_history = []
        st.rerun()
        
    history = st.session_state.search_history
    if not history:
        st.info("No activity recorded yet.")
    else:
        for item in history:
            with st.expander(f"🕒 {item['timestamp']} - {item['type']}"):
                st.write(f"**Query:** {item['query']}")
                if item.get('details'):
                    st.caption(f"Details: {item['details']}")

def show_wiki_page():
    set_global_style("test3.jpg")
    show_navbar()
    
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🕵️ Character Wiki & Vision")
    
    stats = get_api_stats()
    if stats['calls_last_minute'] >= 10:
        st.warning(f"⚠️ API Usage: {stats['limit']} - Approaching limit!")
    elif stats['calls_last_minute'] >= 8:
        st.info(f"ℹ️ API Usage: {stats['limit']}")
    
    if 'wiki_search_results' not in st.session_state: 
        st.session_state.wiki_search_results = None
    if 'wiki_ai_analysis' not in st.session_state: 
        st.session_state.wiki_ai_analysis = None
    if 'wiki_selected_char' not in st.session_state: 
        st.session_state.wiki_selected_char = None
    if 'search_source' not in st.session_state: 
        st.session_state.search_source = None
    if 'analyzing' not in st.session_state:
        st.session_state.analyzing = False

    def clear_previous_results():
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
        st.session_state.analyzing = False

    def display_character_profile(info, ai_text):
        st.markdown("---")
        c_img, c_info = st.columns([1, 2])
        
        with c_img: 
            st.image(info['images']['jpg']['image_url'], use_container_width=True)
            
            char_id = info['mal_id']
            in_fav = is_favorited(char_id, 'characters')
            btn_label = "💔 Unfavorite" if in_fav else "❤️ Favorite"
            
            if st.button(btn_label, key=f"wiki_fav_{char_id}"):
                toggle_favorite(info, 'characters')
                st.rerun()
                
        with c_info:
            st.header(info['name'])
            st.subheader(f"Japanese: {info.get('name_kanji', '')}")
            
            char_id = info.get('mal_id')
            about = info.get('about', 'N/A')
            about_preview = about[:200] if about and about != 'N/A' else "no_data"
            cache_key = f"{char_id}_{hash(about_preview)}"
            
            if cache_key in st.session_state.get('character_analysis_cache', {}):
                st.success("⚡ Loaded from cache (instant!)", icon="⚡")
            
            st.success(ai_text, icon="📝")

    tab1, tab2 = st.tabs(["🔤 Search by Name", "📸 Search by Image"])
    
    with tab1:
        search_query = st.text_input(
            "Enter Character Name:", 
            placeholder="E.g: Naruto...", 
            key="search_input"
        )
        
        if st.button("🔍 Search", type="primary", use_container_width=True):
            if search_query:
                clear_previous_results()
                st.session_state.wiki_search_results = get_character_data(search_query)
                st.session_state.search_source = "text"
                add_to_history("Wiki_Search_Text", search_query, "Searched by name")
                st.rerun()

        if st.session_state.wiki_search_results and st.session_state.search_source == "text":
            results = st.session_state.wiki_search_results
            
            if len(results) > 0:
                char_opts = {f"{c['name']} (ID: {c['mal_id']})": c for c in results}
                selected_key = st.selectbox(
                    "Select character:", 
                    list(char_opts.keys()), 
                    key="char_select_box"
                )
                
                selected_info = char_opts<function_calls>
<invoke name="artifacts">
<parameter name="command">update</parameter>
<parameter name="id">main_complete_fixed</parameter>
<parameter name="old_str">                selected_info = char_opts</parameter>
<parameter name="new_str">                selected_info = char_opts[selected_key]
            st.info("💡 Tip: Analysis results are cached. Re-analyzing the same character is instant!")
            
            analyze_clicked = st.button(
                "🚀 Analyze Profile", 
                type="primary", 
                use_container_width=True,
                key="analyze_btn"
            )
            
            if analyze_clicked:
                st.session_state.wiki_selected_char = selected_info
                st.session_state.analyzing = True
                st.rerun()
            
            if (st.session_state.wiki_selected_char and 
                st.session_state.wiki_selected_char['mal_id'] == selected_info['mal_id']):
                
                if st.session_state.analyzing:
                    st.markdown("---")
                    c1, c2 = st.columns([1, 2])
                    
                    with c1: 
                        st.image(selected_info['images']['jpg']['image_url'], use_container_width=True)
                    
                    with c2:
                        st.header(selected_info['name'])
                        
                        char_id = selected_info.get('mal_id')
                        about = selected_info.get('about', 'N/A')
                        about_preview = about[:200] if about and about != 'N/A' else "no_data"
                        cache_key = f"{char_id}_{hash(about_preview)}"
                        
                        if cache_key in st.session_state.get('character_analysis_cache', {}):
                            st.success("⚡ Loading from cache...")
                            cached_text = st.session_state.character_analysis_cache[cache_key]
                            st.success(cached_text, icon="📝")
                            st.session_state.wiki_ai_analysis = cached_text
                            st.session_state.analyzing = False
                        else:
                            placeholder = st.empty()
                            placeholder.info("🤖 AI is analyzing... (6-10 seconds)")
                            
                            full_text = ""
                            try:
                                stream_response = generate_ai_stream(selected_info)
                                
                                for chunk in stream_response:
                                    if hasattr(chunk, 'text'):
                                        full_text += chunk.text
                                        placeholder.success(full_text + "▌", icon="📝")
                                
                                placeholder.success(full_text, icon="📝")
                                st.session_state.wiki_ai_analysis = full_text
                                st.session_state.analyzing = False
                                add_to_history("Wiki_Analysis", selected_info['name'], "AI Profile Generated")
                                
                            except Exception as e:
                                placeholder.error(f"❌ Error: {e}")
                                st.session_state.analyzing = False
                
                elif st.session_state.wiki_ai_analysis:
                    display_character_profile(selected_info, st.session_state.wiki_ai_analysis)
        else:
            st.warning("No character found.")

with tab2:
    st.info("📸 Upload an anime screenshot to identify the character.")
    st.warning("⚠️ Vision detection uses more API quota. Use sparingly!")
    
    uploaded = st.file_uploader(
        "Upload Image", 
        type=["jpg", "png", "jpeg"], 
        key="vision_uploader"
    )
    
    if uploaded:
        st.image(uploaded, width=150, caption="Preview")
        st.info("💡 This will use AI vision (8-10 seconds wait time)")
        
        scan_clicked = st.button(
            "🚀 Scan Character", 
            key="btn_scan_vision", 
            type="primary"
        )
        
        if scan_clicked:
            clear_previous_results()
            st.session_state.search_source = "image"
            st.session_state.analyzing = True
            st.rerun()
    
    if (st.session_state.search_source == "image" and 
        st.session_state.analyzing and 
        uploaded):
        
        with st.spinner("🤖 Gemini Vision is analyzing..."):
            name = ai_vision_detect(uploaded)
            add_to_history("Wiki_Vision", "Image Upload", f"Detected: {name}")
        
        if name != "Unknown":
            st.success(f"✅ Detected: **{name}**")
            info = get_one_character_data(name)
            
            if info:
                st.session_state.wiki_selected_char = info
                
                st.markdown("---")
                c1, c2 = st.columns([1, 2])
                
                with c1: 
                    st.image(info['images']['jpg']['image_url'], use_container_width=True)
                
                with c2:
                    st.header(info['name'])
                    
                    placeholder = st.empty()
                    full_text = ""
                    
                    try:
                        with st.spinner("Generating profile..."):
                            stream_response = generate_ai_stream(info)
                            
                        for chunk in stream_response:
                            if hasattr(chunk, 'text'):
                                full_text += chunk.text
                                placeholder.success(full_text + "▌", icon="📝")
                        
                        placeholder.success(full_text, icon="📝")
                        st.session_state.wiki_ai_analysis = full_text
                        st.session_state.analyzing = False
                        
                    except Exception as e:
                        placeholder.error(f"❌ Error: {e}")
                        st.session_state.analyzing = False
            else:
                st.warning(f"Found '{name}' but no info on MyAnimeList.")
                st.session_state.analyzing = False
        else:
            st.error("❌ Cannot identify character. Try a clearer image or use text search.")
            st.session_state.analyzing = False
    
    elif (st.session_state.search_source == "image" and 
          st.session_state.wiki_ai_analysis and 
          st.session_state.wiki_selected_char):
        display_character_profile(
            st.session_state.wiki_selected_char, 
            st.session_state.wiki_ai_analysis
        )

st.markdown("---")
with st.expander("🗂️ Cache Management"):
    if 'character_analysis_cache' in st.session_state:
        cache_size = len(st.session_state.character_analysis_cache)
        st.caption(f"📊 Cached analyses: {cache_size}")
        
        if cache_size > 0:
            if st.button("🗑️ Clear All Cache"):
                clear_analysis_cache()
                st.success("Cache cleared!")
                st.rerun()
    else:
        st.caption("📊 No cached data yet")
def show_contact_page():
set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
show_navbar()
if st.session_state.show_upgrade_modal:
    show_upgrade_dialog()
    return

st.markdown('<div class="content-box"><h2>📞 Contact Us</h2><p>Email: admin@itooklibrary.com</p></div>', unsafe_allow_html=True)
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
show_contact_page()</parameter>
