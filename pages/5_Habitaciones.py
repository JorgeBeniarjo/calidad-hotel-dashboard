import streamlit as st
import pandas as pd
import plotly.express as px

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, color_puntuacion
from utils.ui_components import date_filter_with_shortcuts
from utils.export import download_excel_button

st.set_page_config(page_title="Habitaciones Problemáticas", page_icon="🏠", layout="wide")
st.title("🏠 Habitaciones Problemáticas")
st.markdown(
    "Ranking de habitaciones con peores puntuaciones y mayor número de repasos "
    "en el período seleccionado. Ideal para detectar problemas de mantenimiento."
)

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_habitaciones = get_sheet_data("HABITACIONES")

if df_revisiones_raw.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Filtro de fecha en sidebar
st.sidebar.header("Filtros")
fecha_inicio, fecha_fin = date_filter_with_shortcuts(key_prefix="habitaciones", default="30dias")

mask = (df["FECHA"].dt.date >= fecha_inicio) & (df["FECHA"].dt.date <= fecha_fin)
df_f = df[mask].copy()

if df_f.empty:
    st.info("No hay revisiones para el período seleccionado.")
    st.stop()

# Detectar columna de habitación
hab_col = "ID_HABITACION" if "ID_HABITACION" in df_f.columns else (
    "HABITACION" if "HABITACION" in df_f.columns else None
)
if hab_col is None:
    st.error("No se encontró columna de habitación (ID_HABITACION o HABITACION).")
    st.stop()

# Calcular métricas por habitación
ranking_hab = (
    df_f.groupby(hab_col)
    .agg(
        Puntuación_Media=("PUNTUACION", "mean"),
        Nº_Revisiones=("PUNTUACION", "count"),
    )
    .reset_index()
    .rename(columns={
        hab_col: "Habitación",
        "Puntuación_Media": "Puntuación Media",
        "Nº_Revisiones": "Nº Revisiones",
    })
)
ranking_hab["Puntuación Media"] = ranking_hab["Puntuación Media"].round(2)

# Añadir repasos si existe la columna
repaso_col = None
if "REPASO" in df_f.columns:
    repaso_col = "REPASO"
elif "CON_REPASO" in df_f.columns:
    repaso_col = "CON_REPASO"

if repaso_col:
    df_f["_repaso_flag"] = df_f[repaso_col].astype(str).str.lower().isin(
        ["sí", "si", "s", "1", "true", "yes"]
    )
    repasos = (
        df_f.groupby(hab_col)["_repaso_flag"]
        .agg(n_repasos="sum", pct_repasos="mean")
        .reset_index()
        .rename(columns={hab_col: "Habitación"})
    )
    repasos["n_repasos"] = repasos["n_repasos"].astype(int)
    ranking_hab = ranking_hab.merge(repasos, on="Habitación", how="left")
    ranking_hab["Nº Repasos"] = ranking_hab["n_repasos"].fillna(0).astype(int)
    ranking_hab["% Repasos"] = (ranking_hab["pct_repasos"].fillna(0) * 100).round(1).astype(str) + "%"
    ranking_hab = ranking_hab.drop(columns=["n_repasos", "pct_repasos"])

# Añadir Planta y Tipología
if not df_habitaciones.empty and "ID_HABITACION" in df_habitaciones.columns:
    cols_info = ["ID_HABITACION"] + [c for c in ["PLANTA", "TIPOLOGIA"] if c in df_habitaciones.columns]
    df_info = df_habitaciones[cols_info].rename(columns={"ID_HABITACION": "Habitación"})
    ranking_hab = ranking_hab.merge(df_info, on="Habitación", how="left")
elif "PLANTA" in df_f.columns:
    planta_info = df_f.groupby(hab_col)["PLANTA"].first().reset_index()
    planta_info.columns = ["Habitación", "PLANTA"]
    ranking_hab = ranking_hab.merge(planta_info, on="Habitación", how="left")

# Renombrar y reordenar columnas
ranking_hab = ranking_hab.rename(columns={"PLANTA": "Planta", "TIPOLOGIA": "Tipología"})
cols_orden = ["Habitación"]
for c in ["Planta", "Tipología", "Puntuación Media", "Nº Revisiones", "Nº Repasos", "% Repasos"]:
    if c in ranking_hab.columns:
        cols_orden.append(c)
ranking_hab = ranking_hab[cols_orden]

# Ordenar por peor puntuación (ascendente)
ranking_hab = ranking_hab.sort_values("Puntuación Media", ascending=True).reset_index(drop=True)

# Información del período
label_periodo = (
    fecha_inicio.strftime("%d/%m/%Y")
    if fecha_inicio == fecha_fin
    else f"{fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
)
st.caption(f"Período: {label_periodo} · {len(ranking_hab)} habitaciones con revisiones")

# Métricas resumen
col1, col2, col3 = st.columns(3)
with col1:
    criticas = int((ranking_hab["Puntuación Media"] < 6).sum())
    st.metric("Habitaciones críticas (< 6)", criticas)
with col2:
    st.metric("Puntuación media global", f"{ranking_hab['Puntuación Media'].mean():.2f}")
with col3:
    if "Nº Repasos" in ranking_hab.columns:
        st.metric("Total repasos", int(ranking_hab["Nº Repasos"].sum()))

st.divider()

# Tabla con coloración de puntuación
st.subheader("Ranking de habitaciones (peores primero)")


def estilo_puntuacion(val):
    color = color_puntuacion(val)
    return f"background-color: {color}; color: white; font-weight: bold;"


if "Puntuación Media" in ranking_hab.columns:
    st.dataframe(
        ranking_hab.style.map(estilo_puntuacion, subset=["Puntuación Media"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.dataframe(ranking_hab, use_container_width=True, hide_index=True)

download_excel_button(
    ranking_hab,
    f"habitaciones_{fecha_inicio}_{fecha_fin}.xlsx",
    key="dl_habitaciones",
    sheet_name="Habitaciones",
)

st.divider()

# Gráfico de barras: Top 10 peores habitaciones
st.subheader("Top 10 habitaciones con peor puntuación")

top10 = ranking_hab.head(10).copy()
if not top10.empty:
    colores_top = [color_puntuacion(v) for v in top10["Puntuación Media"]]
    fig_top = px.bar(
        top10,
        x="Habitación",
        y="Puntuación Media",
        color="Puntuación Media",
        color_continuous_scale=[[0, "#e74c3c"], [0.4, "#f39c12"], [0.7, "#f1c40f"], [1.0, "#27ae60"]],
        range_color=[0, 10],
        text="Puntuación Media",
        labels={"Puntuación Media": "Puntuación media"},
    )
    fig_top.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_top.update_layout(
        yaxis=dict(range=[0, 10]),
        plot_bgcolor="white",
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=40),
    )
    st.plotly_chart(fig_top, use_container_width=True)
