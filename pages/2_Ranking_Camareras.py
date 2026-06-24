import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera, color_puntuacion
from utils.ui_components import date_filter_with_shortcuts
from utils.export import download_excel_button

st.set_page_config(page_title="Ranking Camareras", page_icon="🏆", layout="wide")
st.title("🏆 Ranking de Camareras")

# Carga de datos
df_revisiones_raw = get_sheet_data("REVISIONES")
df_personal = get_sheet_data("PERSONAL")

if df_revisiones_raw.empty:
    st.warning("No hay datos disponibles. Comprueba la conexión con Google Sheets.")
    st.stop()

df = preparar_revisiones(df_revisiones_raw)

# Filtro de fecha en sidebar
st.sidebar.header("Filtros")
fecha_inicio, fecha_fin = date_filter_with_shortcuts(key_prefix="ranking", default="30dias")

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

label_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
st.caption(f"Período: {label_periodo}")
st.divider()

# Calcular ranking
repaso_col = None
if "REPASO" in df_filtrado.columns:
    repaso_col = "REPASO"
elif "CON_REPASO" in df_filtrado.columns:
    repaso_col = "CON_REPASO"

ranking = (
    df_filtrado.groupby("Camarera")
    .agg(Media=("PUNTUACION", "mean"), Total=("PUNTUACION", "count"))
    .reset_index()
)
ranking["Media"] = ranking["Media"].round(2)

if repaso_col:
    df_filtrado["_repaso_flag"] = df_filtrado[repaso_col].astype(str).str.lower().isin(
        ["sí", "si", "s", "1", "true", "yes"]
    )
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

download_excel_button(
    ranking,
    f"ranking_camareras_{fecha_inicio}_{fecha_fin}.xlsx",
    key="dl_ranking",
    sheet_name="Ranking",
)

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

st.divider()

# Tendencia individual por camarera
with st.expander("📈 Tendencia individual por camarera"):
    camareras_lista = sorted(df_filtrado["Camarera"].dropna().unique())
    if not camareras_lista:
        st.info("No hay datos de camareras disponibles.")
    else:
        cam_sel = st.selectbox("Seleccionar camarera", camareras_lista, key="tendencia_camarera")
        df_cam = df_filtrado[df_filtrado["Camarera"] == cam_sel].copy()
        df_cam["Fecha"] = df_cam["FECHA"].dt.date

        evolucion_cam = (
            df_cam.groupby("Fecha")["PUNTUACION"]
            .mean()
            .reset_index()
            .rename(columns={"PUNTUACION": "Media"})
        )
        evolucion_cam["Media"] = evolucion_cam["Media"].round(2)

        if evolucion_cam.empty:
            st.info(f"No hay datos para {cam_sel} en el período seleccionado.")
        else:
            fig_tend = px.line(
                evolucion_cam,
                x="Fecha",
                y="Media",
                markers=True,
                title=f"Evolución diaria — {cam_sel}",
                color_discrete_sequence=["#2a73cc"],
                labels={"Media": "Puntuación media", "Fecha": ""},
            )
            fig_tend.update_layout(
                yaxis=dict(range=[0, 10]),
                plot_bgcolor="white",
                margin=dict(l=10, r=10, t=40, b=20),
            )
            st.plotly_chart(fig_tend, use_container_width=True)

            evolucion_cam_export = evolucion_cam.copy()
            evolucion_cam_export["Fecha"] = evolucion_cam_export["Fecha"].astype(str)
            download_excel_button(
                evolucion_cam_export,
                f"tendencia_{cam_sel}_{fecha_inicio}_{fecha_fin}.xlsx",
                key="dl_tendencia",
                sheet_name="Tendencia",
            )
