import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera

st.set_page_config(page_title="Histórico", page_icon="📊", layout="wide")
st.title("📊 Histórico de Revisiones")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_personal = get_sheet_data("PERSONAL")

if df_revisiones_raw.empty:
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

# Panel de filtros
st.sidebar.header("Filtros")

hoy = date.today()
fecha_inicio = st.sidebar.date_input("Desde", value=hoy - timedelta(days=90))
fecha_fin = st.sidebar.date_input("Hasta", value=hoy)

camareras_disponibles = sorted(df["Camarera"].dropna().unique().tolist())
camareras_sel = st.sidebar.multiselect("Camarera", options=camareras_disponibles, default=[])

plantas_disponibles = sorted(df["PLANTA"].dropna().unique().tolist()) if "PLANTA" in df.columns else []
plantas_sel = st.sidebar.multiselect("Planta", options=plantas_disponibles, default=[])

estados_disponibles = sorted(df["ESTADO"].dropna().unique().tolist()) if "ESTADO" in df.columns else []
estados_sel = st.sidebar.multiselect("Estado", options=estados_disponibles, default=[])

# Aplicar filtros
if fecha_inicio > fecha_fin:
    st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)
df_f = df[mask].copy()

if camareras_sel:
    df_f = df_f[df_f["Camarera"].isin(camareras_sel)]
if plantas_sel and "PLANTA" in df_f.columns:
    df_f = df_f[df_f["PLANTA"].isin(plantas_sel)]
if estados_sel and "ESTADO" in df_f.columns:
    df_f = df_f[df_f["ESTADO"].isin(estados_sel)]

if df_f.empty:
    st.info("No hay revisiones para los filtros seleccionados.")
    st.stop()

# Gráfico de evolución diaria
st.subheader("Evolución diaria de puntuación media")

evolucion = (
    df_f.groupby(df_f["FECHA"].dt.date)["PUNTUACION"]
    .mean()
    .reset_index()
    .rename(columns={"FECHA": "Fecha", "PUNTUACION": "Media"})
)

fig_linea = px.line(
    evolucion,
    x="Fecha",
    y="Media",
    markers=True,
    labels={"Media": "Puntuación media", "Fecha": ""},
    color_discrete_sequence=["#2a73cc"],
)
fig_linea.update_layout(
    yaxis=dict(range=[0, 10]),
    plot_bgcolor="white",
    margin=dict(l=10, r=10, t=20, b=20),
)
st.plotly_chart(fig_linea, use_container_width=True)

st.divider()

# Histograma de distribución de puntuaciones
st.subheader("Distribución de puntuaciones")

fig_hist = px.histogram(
    df_f,
    x="PUNTUACION",
    nbins=20,
    color_discrete_sequence=["#2a73cc"],
    labels={"PUNTUACION": "Puntuación", "count": "Frecuencia"},
)
fig_hist.update_layout(
    plot_bgcolor="white",
    bargap=0.1,
    margin=dict(l=10, r=10, t=20, b=20),
)
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# Tabla completa filtrada
st.subheader("Tabla de revisiones")

columnas_mostrar = {
    "FECHA": "Fecha",
    "HABITACION": "Habitación",
    "PLANTA": "Planta",
    "TIPOLOGIA": "Tipología",
    "Camarera": "Camarera",
    "PUNTUACION": "Puntuación",
    "ESTADO": "Estado",
    "OBSERVACIONES": "Observaciones",
}
cols_existentes = [c for c in columnas_mostrar if c in df_f.columns]
df_tabla = df_f[cols_existentes].rename(columns=columnas_mostrar).copy()

if "Fecha" in df_tabla.columns:
    df_tabla["Fecha"] = df_tabla["Fecha"].dt.strftime("%d/%m/%Y")

st.dataframe(df_tabla, use_container_width=True, hide_index=True)

# Descarga CSV
csv = df_tabla.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Descargar CSV",
    data=csv,
    file_name=f"revisiones_{fecha_inicio}_{fecha_fin}.csv",
    mime="text/csv",
)
