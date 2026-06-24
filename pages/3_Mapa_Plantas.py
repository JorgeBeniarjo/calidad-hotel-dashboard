import streamlit as st
import pandas as pd

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera, color_puntuacion
from utils.ui_components import date_filter_with_shortcuts
from utils.export import download_excel_button

st.set_page_config(page_title="Mapa de Plantas", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa de Plantas")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_habitaciones = get_sheet_data("HABITACIONES")
df_personal = get_sheet_data("PERSONAL")

if df_revisiones_raw.empty or df_habitaciones.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Añadir nombre de camarera
id_col = "ID_PERSONAL" if "ID_PERSONAL" in df.columns else None
if id_col and not df_personal.empty:
    df["Camarera"] = df[id_col].apply(lambda x: get_nombre_camarera(x, df_personal))
elif "CAMARERA" in df.columns:
    df["Camarera"] = df["CAMARERA"]
else:
    df["Camarera"] = "—"

# Filtro de fecha en sidebar
st.sidebar.header("Filtros")
fecha_inicio, fecha_fin = date_filter_with_shortcuts(key_prefix="mapa", default="hoy")

mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)
df_filtrado = df[mask].copy()

label_periodo = (
    fecha_inicio.strftime("%d/%m/%Y")
    if fecha_inicio == fecha_fin
    else f"{fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
)

# Obtener la última puntuación por habitación en el período
cols_agg = ["PUNTUACION", "FECHA", "Camarera"]
cols_agg = [c for c in cols_agg if c in df_filtrado.columns]

if not df_filtrado.empty and "ID_HABITACION" in df_filtrado.columns and "PUNTUACION" in df_filtrado.columns:
    df_filtrado["ID_HABITACION"] = df_filtrado["ID_HABITACION"].astype(str)
    df_ultimas = (
        df_filtrado.sort_values("FECHA")
        .groupby("ID_HABITACION")[cols_agg]
        .last()
        .reset_index()
    )
else:
    df_ultimas = pd.DataFrame(columns=["ID_HABITACION", "PUNTUACION", "FECHA"])

# Claves siempre como string para evitar desajustes de tipo
puntuacion_map = dict(zip(df_ultimas["ID_HABITACION"].astype(str), df_ultimas["PUNTUACION"]))
camarera_map = (
    dict(zip(df_ultimas["ID_HABITACION"].astype(str), df_ultimas["Camarera"]))
    if "Camarera" in df_ultimas.columns
    else {}
)

# Leyenda de colores
st.caption(f"Período: {label_periodo}")
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

# Validación de hoja HABITACIONES
if "PLANTA" not in df_habitaciones.columns or "ID_HABITACION" not in df_habitaciones.columns:
    st.error("La hoja HABITACIONES debe tener columnas PLANTA y ID_HABITACION.")
    st.stop()

def _sort_key(v):
    try:
        return (0, int(v), v)
    except (ValueError, TypeError):
        return (1, 0, v)

plantas = sorted(df_habitaciones["PLANTA"].dropna().astype(str).unique(), key=_sort_key)

# Renderizado por planta
for planta in plantas:
    st.subheader(f"Planta {planta}")
    # Comparar como string en ambos lados para evitar desajustes int/str
    habitaciones_planta = (
        df_habitaciones[df_habitaciones["PLANTA"].astype(str) == planta]["ID_HABITACION"]
        .astype(str)
        .tolist()
    )

    celdas_html = []
    for hab in sorted(habitaciones_planta, key=_sort_key):
        punt = puntuacion_map.get(hab, None)
        cam = camarera_map.get(hab, "")
        if punt is None:
            bg = "#95a5a6"
            texto_punt = "—"
        else:
            bg = color_puntuacion(punt)
            texto_punt = f"{punt:.1f}"

        tooltip = f'title="{cam}"' if cam and cam != "—" else ""
        celda = (
            f'<div {tooltip} style="background:{bg};color:white;border-radius:8px;'
            f'padding:10px 8px;text-align:center;min-width:70px;margin:4px;'
            f'display:inline-block;font-size:13px;font-weight:bold;cursor:default;">'
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

st.divider()

# Export Excel como tabla de estado de habitaciones
if not df_ultimas.empty:
    st.subheader("Exportar estado de habitaciones")

    df_export = df_ultimas.copy()

    # Unir con info de habitaciones
    df_info = df_habitaciones[["ID_HABITACION"] + [c for c in ["PLANTA", "TIPOLOGIA"] if c in df_habitaciones.columns]]
    df_export = df_export.merge(df_info, on="ID_HABITACION", how="left")

    # Formatear y renombrar
    rename_map = {
        "ID_HABITACION": "Habitación",
        "PLANTA": "Planta",
        "TIPOLOGIA": "Tipología",
        "PUNTUACION": "Puntuación",
        "FECHA": "Última revisión",
        "Camarera": "Camarera",
    }
    cols_export = [c for c in rename_map if c in df_export.columns]
    df_export = df_export[cols_export].rename(columns=rename_map)

    if "Última revisión" in df_export.columns:
        df_export["Última revisión"] = pd.to_datetime(df_export["Última revisión"]).dt.strftime("%d/%m/%Y")

    download_excel_button(
        df_export,
        f"mapa_plantas_{fecha_inicio}_{fecha_fin}.xlsx",
        key="dl_mapa",
        sheet_name="Mapa Plantas",
    )
