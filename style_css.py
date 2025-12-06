import streamlit as st
import base64
import os

def get_base64_of_bin_file(filename):
    file_path = os.path.join(os.getcwd(), "resources", filename)
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def set_global_style(bg_source):
    background_css = ""

    if bg_source.startswith("#"):
        background_css = f"""
            background-color: {bg_source} !important;
            background-image: none !important;
        """
    elif bg_source.startswith("http"):
        background_css = f"""
            background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), url("{bg_source}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        """
    else:
        b64_data = get_base64_of_bin_file(bg_source)
        if b64_data:
            ext = "jpeg" if bg_source.lower().endswith((".jpg", ".jpeg")) else "png"
            background_css = f"""
                background-image: url("data:image/{ext};base64,{b64_data}");
                background-size: cover;
                background-attachment: fixed;
                background-position: center;
            """
        else:
            background_css = "background-color: #0e1117;"

    st.markdown(f"""
    <style>
    .stApp {{
        {background_css}
    }}
    
    h1, h2, h3, h4, p, span, div, label, li {{
        color: white !important;
        text-shadow: 2px 2px 6px #000000 !important;
        font-weight: 500;
    }}

    header {{display: none !important;}}
    [data-testid="stHeader"] {{display: none !important;}}
    .stStatusWidget, [data-testid="stStatusWidget"] {{visibility: hidden !important; display: none !important;}}
    div[data-testid="stDecoration"] {{ display: none !important; }}

    div[data-testid="stImage"] {{ background-color: transparent !important; }}
    div[data-testid="stImage"] > img {{ border-radius: 12px !important; }}

    .block-container {{ padding-top: 0rem !important; margin-top: 10px !important; }}
    
    /* --- [SỬA ĐỔI MỚI] STYLE CHO THANH NAVBAR --- */
    .nav-container {{
        padding: 10px 20px; /* Thêm khoảng cách bên trong */
        margin-bottom: 20px;
        background-color: rgba(0, 0, 0, 0.3); /* Lớp nền đen mờ (30%) */
        border-radius: 15px; /* Bo góc cho đẹp */
        backdrop-filter: blur(5px); /* Hiệu ứng làm mờ kính hiện đại */
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); /* Thêm bóng nhẹ */
    }}

    /* --- 1. STYLE CHO NÚT BẤM TRÊN NAVBAR (Menu ngang) --- */
    div[data-testid="stHorizontalBlock"] button {{
        /* background-color: transparent !important; -> Bỏ dòng này để nút ăn theo nền container */
        border: 0px solid transparent !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0px !important;
        
        color: #FFFFFF !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        text-shadow: 0px 2px 5px rgba(0,0,0,0.8);
        transition: all 0.2s ease-in-out;
        text-decoration: none !important;
        padding-left: 5px !important;
        padding-right: 5px !important;
    }}
    
    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #ff7f50 !important; /* Màu cam */
        text-shadow: 0px 0px 10px #ff7f50;
        transform: none !important;
        border-bottom: 3px solid #ff7f50 !important;
    }}

    div[data-testid="stHorizontalBlock"] button:active, 
    div[data-testid="stHorizontalBlock"] button:focus {{
        /* background-color: transparent !important; -> Bỏ dòng này */
        color: #ff7f50 !important;
        border-bottom: 3px solid #ff7f50 !important;
        box-shadow: none !important;
    }}
    
    /* --- 2. STYLE CHO CÁC KHỐI NÚT TRONG MENU SERVICES (Popover) --- */
    div[data-testid="stPopoverBody"] button {{
        border: 2px solid #ff7f50 !important;
        border-radius: 10px !important;
        color: white !important;
        transition: all 0.3s;
        background-color: rgba(0,0,0,0.5) !important;
    }}

    div[data-testid="stPopoverBody"] button:hover {{
        border-color: #ff4500 !important;
        background-color: rgba(255, 127, 80, 0.2) !important;
        color: #ff7f50 !important;
    }}

    /* --- 3. STYLE CHO NÚT PRIMARY --- */
    button[kind="primary"] {{
        background: linear-gradient(90deg, #ff7f50, #ff4500) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(255, 69, 0, 0.4);
    }}

    .nav-logo {{
        font-size: 24px; font-weight: 900; color: #fff; margin: 0; 
        font-family: 'Arial', sans-serif; text-transform: uppercase;
        padding-left: 10px; /* Thêm chút khoảng cách cho logo */
    }}
    </style>
    """, unsafe_allow_html=True)
