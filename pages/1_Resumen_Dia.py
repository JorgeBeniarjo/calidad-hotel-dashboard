import streamlit as st
import pandas as pd

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera, color_puntuacion
from utils.ui_components import date_filter_with_shortcuts
from utils.export import download_excel_button

st.set_page_config(page_title="Resumen del Día", page_icon="📋", layout="wide")
st.title("📋 Resumen del Día")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_personal = get_sheet_data("PERSONAL")

df = preparar_revisiones(df_revisiones_raw) if not df_revisiones_raw.empty else pd.DataFrame()

# Filtro de fecha en sidebar
st.sidebar.header("Filtros")
fecha_inicio, fecha_fin = date_filter_with_shortcuts(key_prefix="resumen", default="hoy")

# Aplicar filtro
if "FECHA" in df.columns and not df.empty:
    mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)
    df_periodo = df[mask].copy()
else:
    df_periodo = pd.DataFrame()

# Etiqueta del período seleccionado
if fecha_inicio == fecha_fin:
    label_periodo = fecha_inicio.strftime("%d/%m/%Y")
else:
    label_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"

# Métricas del período
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total revisiones", len(df_periodo))

with col2:
    if not df_periodo.empty and "PUNTUACION" in df_periodo.columns:
        st.metric("Media puntuación", f"{df_periodo['PUNTUACION'].mean():.2f}")
    else:
        st.metric("Media puntuación", "—")

with col3:
    if not df_periodo.empty and "ESTADO" in df_periodo.columns:
        abiertas = (df_periodo["ESTADO"].str.lower() == "abierta").sum()
        st.metric("Revisiones abiertas", int(abiertas))
    else:
        st.metric("Revisiones abiertas", "—")

st.divider()

if df_periodo.empty:
    st.info(f"No hay revisiones registradas para el período seleccionado ({label_periodo}).")
    st.stop()

# Añadir nombre de camarera
if "ID_PERSONAL" in df_periodo.columns and not df_personal.empty:
    df_periodo["Camarera"] = df_periodo["ID_PERSONAL"].apply(
        lambda x: get_nombre_camarera(x, df_personal)
    )
elif "CAMARERA" in df_periodo.columns:
    df_periodo["Camarera"] = df_periodo["CAMARERA"]
else:
    df_periodo["Camarera"] = "—"

# Tabla de revisiones del período
st.subheader(f"Revisiones del {label_periodo}")

columnas_mostrar = {
    "FECHA": "Fecha",
    "HABITACION": "Habitación",
    "PLANTA": "Planta",
    "TIPOLOGIA": "Tipología",
    "Camarera": "Camarera",
    "PUNTUACION": "Puntuación",
    "ESTADO": "Estado",
}
cols_existentes = [c for c in columnas_mostrar if c in df_periodo.columns]
df_tabla = df_periodo[cols_existentes].rename(columns=columnas_mostrar).copy()

if "Fecha" in df_tabla.columns:
    df_tabla["Fecha"] = df_tabla["Fecha"].dt.strftime("%d/%m/%Y")


def estilo_puntuacion(val):
    color = color_puntuacion(val)
    return f"background-color: {color}; color: white; font-weight: bold; border-radius: 4px;"


if "Puntuación" in df_tabla.columns:
    st.dataframe(
        df_tabla.style.map(estilo_puntuacion, subset=["Puntuación"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

download_excel_button(
    df_tabla,
    f"resumen_{fecha_inicio}_{fecha_fin}.xlsx",
    key="dl_resumen",
    sheet_name="Resumen",
)

st.divider()

# Sección de alertas
st.subheader("⚠️ Alertas — Habitaciones con puntuación crítica (< 6)")

if "PUNTUACION" in df_periodo.columns:
    df_alertas = df_periodo[df_periodo["PUNTUACION"] < 6]
    if df_alertas.empty:
        st.success("No hay habitaciones con puntuación crítica en el período seleccionado.")
    else:
        for _, fila in df_alertas.iterrows():
            hab = fila.get("HABITACION", "—")
            punt = fila.get("PUNTUACION", "—")
            camarera = fila.get("Camarera", "—")
            estado = fila.get("ESTADO", "—")
            st.markdown(
                f"""
                <div style="background-color:#fdecea; border-left: 5px solid #e74c3c;
                            padding: 10px 16px; border-radius: 6px; margin-bottom: 8px;">
                    🚨 <strong>Habitación {hab}</strong> — Puntuación: <strong>{punt}</strong>
                    &nbsp;|&nbsp; Camarera: {camarera} &nbsp;|&nbsp; Estado: {estado}
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    st.info("No se encontró la columna PUNTUACION en los datos.")
