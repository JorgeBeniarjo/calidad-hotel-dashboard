import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones

st.set_page_config(
    page_title="Control de Calidad — Hotel Tres Anclas",
    page_icon="🏨",
    layout="wide",
)

# Logo
logo_path = Path(__file__).parent / "icons" / "logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_column_width=True)

st.title("Control de Calidad — Hotel Tres Anclas")
st.markdown(
    "Panel central de seguimiento de revisiones de habitaciones. "
    "Usa el menú lateral para navegar entre secciones."
)

st.sidebar.title("Navegación")
st.sidebar.page_link("app.py", label="Inicio")
st.sidebar.page_link("pages/1_Resumen_Dia.py", label="Resumen del Día")
st.sidebar.page_link("pages/2_Ranking_Camareras.py", label="Ranking Camareras")
st.sidebar.page_link("pages/3_Mapa_Plantas.py", label="Mapa de Plantas")
st.sidebar.page_link("pages/4_Historico.py", label="Histórico")

# Métricas rápidas
st.subheader("Resumen de hoy")

df_raw = get_sheet_data("REVISIONES")

if df_raw.empty:
    st.warning("No se pudieron cargar datos de revisiones. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_raw)
hoy = pd.Timestamp(date.today())
df_hoy = df[df["FECHA"].dt.date == hoy.date()] if "FECHA" in df.columns else pd.DataFrame()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Revisiones hoy", len(df_hoy))

with col2:
    if not df_hoy.empty and "PUNTUACION" in df_hoy.columns:
        media = df_hoy["PUNTUACION"].mean()
        st.metric("Media hoy", f"{media:.2f}")
    else:
        st.metric("Media hoy", "—")

with col3:
    if not df_hoy.empty and "ESTADO" in df_hoy.columns:
        abiertas = (df_hoy["ESTADO"].str.lower() == "abierta").sum()
        st.metric("Abiertas", int(abiertas))
    else:
        st.metric("Abiertas", "—")

with col4:
    if not df_hoy.empty and "ESTADO" in df_hoy.columns:
        resueltas = (df_hoy["ESTADO"].str.lower() == "resuelta").sum()
        st.metric("Resueltas", int(resueltas))
    else:
        st.metric("Resueltas", "—")
