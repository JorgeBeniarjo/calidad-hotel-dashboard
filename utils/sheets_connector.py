import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)
def get_sheet_data(sheet_name: str) -> pd.DataFrame:
    """
    Descarga una hoja del Google Spreadsheet configurado en st.secrets
    y devuelve un DataFrame. Caché de 5 minutos.
    """
    try:
        client = _get_client()
        spreadsheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Hoja '{sheet_name}' no encontrada en el spreadsheet.")
        return pd.DataFrame()
    except Exception as exc:
        st.error(f"Error al conectar con Google Sheets: {exc}")
        return pd.DataFrame()
