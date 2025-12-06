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
    .nav-container {{ padding: 0; margin-bottom: 20px; }}

    /* --- STYLE CHO NÚT BẤM TRÊN NAVBAR --- */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        text-shadow: 0px 2px 5px rgba(0,0,0,0.8);
        transition: all 0.3s ease;
        text-decoration: none; /* Mặc định không gạch chân */
    }}
    
    /* Hiệu ứng khi di chuột (Hover) */
    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #00D4FF !important;
        text-shadow: 0px 0px 10px #00D4FF;
        
        /* Thay đổi ở đây: Tắt scale, Bật underline */
        transform: none !important; 
        text-decoration: underline !important;
        text-underline-offset: 8px !important; /* Khoảng cách giữa chữ và gạch chân */
        text-decoration-thickness: 3px !important; /* Độ dày nét gạch */
    }}

    .nav-logo {{
        font-size: 24px; font-weight: 900; color: #fff; margin: 0; 
        font-family: 'Arial', sans-serif; text-transform: uppercase;
    }}
    
    button[kind="primary"] {{
        background: linear-gradient(90deg, #00D4FF, #005Bea) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
    }}
    </style>
    """, unsafe_allow_html=True)
