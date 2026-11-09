"""Protótipo: a enchente de maio/2024 em mapa navegável. Rode: streamlit run app/app.py"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Guaíba em maio de 2024", layout="wide")
st.markdown("""<style>
header, footer, .stAppToolbar { display: none !important; }
.stMainBlockContainer, .block-container { padding: 0 !important; max-width: 100% !important; }
.stAppViewContainer, .stMain { overflow: hidden !important; }
.stVerticalBlock { gap: 0 !important; }
iframe[title="Mapa da enchente de maio de 2024"] { height: 100dvh !important; display: block; }
</style>""", unsafe_allow_html=True)
st.iframe(Path(__file__).parent / "mapa.html", height=900, alt="Mapa da enchente de maio de 2024")
