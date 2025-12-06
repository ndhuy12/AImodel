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

    # Xử lý hình nền
    if bg_source.startswith("#"):
        background_css = f"""
            background-color: {bg_source} !important;
            background-image: none !important;
        """
    elif bg_source.startswith("http"):
        # Lớp phủ đen 50% lên toàn màn hình
        background_css = f"""
            background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url("{bg_source}");
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
    /* 1. SETUP GIAO DIỆN CHUNG */
    .stApp {{ {background_css} }}
    
    h1, h2, h3, h4, p, span, div, label, li {{
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
        font-weight: 500;
    }}
    
    /* Ẩn các thành phần thừa của Streamlit */
    header, [data-testid="stHeader"] {{display: none !important;}}
    .stStatusWidget {{visibility: hidden !important;}}
    .block-container {{ padding-top: 0rem !important; margin-top: 10px !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}

    /* 2. THANH MENU (NAVBAR) TRONG SUỐT */
    .nav-container {{ 
        background-color: transparent !important;
        box-shadow: none !important;
    }}

    /* 3. [FIX QUAN TRỌNG] ĐỔ MÀU KHỐI NỘI DUNG (Manga of the Day) */
    /* Dùng selector cụ thể hơn để Streamlit không thể chối từ */
    div[data-testid="stVerticalBlockBorderWrapper"], 
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: rgba(10, 10, 20, 0.9) !important; /* Màu xanh đen đậm 90% */
        border-color: #ff7f50 !important; /* Viền cam */
        border-radius: 15px !important;
    }}
    
    /* Fix lỗi chữ bị mờ trong khối */
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] h1,
    div[data-testid="stVerticalBlockBorderWrapper"] h2,
    div[data-testid="stVerticalBlockBorderWrapper"] h3 {{
        background-color: transparent !important;
    }}

    /* 4. STYLE ẢNH */
    div[data-testid="stImage"] {{ background-color: transparent !important; }}
    div[data-testid="stImage"] > img {{ border-radius: 12px !important; }}

    /* 5. [FIX LỖI MENU SERVICES] XỬ LÝ NÚT POPOVER RIÊNG */
    /* Nút Services (Popover) thường bị dính style mặc định màu xanh */
    div[data-testid="stPopover"] > button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important; /* Viền ẩn */
        border-radius: 0px !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        box-shadow: none !important; /* Xóa bóng xanh mặc định */
        padding: 0 5px !important;
        margin-top: 2px !important; /* Căn chỉnh cho bằng với các nút khác */
    }}

    /* Hiệu ứng khi di chuột vào Services */
    div[data-testid="stPopover"] > button:hover {{
        color: #ff7f50 !important;
        border-bottom: 3px solid #ff7f50 !important; /* Hiện viền cam */
    }}

    /* 6. CÁC NÚT THƯỜNG (Home, Favorites, Contact) */
    div[data-testid="stHorizontalBlock"] > div > div > div > button {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0px !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        box-shadow: none !important;
        padding: 0 5px !important;
    }}

    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #ff7f50 !important;
        border-bottom: 3px solid #ff7f50 !important;
        text-shadow: 0px 0px 10px #ff7f50;
    }}

    div[data-testid="stHorizontalBlock"] button:focus:not(:active) {{
        border-color: transparent !important;
        color: white !important;
    }}

    /* 7. MENU CON BÊN TRONG SERVICES */
    div[data-testid="stPopoverBody"] button {{
        border: 1px solid #ff7f50 !important;
        border-radius: 8px !important;
        background-color: rgba(0, 0, 0, 0.8) !important;
        color: white !important;
        margin-bottom: 5px !important;
    }}
    div[data-testid="stPopoverBody"] button:hover {{
        background-color: rgba(255, 127, 80, 0.3) !important;
        color: #ff7f50 !important;
    }}

    /* 8. NÚT PRIMARY (Gradient Cam) */
    button[kind="primary"] {{
        background: linear-gradient(90deg, #ff7f50, #ff4500) !important;
        color: white !important; border: none !important;
    }}

    .nav-logo {{ font-size: 24px; font-weight: 900; color: #fff; margin: 0; font-family: 'Arial', sans-serif; text-transform: uppercase; }}
    </style>
    """, unsafe_allow_html=True)
