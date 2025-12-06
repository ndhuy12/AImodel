import streamlit as st
import google.generativeai as genai
import requests

# Import custom modules
from style_css import set_global_style
from jikan_services import get_genre_map, get_character_data, get_one_character_data, get_random_manga_data
from ai_service import ai_vision_detect, generate_ai_stream

# # Configuration
st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "AIzaSyDS4IfeA-9eXbn-C9J3m4PFqDyU7L1s4CY" # Lưu ý: Nên bảo mật API Key này

genai.configure(api_key=API_KEY)

# # State Management
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'favorites' not in st.session_state:
    st.session_state.favorites = [] 
if 'random_manga_item' not in st.session_state:
    st.session_state.random_manga_item = None

def navigate_to(page):
    if page == 'wiki':
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
        if 'search_input' in st.session_state:
            st.session_state.search_input = ""
    st.session_state.current_page = page
    st.rerun()

# # Favorites Logic
def is_favorited(manga_id):
    for item in st.session_state.favorites:
        if item['mal_id'] == manga_id:
            return True
    return False

def toggle_favorite(manga_data):
    manga_id = manga_data.get('mal_id')
    if is_favorited(manga_id):
        st.session_state.favorites = [item for item in st.session_state.favorites if item['mal_id'] != manga_id]
        st.toast(f"💔 Removed '{manga_data.get('title')}' from Favorites", icon="🗑️")
    else:
        fav_item = {
            'mal_id': manga_id,
            'title': manga_data.get('title'),
            'title_english': manga_data.get('title_english'),
            'image_url': manga_data.get('images', {}).get('jpg', {}).get('image_url'),
            'score': manga_data.get('score'),
            'url': manga_data.get('url'),
            'type': manga_data.get('type', 'Manga')
        }
        st.session_state.favorites.append(fav_item)
        st.toast(f"❤️ Added '{manga_data.get('title')}' to Favorites", icon="✅")

