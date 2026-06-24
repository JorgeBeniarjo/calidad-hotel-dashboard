from datetime import date, timedelta

import streamlit as st

_LABELS = ["Hoy", "Esta semana", "Este mes", "Últimos 30 días", "Personalizado"]
_VALORES = ["hoy", "semana", "mes", "30dias", "custom"]
_DEFAULT_IDX = {v: i for i, v in enumerate(_VALORES)}


def date_filter_with_shortcuts(
    key_prefix: str = "",
    default: str = "30dias",
) -> tuple:
    """
    Renderiza un filtro de fechas con atajos rápidos en el sidebar.
    Retorna (start_date, end_date) como objetos date.

    Parámetros:
        key_prefix: prefijo único por página para evitar conflictos de session_state
        default: valor inicial ('hoy', 'semana', 'mes', '30dias', 'custom')
    """
    hoy = date.today()
    radio_key = f"{key_prefix}_shortcut_radio"
    default_idx = _DEFAULT_IDX.get(default, 3)

    seleccion = st.sidebar.radio(
        "Período",
        options=_LABELS,
        index=default_idx,
        key=radio_key,
    )

    periodo = _VALORES[_LABELS.index(seleccion)]

    if periodo == "hoy":
        return hoy, hoy
    elif periodo == "semana":
        lunes = hoy - timedelta(days=hoy.weekday())
        return lunes, hoy
    elif periodo == "mes":
        return hoy.replace(day=1), hoy
    elif periodo == "30dias":
        return hoy - timedelta(days=30), hoy
    else:
        fecha_inicio = st.sidebar.date_input(
            "Desde",
            value=hoy - timedelta(days=30),
            key=f"{key_prefix}_desde",
        )
        fecha_fin = st.sidebar.date_input(
            "Hasta",
            value=hoy,
            key=f"{key_prefix}_hasta",
        )
        if fecha_inicio > fecha_fin:
            st.sidebar.error("La fecha inicio no puede ser posterior al fin.")
        return fecha_inicio, fecha_fin
