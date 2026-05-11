import pandas as pd


def color_puntuacion(valor) -> str:
    """Devuelve un color hex según la puntuación."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "#95a5a6"  # gris para valores no numéricos
    if v < 6:
        return "#e74c3c"   # rojo
    if v < 8:
        return "#f39c12"   # naranja
    return "#27ae60"        # verde


def preparar_revisiones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y tipifica el DataFrame de revisiones:
    - FECHA → datetime
    - PUNTUACION → numérico
    - Nulos rellenados con valores neutros
    """
    if df.empty:
        return df

    df = df.copy()

    if "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")

    if "PUNTUACION" in df.columns:
        df["PUNTUACION"] = pd.to_numeric(df["PUNTUACION"], errors="coerce")

    # Relleno de nulos por tipo de columna
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("")
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].fillna(0)

    return df


def get_nombre_camarera(id_personal, df_personal: pd.DataFrame) -> str:
    """Devuelve el NOMBRE de una camarera dado su ID_PERSONAL."""
    if df_personal.empty or "ID_PERSONAL" not in df_personal.columns:
        return str(id_personal)
    fila = df_personal[df_personal["ID_PERSONAL"] == id_personal]
    if fila.empty:
        return str(id_personal)
    return str(fila.iloc[0].get("NOMBRE", id_personal))
