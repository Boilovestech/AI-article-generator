import streamlit as st
import requests
from fpdf import FPDF
from urllib.parse import urlparse
import tempfile
from groq import Groq
from colorsys import rgb_to_hls
import base64

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
        return [image["src"]["large"] for image in images[:2]]
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
        st.error(f"Failed to generate text: {str(e)}")
        return None

def get_text_color(bg_color):
    h, l, s = rgb_to_hls(bg_color[0] / 255, bg_color[1] / 255, bg_color[2] / 255)
    if l < 0.5:
        return 255, 255, 255  
    else:
        return 0, 0, 0  

def download_pdf(pdf):
    if pdf is None:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        pdf.output(f.name, "F")
        return f.name

def get_binary_file_downloader_html(bin_file, file_label='Download PDF'):
    if bin_file is None:
        return ''
    with open(bin_file, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{bin_file}" target="_blank">{file_label}</a>'
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

st.sidebar.title("Customization Options")
num_paragraphs = st.sidebar.slider("Number of paragraphs", min_value=1, max_value=10, value=3, step=1)
num_images = st.sidebar.slider("Number of images", min_value=0, max_value=5, value=2, step=1)
font_size = st.sidebar.slider("Font size", min_value=8, max_value=24, value=12, step=1)
font_family = st.sidebar.selectbox("Font family", ["Arial", "Times New Roman", "Courier", "Verdana"])

st.title("📝AI Article Generator✨")
topic = st.text_input("Enter the topic for the article:")

if st.button("Generate Article"):
    with st.spinner("Generating article..."):
        prompt = f"Write a short article about {topic} with {num_paragraphs} paragraphs:"
        article_text = generate_text(prompt)
        image_urls = query_image(topic)

        if article_text and image_urls:
            pdf = FPDF()
            pdf.add_page()

            bg_color = sum(ord(c) for c in topic.lower()) % 256
            pdf.set_fill_color(bg_color, bg_color, bg_color)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(font_family, style="B", size=16)
            pdf.cell(200, 10, txt=topic.upper(), ln=True, align="C")

            pdf.set_font(font_family, size=font_size)

            paragraphs = article_text.split("\n\n")

            for paragraph in paragraphs[:num_paragraphs]:
                pdf.multi_cell(0, 10, txt=paragraph, align="J")

            for img_url in image_urls[:num_images]:
                response = requests.get(img_url)
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                        temp_file.write(response.content)
                        pdf.image(temp_file.name, w=150)
                else:
                    st.warning(f"Failed to fetch image: {img_url}")

            pdf_file = download_pdf(pdf)
            st.success("Article generated successfully!")

            st.subheader("Generated Text:")
            st.write(article_text)

            st.subheader("Used Images:")
            for img_url in image_urls[:num_images]:
                st.image(img_url, caption="Used Image")

            st.markdown(get_binary_file_downloader_html(pdf_file), unsafe_allow_html=True)
        else:
            st.error("Failed to generate article. Please try again later.")
