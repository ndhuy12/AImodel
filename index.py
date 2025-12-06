import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import base64
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

# ⚠️ API KEY SETUP
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "AIzaSyDS4IfeA-9eXbn-C9J3m4PFqDyU7L1s4CY"

genai.configure(api_key=API_KEY)

# --- STATE MANAGEMENT ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

# [MỚI] Khởi tạo danh sách yêu thích
if 'favorites' not in st.session_state:
    st.session_state.favorites = [] 

if 'random_manga_item' not in st.session_state:
    st.session_state.random_manga_item = None

def navigate_to(page):
    # [MỚI] Nếu chuyển đến trang Wiki, xóa sạch dữ liệu tìm kiếm cũ
    if page == 'wiki':
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
        
        # Xóa luôn chữ trong ô nhập liệu (nếu có) để trang trắng tinh
        if 'search_input' in st.session_state:
            st.session_state.search_input = ""
            
    # [MỚI] Tương tự, nếu muốn trang Genre cũng reset khi quay lại thì thêm dòng này:
    if page == 'genre':
        # Xóa lựa chọn cũ của Genre nếu cần (tùy chọn)
        pass 

    st.session_state.current_page = page
    st.rerun()

# --- [MỚI] FAVORITES LOGIC ---
def is_favorited(manga_id):
    """Kiểm tra xem truyện đã có trong danh sách chưa"""
    for item in st.session_state.favorites:
        if item['mal_id'] == manga_id:
            return True
    return False

def toggle_favorite(manga_data):
    """Thêm hoặc xóa truyện khỏi danh sách yêu thích"""
    manga_id = manga_data.get('mal_id')
    if is_favorited(manga_id):
        # Nếu có rồi thì xóa (Lọc bỏ item có ID trùng)
        st.session_state.favorites = [item for item in st.session_state.favorites if item['mal_id'] != manga_id]
        st.toast(f"💔 Removed '{manga_data.get('title')}' from Favorites", icon="🗑️")
    else:
        # Nếu chưa có thì thêm vào
        # Chỉ lưu các thông tin cần thiết để nhẹ bộ nhớ
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

# --- 2. SERVICE FUNCTIONS (LOGIC) ---

def get_base64_of_bin_file(filename):
    file_path = os.path.join(os.getcwd(), "resources", filename)
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

@st.cache_data(ttl=3600)
def get_genre_map(content_type="anime"):
    url = f"https://api.jikan.moe/v4/genres/{content_type}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', [])
            return {item['name']: item['mal_id'] for item in data}
        return {}
    except: return {}

@st.cache_data(ttl=3600)
def get_character_data(name):
    url = f"https://api.jikan.moe/v4/characters?q={name}&limit=10"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    except: return []

def get_one_character_data(name):
    results = get_character_data(name)
    return results[0] if results else None

def get_random_manga_data():
    url = "https://api.jikan.moe/v4/random/manga"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', {})
            for genre in data.get('genres', []):
                if genre['name'] in ['Hentai', 'Erotica', 'Harem']:
                    return get_random_manga_data()
            return data
        return None
    except: return None

def ai_vision_detect(image_data):
    image = Image.open(image_data)
    model = genai.GenerativeModel('gemini-2.0-flash')
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

# --- 3. UI STYLING (GLOBAL CSS) ---

def set_global_style(bg_source):
    image_css = ""
    if bg_source.startswith("http"):
        image_css = f'url("{bg_source}")'
    else:
        b64_data = get_base64_of_bin_file(bg_source)
        if b64_data:
            ext = "jpeg" if bg_source.lower().endswith((".jpg", ".jpeg")) else "png"
            image_css = f'url("data:image/{ext};base64,{b64_data}")'
        else:
            image_css = 'url("https://wallpapers.com/images/hd/library-background-4k-q0t2b8j0d1l1y5z3.jpg")'

    st.markdown(f"""
    <style>
    /* 1. Background */
    .stApp {{
        background-image: {image_css};
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }}
    
    /* 2. Text Color */
    h1, h2, h3, h4, p, span, div, label, li {{
        color: white !important;
        text-shadow: 2px 2px 6px #000000 !important;
        font-weight: 500;
    }}

    /* 3. ẨN THÀNH PHẦN THỪA */
    header {{display: none !important;}}
    [data-testid="stHeader"] {{display: none !important;}}
    .stStatusWidget, [data-testid="stStatusWidget"] {{
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
        width: 0 !important;
        opacity: 0 !important;
    }}
    div[data-testid="stDecoration"] {{ display: none !important; }}

    /* 4. IMAGE STYLE */
    div[data-testid="stImage"] {{ background-color: transparent !important; }}
    div[data-testid="stImage"] > img {{ border-radius: 12px !important; }}

    /* 5. NAVBAR STYLE */
    .block-container {{ padding-top: 0rem !important; margin-top: 10px !important; }}
    .nav-container {{ padding: 0; margin-bottom: 20px; }}

    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        text-shadow: 0px 2px 5px rgba(0,0,0,0.8);
        transition: all 0.3s ease;
    }}
    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #00D4FF !important;
        text-shadow: 0px 0px 10px #00D4FF;
        transform: scale(1.1);
    }}

    .nav-logo {{
        font-size: 24px; font-weight: 900; color: #fff; margin: 0; 
        font-family: 'Arial', sans-serif; text-transform: uppercase;
    }}
    
    /* 6. BUTTON STYLE (Primary) */
    button[kind="primary"] {{
        background: linear-gradient(90deg, #00D4FF, #005Bea) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
    }}
    </style>
    """, unsafe_allow_html=True)

