import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

st.title("Gordon Lighfoot Email Generator")

st.write('This app generates emails in the style of the lyrics from a :blue[Gordon Lightfoot] song.  It uses simple prompts and an index containing 250+ :blue[Gordon Lightfoot] lyrics.  On the left sidebar you will find links to two pages where you can:')
st.divider()
st.write('1:  Engage in a chat that will help you create the content for your email.')
st.subheader(":red[OR]")
st.write('2:  Copy and paste or write in the contents of your email.')

image = Image.open('../images/gordon.jpg')

with st.container():
 st.image(image, caption='Gordon Lightfoot - Shadows')