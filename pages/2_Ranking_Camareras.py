import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera, color_puntuacion

st.set_page_config(page_title="Ranking Camareras", page_icon="🏆", layout="wide")
st.title("🏆 Ranking de Camareras")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_personal = get_sheet_data("PERSONAL")

if df_revisiones_raw.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Selector de rango de fechas
hoy = date.today()
col_f1, col_f2 = st.columns(2)
with col_f1:
    fecha_inicio = st.date_input("Desde", value=hoy - timedelta(days=30))
with col_f2:
    fecha_fin = st.date_input("Hasta", value=hoy)

if fecha_inicio > fecha_fin:
    st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

# Filtro de fechas
mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)
df_filtrado = df[mask].copy()

if df_filtrado.empty:
    st.info("No hay revisiones en el rango de fechas seleccionado.")
    st.stop()

# Añadir nombre de camarera
id_col = "ID_PERSONAL" if "ID_PERSONAL" in df_filtrado.columns else None
if id_col and not df_personal.empty:
    df_filtrado["Camarera"] = df_filtrado[id_col].apply(
        lambda x: get_nombre_camarera(x, df_personal)
    )
elif "CAMARERA" in df_filtrado.columns:
    df_filtrado["Camarera"] = df_filtrado["CAMARERA"]
else:
    df_filtrado["Camarera"] = df_filtrado.get(id_col, pd.Series(["—"] * len(df_filtrado)))

st.divider()

# Calcular ranking
tiene_repaso = "REPASO" in df_filtrado.columns or "CON_REPASO" in df_filtrado.columns
repaso_col = "REPASO" if "REPASO" in df_filtrado.columns else ("CON_REPASO" if "CON_REPASO" in df_filtrado.columns else None)

agg_dict = {"PUNTUACION": ["mean", "count"]}
ranking = df_filtrado.groupby("Camarera").agg(agg_dict).reset_index()
ranking.columns = ["Camarera", "Media", "Total"]
ranking["Media"] = ranking["Media"].round(2)

if repaso_col:
    df_filtrado["_repaso_flag"] = df_filtrado[repaso_col].astype(str).str.lower().isin(["sí", "si", "s", "1", "true", "yes"])
    repasos = df_filtrado.groupby("Camarera")["_repaso_flag"].mean().reset_index()
    repasos.columns = ["Camarera", "PctRepaso"]
    ranking = ranking.merge(repasos, on="Camarera", how="left")
    ranking["% Repaso"] = (ranking["PctRepaso"] * 100).round(1).astype(str) + "%"
    ranking = ranking.drop(columns=["PctRepaso"])

ranking = ranking.sort_values("Media", ascending=False).reset_index(drop=True)
ranking.insert(0, "Posición", ranking.index + 1)

# Tabla ranking
st.subheader("Tabla de Ranking")
st.dataframe(ranking, use_container_width=True, hide_index=True)

st.divider()

# Gráfico de barras horizontales
st.subheader("Media de puntuación por camarera")

colores = [color_puntuacion(v) for v in ranking["Media"]]
fig_barras = go.Figure(go.Bar(
    x=ranking["Media"],
    y=ranking["Camarera"],
    orientation="h",
    marker_color=colores,
    text=ranking["Media"],
    textposition="outside",
))
fig_barras.update_layout(
    xaxis=dict(range=[0, 10], title="Puntuación media"),
    yaxis=dict(title=""),
    height=max(300, len(ranking) * 40),
    plot_bgcolor="white",
    margin=dict(l=10, r=40, t=20, b=20),
)
st.plotly_chart(fig_barras, use_container_width=True)

st.divider()

# Evolución semanal por camarera
st.subheader("Evolución semanal de puntuación")

df_filtrado["Semana"] = df_filtrado["FECHA"].dt.to_period("W").dt.start_time
evolucion = (
    df_filtrado.groupby(["Semana", "Camarera"])["PUNTUACION"]
    .mean()
    .reset_index()
    .rename(columns={"PUNTUACION": "Media"})
)

if evolucion.empty:
    st.info("No hay suficientes datos para mostrar la evolución semanal.")
else:
    fig_linea = px.line(
        evolucion,
        x="Semana",
        y="Media",
        color="Camarera",
        markers=True,
        labels={"Media": "Puntuación media", "Semana": "Semana"},
    )
    fig_linea.update_layout(
        yaxis=dict(range=[0, 10]),
        plot_bgcolor="white",
        legend_title="Camarera",
        margin=dict(l=10, r=10, t=20, b=20),
    )
    st.plotly_chart(fig_linea, use_container_width=True)