# # Navigation bar
def show_navbar():
    with st.container():
        st.markdown('<div class="nav-container"></div>', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([2.5, 0.7, 1.0, 1.0, 1.0], gap="small", vertical_alignment="center")
        
        with col1: st.markdown('<p class="nav-logo">ITOOK Library</p>', unsafe_allow_html=True)
        with col2: 
            if st.button("Home", use_container_width=True): navigate_to('home')
        with col3:
            with st.popover("Services", use_container_width=True):
                st.markdown("### 🛠 Utilities")
                if st.button("🕵️ Wiki Search", use_container_width=True): navigate_to('wiki')
                if st.button("📂 Genre Explorer", use_container_width=True): navigate_to('genre')
                if st.button("🤖 AI Recommend", use_container_width=True): navigate_to('recommend')
        with col4:
            if st.button("Favorites", use_container_width=True): navigate_to('favorites')
        with col5:
            if st.button("Contact", use_container_width=True): navigate_to('contact')
    st.write("")

# # Homepage
def show_homepage():
    set_global_style("#102C57") 
    show_navbar() 
    
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
            font-family: 'Arial', sans-serif; font-size: 24px !important; color: #e0e0e0 !important;
            text-align: center; margin-top: -20px; margin-bottom: 40px; font-style: italic;
        }
        div.stButton > button {
            height: 100px; font-size: 18px; font-weight: bold; 
            border-radius: 15px; border: 2px solid #00D4FF; transition: all 0.3s;
        }
        div.stButton > button:hover {
            background-color: rgba(0, 212, 255, 0.1); transform: translateY(-5px);
        }
        div[data-testid="stHorizontalBlock"] button { height: auto !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="hero-title">Welcome to ITOOK Library!</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">What adventure awaits you today?</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2:
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3:
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')

    # Daily Pick Section
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
                st.button("🔄 Shuffle New Manga", on_click=shuffle_manga, use_container_width=True)
                
                manga_id = manga.get('mal_id')
                in_fav = is_favorited(manga_id)
                btn_label = "💔 Remove Favorite" if in_fav else "❤️ Add to Favorites"
                if st.button(btn_label, key="daily_fav_btn", use_container_width=True):
                    toggle_favorite(manga)
                    st.rerun()

            with col_info:
                title = manga.get('title_english') or manga.get('title')
                st.markdown(f"## {title}")
                st.markdown(f"**⭐ Score:** {manga.get('score', 'N/A')} | **📌 Status:** {manga.get('status', 'Unknown')}")
                
                synopsis = manga.get('synopsis')
                if synopsis and len(synopsis) > 600: synopsis = synopsis[:600] + "..."
                st.write(synopsis)
                
                if manga.get('url'): st.markdown(f"[📖 Read more on MyAnimeList]({manga.get('url')})")

# # Pages Logic
def show_genre_page():
    set_global_style("https://images3.alphacoders.com/812/thumb-1920-812062.png")
    show_navbar()
    
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
                                            in_fav = is_favorited(manga_id)
                                            btn_label = "💔" if in_fav else "❤️ Add"
                                            if st.button(btn_label, key=f"fav_btn_{manga_id}", use_container_width=True):
                                                toggle_favorite(item)
                                                st.rerun()
                                        with c2:
                                            st.subheader(f"📺 {item.get('title_english') or item.get('title')}")
                                            st.write(f"**Summary:** {item.get('synopsis', 'No summary')[:250]}...")
                                            st.markdown(f"[🔗 View on MyAnimeList]({item.get('url', '#')})")
                            else: st.warning("No results found.")
                    except: st.error("Connection Error")

def show_favorites_page():
    set_global_style("https://wallpapers.com/images/hd/aesthetic-anime-bedroom-lq7b5j3x5x5y5x5.jpg")
    show_navbar()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("❤️ My Favorites Collection")
    
    if not st.session_state.favorites:
        st.info("Your collection is empty. Go explore and add some stories!")
    else:
        st.write(f"You have **{len(st.session_state.favorites)}** items in your library.")
        st.markdown("---")
        for item in st.session_state.favorites:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 4, 1])
                with c1:
                    if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                with c2:
                    st.subheader(item.get('title_english') or item.get('title'))
                    st.caption(f"Type: {item.get('type')} | Score: {item.get('score', 'N/A')}")
                    if item.get('url'): st.markdown(f"[🔗 Read More]({item['url']})")
                with c3:
                    if st.button("💔 Remove", key=f"remove_fav_{item['mal_id']}", use_container_width=True):
                        toggle_favorite(item)
                        st.rerun()

def show_wiki_page():
    set_global_style("test.jpg")
    show_navbar()
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🕵️ Character Wiki & Vision")
    
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
            with c_img: st.image(info['images']['jpg']['image_url'], use_container_width=True)
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
                with st.spinner("Gemini 2.0 is Identifying..."):
                    name = ai_vision_detect(uploaded)
                if name != "Unknown":
                    st.success(f"Detected: **{name}**")
                    info = get_one_character_data(name)
                    if info:
                        st.session_state.wiki_selected_char = info
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

def show_recommend_page():
    set_global_style("https://images.alphacoders.com/133/thumb-1920-1330275.png")
    show_navbar()
    st.markdown('<div class="content-box"><h2>🤖 AI Recommend (Coming Soon)</h2></div>', unsafe_allow_html=True)

def show_contact_page():
    set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
    show_navbar()
    st.markdown('<div class="content-box"><h2>📞 Contact Us</h2></div>', unsafe_allow_html=True)

# # Router
if st.session_state.current_page == 'home': show_homepage()
elif st.session_state.current_page == 'wiki': show_wiki_page()
elif st.session_state.current_page == 'genre': show_genre_page()
elif st.session_state.current_page == 'recommend': show_recommend_page()
elif st.session_state.current_page == 'favorites': show_favorites_page()

elif st.session_state.current_page == 'contact': show_contact_page()


