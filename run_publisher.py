import os
import openaq
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import sys
import io
import time
import pandas as pd

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cargar variables de entorno
load_dotenv()

# --- Configuración ---
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")
DB_HOST = os.getenv("DB_HOST", "postgres_db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sensordata")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

LOCATION_ID = 17
SENSOR_PARAMETER_MAPPING = {
    12234782: 102, 12234783: 24, 12234784: 15, 14340713: 23,
    12234785: 3, 399: 1, 12234787: 2, 12234789: 101
}

# --- Funciones ---

def get_db_connection():
    """Establece conexión a la BD con reintentos."""
    for i in range(5):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASSWORD
            )
            print("✅ Conexión a la base de datos PostgreSQL exitosa.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"❌ Error al conectar con PostgreSQL (intento {i+1}/5): {e}")
            time.sleep(5)
    return None

def get_latest_timestamp(conn, station_id, parameter_id):
    """Obtiene el timestamp más reciente para un sensor."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(timestamp_utc) FROM fact_measurements WHERE station_id = %s AND parameter_id = %s;",
            (station_id, parameter_id)
        )
        return cur.fetchone()[0]

def insert_dataframe_to_db(conn, df):
    """Inserta un DataFrame de mediciones en la base de datos."""
    if df.empty:
        print("ℹ️ No hay nuevos datos que insertar.")
        return 0
    
    tuples = [tuple(x) for x in df.to_numpy()]
    cols = ','.join(list(df.columns))
    insert_query = f"INSERT INTO fact_measurements ({cols}) VALUES %s ON CONFLICT (station_id, parameter_id, timestamp_utc) DO NOTHING;"
    
    with conn.cursor() as cur:
        try:
            extras.execute_values(cur, insert_query, tuples)
            conn.commit()
            print(f"💾 {cur.rowcount} nuevos registros insertados.")
            return cur.rowcount
        except psycopg2.Error as e:
            print(f"❌ Error de base de datos durante la inserción: {e}")
            conn.rollback()
            return 0

# --- Lógica Principal ---

def main():
    """Orquesta la ingesta de datos usando la librería oficial openaq."""
    print("🚀 Iniciando proceso de ingesta de datos con la librería oficial de OpenAQ...")
    conn = get_db_connection()
    if not conn:
        sys.exit(1)

    total_inserted = 0
    try:
        with openaq.OpenAQ(api_key=OPENAQ_API_KEY) as api:
            for sensor_id, parameter_id in SENSOR_PARAMETER_MAPPING.items():
                print(f"\n--- Procesando Sensor ID: {sensor_id} (Parámetro: {parameter_id}) ---")
                
                latest_ts = get_latest_timestamp(conn, LOCATION_ID, parameter_id)
                date_from = (latest_ts + timedelta(seconds=1)) if latest_ts else (datetime.now(timezone.utc) - timedelta(days=7))

                try:
                    print(f"📡 Consultando API para sensor {sensor_id} desde {date_from.strftime('%Y-%m-%d')}...")
                    
                    resp = api.measurements.list(
                        sensors_id=sensor_id,
                        datetime_from=date_from,
                        limit=1000
                    )
                    
                    if not resp.results:
                        print("✅ No se encontraron nuevos registros en la API.")
                        continue

                    rows = []
                    for r in resp.results:
                        # CORRECCIÓN FINAL: Acceder al timestamp correctamente desde r.period.datetime_from.utc
                        rows.append({
                            'timestamp_utc': r.period.datetime_from.utc,
                            'value': r.value,
                        })
                    
                    df = pd.DataFrame(rows)
                    df['station_id'] = LOCATION_ID
                    df['parameter_id'] = parameter_id
                    
                    df_to_insert = df[['station_id', 'parameter_id', 'value', 'timestamp_utc']]

                    total_inserted += insert_dataframe_to_db(conn, df_to_insert)

                except Exception as e:
                    print(f"❌ Ocurrió un error procesando el sensor {sensor_id}: {e}")

    finally:
        if conn:
            conn.close()
            print("\n🔌 Conexión a la base de datos cerrada.")

    print(f"\n✨ Proceso de ingesta finalizado. Total de registros nuevos: {total_inserted}")

if __name__ == "__main__":
    main()