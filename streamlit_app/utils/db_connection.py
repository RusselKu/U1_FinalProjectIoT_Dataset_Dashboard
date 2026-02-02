import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime

# Cargar variables de entorno desde .env
load_dotenv()

@st.cache_resource
def get_db_connection():
    """
    Obtiene y cachea una conexión a la base de datos PostgreSQL.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password"),
            dbname=os.getenv("DB_NAME", "sensordata"),
            connect_timeout=5
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        return None

def query_data(query, params=None):
    """
    Función genérica para ejecutar consultas y devolver un DataFrame.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"❌ Error ejecutando consulta SQL: {e}")
        return pd.DataFrame()

# --- Funciones para el Dashboard ---

@st.cache_data(ttl=3600)
def get_station_info(station_id=17):
    """Obtiene la información de una estación específica."""
    query = "SELECT id, name, city, country_code, latitude, longitude FROM dim_stations WHERE id = %s;"
    df = query_data(query, (station_id,))
    return df.iloc[0] if not df.empty else None

@st.cache_data(ttl=3600)
def get_available_parameters():
    """Obtiene los parámetros (contaminantes) con datos disponibles."""
    query = """
    SELECT p.id, p.display_name, p.units 
    FROM dim_parameters p
    JOIN fact_measurements fm ON p.id = fm.parameter_id
    GROUP BY p.id, p.display_name, p.units
    ORDER BY p.display_name;
    """
    return query_data(query)

@st.cache_data(ttl=60)
def get_summary_stats(parameter_id, start_date, end_date, station_id=17):
    """Calcula estadísticas y obtiene el último valor para un parámetro y rango de fechas."""
    query = """
    SELECT 
        COUNT(fm.value) as total_records,
        AVG(fm.value) as average_value,
        MIN(fm.value) as min_value,
        MAX(fm.value) as max_value,
        (SELECT value FROM fact_measurements 
         WHERE station_id = %(station_id)s AND parameter_id = %(parameter_id)s 
         ORDER BY timestamp_utc DESC LIMIT 1) as latest_value
    FROM fact_measurements fm
    WHERE 
        fm.station_id = %(station_id)s AND
        fm.parameter_id = %(parameter_id)s AND
        fm.timestamp_utc BETWEEN %(start_date)s AND %(end_date)s;
    """
    params = {"station_id": station_id, "parameter_id": parameter_id, "start_date": start_date, "end_date": end_date}
    df = query_data(query, params)
    return df.iloc[0] if not df.empty else None

@st.cache_data(ttl=60)
def get_enriched_measurements(parameter_id, start_date, end_date, station_id=17):
    """
    Función principal para análisis: Obtiene mediciones y extrae partes de la fecha.
    EXTRACT(ISODOW FROM ...): 1=Lunes, 7=Domingo.
    """
    query = """
    SELECT 
        fm.value,
        fm.timestamp_utc,
        EXTRACT(ISODOW FROM fm.timestamp_utc) as day_of_week, -- 1=Lunes, 7=Domingo
        EXTRACT(HOUR FROM fm.timestamp_utc) as hour_of_day,
        fm.timestamp_utc::date as date_only
    FROM fact_measurements fm
    WHERE 
        fm.station_id = %(station_id)s AND
        fm.parameter_id = %(parameter_id)s AND
        fm.timestamp_utc BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY fm.timestamp_utc ASC;
    """
    params = {"station_id": station_id, "parameter_id": parameter_id, "start_date": start_date, "end_date": end_date}
    return query_data(query, params)