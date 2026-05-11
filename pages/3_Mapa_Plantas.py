import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, color_puntuacion

st.set_page_config(page_title="Mapa de Plantas", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa de Plantas")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_habitaciones = get_sheet_data("HABITACIONES")

if df_revisiones_raw.empty or df_habitaciones.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Selector de fecha o rango
modo = st.radio("Modo de filtro", ["Fecha única", "Rango de fechas"], horizontal=True)
hoy = date.today()

if modo == "Fecha única":
    fecha_sel = st.date_input("Fecha", value=hoy)
    mask = df["FECHA"].dt.date == fecha_sel
else:
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde", value=hoy - timedelta(days=7))
    with col2:
        fecha_fin = st.date_input("Hasta", value=hoy)
    mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)

df_filtrado = df[mask].copy()

# Obtener la última puntuación por habitación
if not df_filtrado.empty and "ID_HABITACION" in df_filtrado.columns and "PUNTUACION" in df_filtrado.columns:
    df_ultimas = (
        df_filtrado.sort_values("FECHA")
        .groupby("ID_HABITACION")[["PUNTUACION", "FECHA"]]
        .last()
        .reset_index()
    )
else:
    df_ultimas = pd.DataFrame(columns=["ID_HABITACION", "PUNTUACION", "FECHA"])

# Mapa de puntuaciones por habitación
puntuacion_map = dict(zip(df_ultimas["ID_HABITACION"], df_ultimas["PUNTUACION"]))

# Leyenda
st.divider()
col_r, col_n, col_v, col_g = st.columns(4)
with col_r:
    st.markdown('<span style="background:#e74c3c;color:white;padding:4px 10px;border-radius:4px;">Crítica (&lt;6)</span>', unsafe_allow_html=True)
with col_n:
    st.markdown('<span style="background:#f39c12;color:white;padding:4px 10px;border-radius:4px;">Mejorable (6–7.9)</span>', unsafe_allow_html=True)
with col_v:
    st.markdown('<span style="background:#27ae60;color:white;padding:4px 10px;border-radius:4px;">Buena (≥8)</span>', unsafe_allow_html=True)
with col_g:
    st.markdown('<span style="background:#95a5a6;color:white;padding:4px 10px;border-radius:4px;">Sin revisión</span>', unsafe_allow_html=True)

st.divider()

# Renderizado por planta
if "PLANTA" not in df_habitaciones.columns or "ID_HABITACION" not in df_habitaciones.columns:
    st.error("La hoja HABITACIONES debe tener columnas PLANTA y ID_HABITACION.")
    st.stop()

plantas = sorted(df_habitaciones["PLANTA"].dropna().unique())

for planta in plantas:
    st.subheader(f"Planta {planta}")
    habitaciones_planta = df_habitaciones[df_habitaciones["PLANTA"] == planta]["ID_HABITACION"].tolist()

    celdas_html = []
    for hab in sorted(habitaciones_planta):
        punt = puntuacion_map.get(hab, None)
        if punt is None:
            bg = "#95a5a6"
            texto_punt = "—"
        else:
            bg = color_puntuacion(punt)
            texto_punt = f"{punt:.1f}"

        celda = (
            f'<div style="background:{bg};color:white;border-radius:8px;'
            f'padding:10px 8px;text-align:center;min-width:70px;margin:4px;'
            f'display:inline-block;font-size:13px;font-weight:bold;">'
            f'<div style="font-size:15px;">{hab}</div>'
            f'<div style="opacity:0.9;">{texto_punt}</div>'
            f'</div>'
        )
        celdas_html.append(celda)

    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;gap:2px;">' + "".join(celdas_html) + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")
