import os
import pandas as pd
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine, text

# Cargar variables de entorno desde .env
load_dotenv()

@st.cache_resource
def get_db_engine():
    """
    Crea y cachea el engine SQLAlchemy para PostgreSQL.
    """
    try:
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_user = os.getenv("DB_USER", "user")
        db_password = os.getenv("DB_PASSWORD", "password")
        db_name = os.getenv("DB_NAME", "sensordata")

        engine = create_engine(
            f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
            pool_pre_ping=True,
            pool_recycle=300,
        )
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        return None

def query_data(query, params=None):
    """
    Función genérica para ejecutar consultas y devolver un DataFrame.
    """
    engine = get_db_engine()
    if engine is None:
        return pd.DataFrame()
    try:
        with engine.connect() as conn:
            if isinstance(query, str):
                return pd.read_sql_query(text(query), conn, params=params)
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"❌ Error ejecutando consulta SQL: {e}")
        return pd.DataFrame()

# --- Funciones para el Dashboard ---

@st.cache_data(ttl=3600)
def get_available_states():
    """Obtiene los estados/localidades disponibles en dim_stations."""
    query = """
    SELECT DISTINCT city AS state_name
    FROM dim_stations
    WHERE city IS NOT NULL AND TRIM(city) <> ''
    ORDER BY state_name;
    """
    return query_data(query)


@st.cache_data(ttl=300)
def get_stations(state_name=None):
    """Obtiene estaciones, opcionalmente filtradas por estado/localidad."""
    query = """
    SELECT id, name, city, country_code, latitude, longitude
    FROM dim_stations
    WHERE (:state_name IS NULL OR city = :state_name)
    ORDER BY city, name;
    """
    return query_data(query, {"state_name": state_name})

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


@st.cache_data(ttl=300)
def get_measurement_date_bounds():
    """Obtiene el primer y último timestamp disponible en fact_measurements."""
    query = """
    SELECT MIN(timestamp_utc) AS min_timestamp, MAX(timestamp_utc) AS max_timestamp
    FROM fact_measurements;
    """
    df = query_data(query)
    return df.iloc[0] if not df.empty else None

@st.cache_data(ttl=60)
def get_summary_stats(parameter_id, start_date, end_date, station_ids=None):
    """Calcula estadísticas para un parámetro y rango de fechas con filtro por estaciones opcional."""
    station_filter = ""
    if station_ids:
        station_list = ", ".join(str(int(station_id)) for station_id in station_ids)
        station_filter = f" AND fm.station_id IN ({station_list})"
        latest_station_filter = f" AND latest_fm.station_id IN ({station_list})"
    else:
        latest_station_filter = ""

    query = """
    SELECT
        COUNT(fm.value) AS total_records,
        AVG(fm.value) AS average_value,
        MIN(fm.value) AS min_value,
        MAX(fm.value) AS max_value,
        (
            SELECT value
                        FROM fact_measurements latest_fm
                        WHERE parameter_id = :parameter_id
                            AND timestamp_utc BETWEEN :start_date AND :end_date
                        {latest_station_filter}
            ORDER BY timestamp_utc DESC
            LIMIT 1
        ) AS latest_value
    FROM fact_measurements fm
    WHERE fm.parameter_id = :parameter_id
      AND fm.timestamp_utc BETWEEN :start_date AND :end_date
    {station_filter};
        """.format(station_filter=station_filter, latest_station_filter=latest_station_filter)
    params = {
        "parameter_id": parameter_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    df = query_data(query, params)
    return df.iloc[0] if not df.empty else None

@st.cache_data(ttl=60)
def get_enriched_measurements(parameter_id, start_date, end_date, station_ids=None):
    """
    Función principal para análisis: Obtiene mediciones y extrae partes de la fecha.
    EXTRACT(ISODOW FROM ...): 1=Lunes, 7=Domingo.
    """
    station_filter = ""
    if station_ids:
        station_list = ", ".join(str(int(station_id)) for station_id in station_ids)
        station_filter = f" AND fm.station_id IN ({station_list})"

    query = """
    SELECT 
        fm.value,
        fm.timestamp_utc,
        EXTRACT(ISODOW FROM fm.timestamp_utc) as day_of_week, -- 1=Lunes, 7=Domingo
        EXTRACT(HOUR FROM fm.timestamp_utc) as hour_of_day,
        fm.timestamp_utc::date as date_only
    FROM fact_measurements fm
    WHERE
        fm.parameter_id = :parameter_id AND
        fm.timestamp_utc BETWEEN :start_date AND :end_date
    {station_filter}
    ORDER BY fm.timestamp_utc ASC;
    """.format(station_filter=station_filter)
    params = {
        "parameter_id": parameter_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    return query_data(query, params)


@st.cache_data(ttl=30)
def get_recent_etl_runs(limit=20):
    query = """
    SELECT
        id,
        pipeline_name,
        extraction_mode,
        status,
        started_at,
        finished_at,
        discovered_locations,
        inserted_rows,
        error_message
    FROM etl_runs
    ORDER BY started_at DESC
    LIMIT :limit;
    """
    return query_data(query, {"limit": limit})


@st.cache_data(ttl=30)
def get_latest_etl_run():
    query = """
    SELECT
        id,
        pipeline_name,
        extraction_mode,
        status,
        started_at,
        finished_at,
        discovered_locations,
        inserted_rows,
        error_message,
        metadata
    FROM etl_runs
    ORDER BY started_at DESC
    LIMIT 1;
    """
    df = query_data(query)
    return df.iloc[0] if not df.empty else None


@st.cache_data(ttl=30)
def get_etl_run_events(run_id, limit=100):
    query = """
    SELECT
        event_type,
        status,
        message,
        payload,
        created_at
    FROM etl_run_events
    WHERE run_id = :run_id
    ORDER BY created_at ASC
    LIMIT :limit;
    """
    return query_data(query, {"run_id": run_id, "limit": limit})


@st.cache_data(ttl=30)
def get_etl_summary():
    query = """
    SELECT
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'success') AS success_runs,
        COUNT(*) FILTER (WHERE status = 'error') AS error_runs,
        COALESCE(SUM(inserted_rows), 0) AS total_inserted_rows,
        COALESCE(SUM(discovered_locations), 0) AS total_discovered_locations,
        MAX(started_at) AS last_start_at,
        MAX(finished_at) AS last_finish_at
    FROM etl_runs;
    """
    df = query_data(query)
    return df.iloc[0] if not df.empty else None