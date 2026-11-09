"""Dashboard em duas telas: simulação do INCT e enchente de 2024."""
from pathlib import Path

import streamlit as st

from telas import tela_historico, tela_inct


st.set_page_config(page_title="Guaíba em Porto Alegre", layout="wide", initial_sidebar_state="collapsed")

tela = st.query_params.get("tela", "enchente")
painel = st.query_params.get("painel", "")
if tela == "inct":
    painel = ""
mapa_aberto = tela != "inct" and painel != "historico"

st.markdown("""<style>
header, footer, .stAppToolbar { display: none !important; }
.stApp { background: #17313a; color: #eef2f0; }
.stMainBlockContainer, .block-container { max-width: 100% !important; }
.stMainBlockContainer { padding: 82px 3vw 36px !important; }
.site-nav { position: fixed; z-index: 999999; top: 12px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 4px; padding: 4px; border: 1px solid #34525b;
  border-radius: 7px; background: rgba(23,49,58,.96); box-shadow: 0 3px 16px rgba(0,0,0,.35);
  font: 500 13px Arial, sans-serif; white-space: nowrap; }
.site-nav a { color: #eef2f0; text-decoration: none; padding: 7px 11px; border-radius: 4px; }
.site-nav a:hover, .site-nav a.active { color: #17313a; background: #f2c94c; }
.site-nav .secondary { border-left: 1px solid #34525b; margin-left: 3px; border-radius: 0; }
iframe[title="Mapa da enchente de maio de 2024"] { height: 100dvh !important; display: block; }
@media (max-width: 640px) {
  .site-nav { top: 148px; left: auto; right: 8px; transform: none; font-size: 11px; }
  .site-nav a { padding: 5px 7px; }
  .stMainBlockContainer { padding: 70px 14px 24px !important; }
}
</style>""", unsafe_allow_html=True)

if mapa_aberto:
    st.markdown("""<style>
    .stMainBlockContainer, .block-container { padding: 0 !important; }
    .stAppViewContainer, .stMain { overflow: hidden !important; }
    .stVerticalBlock { gap: 0 !important; }
    </style>""", unsafe_allow_html=True)

link_inct = "active" if tela == "inct" else ""
link_mapa = "active" if mapa_aberto else ""
link_historico = "secondary active" if painel == "historico" else "secondary"
st.markdown(f"""<nav class="site-nav" aria-label="Telas do dashboard">
  <a class="{link_inct}" href="?tela=inct" target="_self">Simulação INCT</a>
  <a class="{link_mapa}" href="?tela=enchente" target="_self">Enchente 2024</a>
  <a class="{link_historico}" href="?tela=enchente&amp;painel=historico" target="_self">Histórico</a>
</nav>""", unsafe_allow_html=True)

if tela == "inct":
    tela_inct()
elif painel == "historico":
    tela_historico()
else:
    st.iframe(Path(__file__).parent / "mapa.html", height=900, alt="Mapa da enchente de maio de 2024")