# [CẬP NHẬT] NAVBAR MỚI - CÓ NÚT FAVORITES
def show_navbar():
    with st.container():
        st.markdown('<div class="nav-container"></div>', unsafe_allow_html=True)
        # Chia 5 cột: Logo | Home | Services | Favorites | Contact
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
            # Nút Favorites mới thêm
            if st.button("Favorites", use_container_width=True): navigate_to('favorites')
        with col5:
            if st.button("Contact", use_container_width=True): navigate_to('contact')
    st.write("")

# --- 4. PAGES ---

# === PAGE: HOME ===
def show_homepage():
    set_global_style("home_bg.jpg") 
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
            font-weight: normal !important;
            line-height: 1.3; margin-top: 20px;
        }
        .hero-subtitle {
            font-family: 'Arial', sans-serif;
            font-size: 24px !important;
            color: #e0e0e0 !important;
            text-align: center;
            margin-top: -20px; margin-bottom: 40px;
            font-weight: 300 !important; font-style: italic;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
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

    # --- DAILY PICK SECTION ---
    if st.session_state.random_manga_item is None:
        st.session_state.random_manga_item = get_random_manga_data()

    def shuffle_manga():
        st.session_state.random_manga_item = get_random_manga_data()

    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color: #ffd700;">✨ Story of the Day</h3>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3], gap="large")
            with col_img:
                img_url = manga.get('images', {}).get('jpg', {}).get('large_image_url')
                if img_url: st.image(img_url, use_container_width=True)
                
                # Nút Shuffle
                st.button("🔄 Shuffle New Story", on_click=shuffle_manga, use_container_width=True)
                
                # [MỚI] Nút Add to Favorites cho Daily Pick
                manga_id = manga.get('mal_id')
                in_fav = is_favorited(manga_id)
                btn_label = "💔 Remove Favorite" if in_fav else "❤️ Add to Favorites"
                if st.button(btn_label, key="daily_fav_btn", use_container_width=True):
                    toggle_favorite(manga)
                    st.rerun()

            with col_info:
                title = manga.get('title_english') or manga.get('title')
                st.markdown(f"## {title}")
                
                score = manga.get('score', 'N/A')
                status = manga.get('status', 'Unknown')
                chapters = manga.get('chapters')
                chapters_text = f"{chapters} Chaps" if chapters else "? Chaps"
                
                st.markdown(f"**⭐ Score:** {score} | **📌 Status:** {status} | **📚 Length:** {chapters_text}")
                
                synopsis = manga.get('synopsis')
                if synopsis:
                    if len(synopsis) > 600: synopsis = synopsis[:600] + "..."
                    st.write(synopsis)
                
                url = manga.get('url')
                if url: st.markdown(f"[📖 Read more on MyAnimeList]({url})")

# === PAGE: GENRE ===
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
                                            
                                            # [MỚI] Nút Add to Favorites trong Search Result
                                            manga_id = item.get('mal_id')
                                            in_fav = is_favorited(manga_id)
                                            btn_label = "💔" if in_fav else "❤️ Add"
                                            # Sử dụng key độc nhất bằng ID
                                            if st.button(btn_label, key=f"fav_btn_{manga_id}", use_container_width=True):
                                                toggle_favorite(item)
                                                st.rerun()

                                        with c2:
                                            st.subheader(f"📺 {item.get('title_english') or item.get('title')}")
                                            st.write(f"**Summary:** {item.get('synopsis', 'No summary')[:250]}...")
                                            st.markdown(f"[🔗 View on MyAnimeList]({item.get('url', '#')})")
                            else: st.warning("No results found.")
                    except: st.error("Connection Error")

# === PAGE: FAVORITES (ĐƯỢC LÀM MỚI HOÀN TOÀN) ===
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
        
        # Hiển thị danh sách yêu thích
        for item in st.session_state.favorites:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 4, 1])
                with c1:
                    if item.get('image_url'):
                        st.image(item['image_url'], use_container_width=True)
                
                with c2:
                    st.subheader(item.get('title_english') or item.get('title'))
                    st.caption(f"Type: {item.get('type')} | Score: {item.get('score', 'N/A')}")
                    if item.get('url'):
                        st.markdown(f"[🔗 Read More]({item['url']})")
                
                with c3:
                    # Nút xóa khỏi danh sách
                    if st.button("💔 Remove", key=f"remove_fav_{item['mal_id']}", use_container_width=True):
                        toggle_favorite(item) # Gọi hàm toggle để xóa
                        st.rerun() # Load lại trang để cập nhật danh sách

# === PAGE: WIKI (GIỮ NGUYÊN) ===
def show_wiki_page():
    set_global_style("wiki_bg.png")
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

# === PLACEHOLDERS ===
def show_recommend_page():
    set_global_style("https://images.alphacoders.com/133/thumb-1920-1330275.png")
    show_navbar()
    st.markdown('<div class="content-box"><h2>🤖 AI Recommend (Coming Soon)</h2></div>', unsafe_allow_html=True)

def show_contact_page():
    set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
    show_navbar()
    st.markdown('<div class="content-box"><h2>📞 Contact Us</h2></div>', unsafe_allow_html=True)

# --- ROUTER ---
if st.session_state.current_page == 'home': show_homepage()
elif st.session_state.current_page == 'wiki': show_wiki_page()
elif st.session_state.current_page == 'genre': show_genre_page()
elif st.session_state.current_page == 'recommend': show_recommend_page()
elif st.session_state.current_page == 'favorites': show_favorites_page()
elif st.session_state.current_page == 'contact': show_contact_page()