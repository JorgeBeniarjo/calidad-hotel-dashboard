import streamlit as st
import pandas as pd
from datetime import date

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera, color_puntuacion

st.set_page_config(page_title="Resumen del Día", page_icon="📋", layout="wide")
st.title("📋 Resumen del Día")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_personal = get_sheet_data("PERSONAL")

if df_revisiones_raw.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Filtro por fecha de hoy
hoy = date.today()
df_hoy = df[df["FECHA"].dt.date == hoy].copy() if "FECHA" in df.columns else pd.DataFrame()

# Métricas del día
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total revisiones", len(df_hoy))

with col2:
    if not df_hoy.empty and "PUNTUACION" in df_hoy.columns:
        st.metric("Media puntuación", f"{df_hoy['PUNTUACION'].mean():.2f}")
    else:
        st.metric("Media puntuación", "—")

with col3:
    if not df_hoy.empty and "ESTADO" in df_hoy.columns:
        abiertas = (df_hoy["ESTADO"].str.lower() == "abierta").sum()
        st.metric("Revisiones abiertas", int(abiertas))
    else:
        st.metric("Revisiones abiertas", "—")

st.divider()

if df_hoy.empty:
    st.info(f"No hay revisiones registradas para hoy ({hoy.strftime('%d/%m/%Y')}).")
    st.stop()

# Añadir nombre de camarera si existe la columna ID_PERSONAL
if "ID_PERSONAL" in df_hoy.columns and not df_personal.empty:
    df_hoy["Camarera"] = df_hoy["ID_PERSONAL"].apply(
        lambda x: get_nombre_camarera(x, df_personal)
    )
elif "CAMARERA" in df_hoy.columns:
    df_hoy["Camarera"] = df_hoy["CAMARERA"]
else:
    df_hoy["Camarera"] = "—"

# Tabla de revisiones del día
st.subheader(f"Revisiones del {hoy.strftime('%d/%m/%Y')}")

columnas_mostrar = {
    "HABITACION": "Habitación",
    "PLANTA": "Planta",
    "TIPOLOGIA": "Tipología",
    "Camarera": "Camarera",
    "PUNTUACION": "Puntuación",
    "ESTADO": "Estado",
}
cols_existentes = [c for c in columnas_mostrar if c in df_hoy.columns]
df_tabla = df_hoy[cols_existentes].rename(columns=columnas_mostrar)

# Colorear columna Puntuación mediante estilos
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

st.divider()

# Sección de alertas
st.subheader("⚠️ Alertas — Habitaciones con puntuación crítica (< 6)")

if "PUNTUACION" in df_hoy.columns:
    df_alertas = df_hoy[df_hoy["PUNTUACION"] < 6]
    if df_alertas.empty:
        st.success("No hay habitaciones con puntuación crítica hoy.")
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
