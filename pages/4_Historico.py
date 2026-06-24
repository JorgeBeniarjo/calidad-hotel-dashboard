import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.sheets_connector import get_sheet_data
from utils.data_processing import preparar_revisiones, get_nombre_camarera
from utils.ui_components import date_filter_with_shortcuts
from utils.export import download_excel_button

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

# Panel de filtros en sidebar
st.sidebar.header("Filtros")
fecha_inicio, fecha_fin = date_filter_with_shortcuts(key_prefix="historico", default="30dias")

st.sidebar.markdown("---")

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

label_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
st.caption(f"Período: {label_periodo} · {len(df_f)} revisiones")

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

# Heatmap calidad por planta × día de la semana
if "PLANTA" in df_f.columns:
    st.subheader("Calidad por Planta y Día de la Semana")

    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_map = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
    }
    df_heat = df_f.copy()
    df_heat["DiaSemana"] = df_heat["FECHA"].dt.day_name().map(dia_map)

    pivot = (
        df_heat.groupby(["PLANTA", "DiaSemana"])["PUNTUACION"]
        .mean()
        .unstack()
        .reindex(columns=dias_es)
    )

    if not pivot.empty:
        fig_heat = go.Figure(
            go.Heatmap(
                z=pivot.values,
                x=dias_es,
                y=[str(p) for p in pivot.index],
                colorscale=[
                    [0.0, "#e74c3c"],
                    [0.3, "#f39c12"],
                    [0.6, "#f1c40f"],
                    [1.0, "#27ae60"],
                ],
                zmin=0,
                zmax=10,
                text=[[f"{v:.1f}" if pd.notna(v) else "—" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                hovertemplate="Planta %{y} — %{x}<br>Puntuación media: %{z:.2f}<extra></extra>",
                colorbar=dict(title="Puntuación"),
            )
        )
        fig_heat.update_layout(
            xaxis_title="Día de la semana",
            yaxis_title="Planta",
            margin=dict(l=60, r=20, t=20, b=40),
            height=max(250, len(pivot) * 60),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No hay suficientes datos para generar el heatmap.")

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

download_excel_button(
    df_tabla,
    f"historico_{fecha_inicio}_{fecha_fin}.xlsx",
    key="dl_historico",
    sheet_name="Histórico",
)
