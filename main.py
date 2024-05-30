import os
import requests
from dotenv import find_dotenv, load_dotenv
import streamlit as st
from fpdf import FPDF
import tempfile
from groq import Groq
from colorsys import rgb_to_hls, hls_to_rgb

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Configure Pexels API client
PEXELS_API_KEY = st.secrets["pexels_api_key"]
SEARCH_URL = "https://api.pexels.com/v1/search"

# Configure Groq API client
client = Groq(api_key=st.secrets["groq_api_key"])

# Function to query Pexels for image search
def query_image(query):
    params = {
        "query": query,
        "per_page": 3,
        "page": 1,
        "orientation": "landscape",
    }
    response = requests.get(SEARCH_URL, params=params, headers={"Authorization": PEXELS_API_KEY})
    if response.status_code == 200:
        images = response.json().get("photos", [])
        if images:
            return [image["src"]["large"] for image in images[:2]]
        else:
            st.warning("No images found.")
            return []
    else:
        st.error(f"Failed to search for images: {response.status_code} - {response.text}")
        return []

# Function to generate text using Groq
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
        return ""

# Function to calculate text color based on background color
def get_text_color(bg_color):
    h, l, s = rgb_to_hls(bg_color[0] / 255, bg_color[1] / 255, bg_color[2] / 255)
    if l < 0.5:
        return 255, 255, 255  # White text for dark background
    else:
        return 0, 0, 0  # Black text for light background

# Set background color of Streamlit UI to black
st.markdown(
    """
    <style>
    body {
        background-color: #000000;
    }
    </style>
    """,
    unsafe_allow_html=True
)
hide_st_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Sidebar for customization options
st.sidebar.title("Customization Options")
num_paragraphs = st.sidebar.slider("Number of paragraphs", min_value=1, max_value=10, value=3, step=1)
num_images = st.sidebar.slider("Number of images", min_value=0, max_value=5, value=2, step=1)
font_size = st.sidebar.slider("Font size", min_value=8, max_value=24, value=12, step=1)
font_family = st.sidebar.selectbox("Font family", ["Arial", "Times New Roman", "Courier", "Verdana"])

# Main content
st.title("📝 AI Article Generator ✨")
topic = st.text_input("Enter the topic for the article:")

if st.button("Generate Article"):
    with st.spinner("Generating article..."):
        # Generate text using Groq
        prompt = f"Write a short article about {topic} with {num_paragraphs} paragraphs:"
        article_text = generate_text(prompt)

        # Search for relevant images
        image_urls = query_image(topic)

        if article_text:
            pdf_path = "generated_article.pdf"
            pdf = FPDF()
            pdf.add_page()

            # Set background color based on topic
            bg_color = sum(ord(c) for c in topic.lower()) % 256
            pdf.set_fill_color(bg_color, bg_color, bg_color)
            pdf.rect(0, 0, pdf.w, pdf.h, 'F')

            # Set title font color
            text_color = get_text_color((bg_color, bg_color, bg_color))
            pdf.set_text_color(*text_color)
            pdf.set_font(font_family, style="B", size=16)
            pdf.cell(0, 10, txt=topic.upper(), ln=1, align="C")

            # Set body font
            pdf.set_font(font_family, size=font_size)

            # Split the article into paragraphs
            paragraphs = article_text.split("\n\n")

            for i, paragraph in enumerate(paragraphs[:num_paragraphs]):
                pdf.multi_cell(0, font_size * 1.2, txt=paragraph, align="J")

                # Add image after each paragraph
                if i < num_images and i < len(image_urls):
                    response = requests.get(image_urls[i])
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                            temp_file.write(response.content)
                            image_width = pdf.w - 40  # Adjust image width based on page width
                            pdf.image(temp_file.name, x=20, w=image_width)  # Center the image horizontally
                            st.image(image_urls[i], caption=f"Image {i+1}")
                    else:
                        st.warning(f"Failed to download image: {response.status_code} - {response.text}")

                pdf.cell(0, font_size * 1.2, txt="", ln=1)  # Add a blank line after the image or paragraph

            pdf.output(pdf_path)
            st.success("Article generated successfully!")
            st.write(article_text)
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="Download PDF",
                    data=pdf_file,
                    file_name="generated_article.pdf",
                    mime="application/pdf"
                )
