import streamlit as st
import requests
from fpdf import FPDF
from urllib.parse import urlparse
import tempfile
from groq import Groq
from colorsys import rgb_to_hls, hls_to_rgb
import base64
import time

PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
SEARCH_URL = "https://api.pexels.com/v1/search"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

@st.cache(ttl=900)  # Cache timeout set to 900 seconds (15 minutes)
def query_image(query):
    params = {
        "query": query,
        "per_page": 3,
        "page": 1,
        "image_type": "photo",
        "size": "large",
        "orientation": "landscape",
        "format": "png"
    }
    response = requests.get(SEARCH_URL, params=params, headers={"Authorization": PEXELS_API_KEY})
    if response.status_code == 200:
        images = response.json()["photos"]
        return [urlparse(image["src"]["large"]).scheme + "://" + urlparse(image["src"]["large"]).netloc + urlparse(image["src"]["large"]).path for image in images[:2]]
    else:
        st.error(f"Failed to search for image: {response.status_code} - {response.text}")
        return None

@st.cache(ttl=900)  # Cache timeout set to 900 seconds (15 minutes)
def generate_text(prompt):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        if hasattr(e, 'response') and e.response:
            error_message = e.response.json()
            st.error(f"Failed to generate text: {error_message}")
        else:
            st.error(f"Failed to generate text: {str(e)}")
        return None

def get_text_color(bg_color):
    h, l, s = rgb_to_hls(bg_color[0] / 255, bg_color[1] / 255, bg_color[2] / 255)
    if l < 0.5:
        return 255, 255, 255  
    else:
        return 0, 0, 0  

def download_pdf(pdf):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        pdf.output(f.name, "F")
        return f.name

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{bin_file}" target="_blank">{file_label}</a>'
    return href

st.markdown(
    """
    <style>
    body {
        background-color: #000000;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)
hide_st_style = """
            <style>
                body {
        background-color: #000000;
        color: #FFFFFF;
    }
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.sidebar.title("Customization Options")
num_paragraphs = st.sidebar.slider("Number of paragraphs", min_value=1, max_value=10, value=3, step=1)
num_images = st.sidebar.slider("Number of images", min_value=0, max_value=5, value=2, step=1)
font_size = st.sidebar.slider("Font size", min_value=8, max_value=24, value=12, step=1)
font_family = st.sidebar.selectbox("Font family", ["Arial", "Times New Roman", "Courier", "Verdana"])

st.title("📝AI Article Generator✨")
topic = st.text_input("Enter the topic for the article:")

# Load last generation time from session state or set default value
last_generation_time = st.session_state.get('last_generation_time', time.time())

if st.button("Generate Article"):
    if time.time() - last_generation_time >= 900:  # Check if 15 minutes have passed
        st.session_state.last_generation_time = time.time()  # Update last generation time

        with st.spinner("Generating article..."):
            
            prompt = f"Write a short article about {topic} with {num_paragraphs} paragraphs:"
            article_text = generate_text(prompt)
            
            image_urls = query_image(topic)

            if article_text and image_urls:
                pdf_path = "generated_article.pdf"
                pdf = FPDF()
                pdf.add_page()

                bg_color = sum(ord(c) for c in topic.lower()) % 256
                pdf.set_fill_color(bg_color, bg_color, bg_color)
                pdf.rect(0, 0, pdf.w, pdf.h, 'F')

                text_color = get_text_color((bg_color, bg_color, bg_color))
                pdf.set_text_color(*text_color)
                pdf.set_font(font_family, style="B", size=16)
                pdf.cell(0, 10, txt=topic.upper
