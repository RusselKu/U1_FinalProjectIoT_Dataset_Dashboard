import io
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2 import extras
from psycopg2.extras import Json

try:
    import openaq
except ImportError:
    openaq = None


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


load_dotenv()


OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")
OPENAQ_BASE_URL = os.getenv("OPENAQ_BASE_URL", "https://api.openaq.org/v3")
DB_HOST = os.getenv("DB_HOST", "postgres_db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sensordata")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
EXTRACTION_MODE = os.getenv("EXTRACTION_MODE", "regional").strip().lower()
DEFAULT_LOOKBACK_DAYS = int(os.getenv("OPENAQ_LOOKBACK_DAYS", "7"))

TARGET_REGIONS = {
    "guanajuato": (-101.80, 20.20, -99.50, 21.65),
    "estado_de_mexico": (-100.60, 18.80, -98.80, 20.40),
    "cdmx": (-99.35, 19.00, -98.90, 19.70),
    "queretaro": (-100.70, 20.20, -99.30, 21.50),
    "hidalgo": (-99.90, 19.40, -97.80, 21.80),
}

LEGACY_LOCATION_ID = 17
LEGACY_SENSOR_PARAMETER_MAPPING = {
    12234782: 102,
    12234783: 24,
    12234784: 15,
    14340713: 23,
    12234785: 3,
    399: 1,
    12234787: 2,
    12234789: 101,
}


def get_db_connection():
    """Establece conexion a la BD con reintentos."""
    for attempt in range(5):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            print("✅ Conexión a la base de datos PostgreSQL exitosa.")
            return conn
        except psycopg2.OperationalError as exc:
            print(f"❌ Error al conectar con PostgreSQL (intento {attempt + 1}/5): {exc}")
            time.sleep(5)
    return None


def api_headers():
    return {"X-API-Key": OPENAQ_API_KEY} if OPENAQ_API_KEY else {}


def api_get(path, params=None):
    response = requests.get(f"{OPENAQ_BASE_URL}{path}", headers=api_headers(), params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_utc_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def parse_found_count(raw_found):
    """Convierte meta.found de OpenAQ a entero, soportando casos como '>1000'."""
    if raw_found is None:
        return 0
    if isinstance(raw_found, (int, float)):
        return int(raw_found)
    if isinstance(raw_found, str):
        digits = "".join(ch for ch in raw_found if ch.isdigit())
        return int(digits) if digits else 0
    return 0


def get_latest_timestamp(conn, station_id, parameter_id):
    """Obtiene el timestamp mas reciente para un sensor."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(timestamp_utc) FROM fact_measurements WHERE station_id = %s AND parameter_id = %s;",
            (station_id, parameter_id),
        )
        return cur.fetchone()[0]


def insert_dataframe_to_db(conn, df):
    """Inserta un DataFrame de mediciones en la base de datos."""
    if df.empty:
        print("ℹ️ No hay nuevos datos que insertar.")
        return 0

    tuples = [tuple(x) for x in df.to_numpy()]
    cols = ",".join(list(df.columns))
    insert_query = f"INSERT INTO fact_measurements ({cols}) VALUES %s ON CONFLICT (station_id, parameter_id, timestamp_utc) DO NOTHING;"

    with conn.cursor() as cur:
        try:
            extras.execute_values(cur, insert_query, tuples)
            conn.commit()
            print(f"💾 {cur.rowcount} nuevos registros insertados.")
            return cur.rowcount
        except psycopg2.Error as exc:
            print(f"❌ Error de base de datos durante la inserción: {exc}")
            conn.rollback()
            return 0


def create_etl_run(conn, extraction_mode):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_runs (pipeline_name, extraction_mode, status, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            ("openaq_pipeline", extraction_mode, "running", Json({"source": "OpenAQ", "mode": extraction_mode})),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def log_etl_event(conn, run_id, event_type, status, message, payload=None):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_run_events (run_id, event_type, status, message, payload)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (run_id, event_type, status, message, Json(payload or {})),
        )
    conn.commit()


def finish_etl_run(conn, run_id, status, discovered_locations, inserted_rows, error_message=None):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE etl_runs
            SET status = %s,
                finished_at = CURRENT_TIMESTAMP,
                discovered_locations = %s,
                inserted_rows = %s,
                error_message = %s
            WHERE id = %s;
            """,
            (status, discovered_locations, inserted_rows, error_message, run_id),
        )
    conn.commit()


def ensure_etl_monitor_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS etl_runs (
                id BIGSERIAL PRIMARY KEY,
                pipeline_name VARCHAR(100) NOT NULL,
                extraction_mode VARCHAR(50) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'running',
                started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMPTZ,
                discovered_locations INTEGER NOT NULL DEFAULT 0,
                inserted_rows INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb
            );

            CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON etl_runs (started_at DESC);

            CREATE TABLE IF NOT EXISTS etl_run_events (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT NOT NULL REFERENCES etl_runs(id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                status VARCHAR(30) NOT NULL,
                message TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_etl_run_events_run_id_created_at ON etl_run_events (run_id, created_at DESC);
            """
        )
    conn.commit()


def upsert_station(conn, location):
    country = location.get("country") or {}
    coordinates = location.get("coordinates") or {}
    city = location.get("locality") or location.get("city") or location.get("name")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_stations (id, name, city, country_code, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                city = EXCLUDED.city,
                country_code = EXCLUDED.country_code,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude;
            """,
            (
                location["id"],
                location.get("name"),
                city,
                (country.get("code") or "MX")[:2],
                coordinates.get("latitude"),
                coordinates.get("longitude"),
            ),
        )
    conn.commit()


def upsert_parameter(conn, parameter):
    parameter_name = parameter.get("name")
    display_name = parameter.get("displayName") or parameter.get("display_name") or parameter_name
    units = parameter.get("units")

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM dim_parameters WHERE name = %s;", (parameter_name,))
        existing = cur.fetchone()
        if existing:
            canonical_id = existing[0]
            cur.execute(
                """
                UPDATE dim_parameters
                SET display_name = %s,
                    units = %s
                WHERE id = %s;
                """,
                (display_name, units, canonical_id),
            )
        else:
            canonical_id = parameter["id"]
            cur.execute(
                """
                INSERT INTO dim_parameters (id, name, display_name, units)
                VALUES (%s, %s, %s, %s);
                """,
                (canonical_id, parameter_name, display_name, units),
            )

    conn.commit()
    return canonical_id


def get_api_locations_for_bbox(bbox, country_code="MX", limit=1000):
    page = 1
    locations = []
    while True:
        payload = api_get(
            "/locations",
            params={"bbox": ",".join(map(str, bbox)), "limit": limit, "page": page},
        )
        batch = payload.get("results", [])
        if not batch:
            break

        for location in batch:
            country = location.get("country") or {}
            if country.get("code") == country_code:
                locations.append(location)

        meta = payload.get("meta") or {}
        found_count = parse_found_count(meta.get("found", 0))
        if len(batch) < limit or (found_count and page * limit >= found_count):
            break
        page += 1

    return locations


def discover_locations_by_regions():
    discovered = {}
    for region_name, bbox in TARGET_REGIONS.items():
        try:
            print(f"📍 Descubriendo ubicaciones para {region_name}...")
            for location in get_api_locations_for_bbox(bbox):
                discovered[location["id"]] = location
        except Exception as exc:
            print(f"❌ Error descubriendo ubicaciones en {region_name}: {exc}")
    return list(discovered.values())


def get_measurements_for_sensor(sensor_id, date_from, limit=1000):
    page = 1
    measurements = []
    while True:
        payload = api_get(
            f"/sensors/{sensor_id}/measurements",
            params={"date_from": date_from.isoformat(), "limit": limit, "page": page},
        )
        batch = payload.get("results", [])
        if not batch:
            break

        measurements.extend(batch)

        meta = payload.get("meta") or {}
        found_count = parse_found_count(meta.get("found", 0))
        if len(batch) < limit or (found_count and page * limit >= found_count):
            break
        page += 1

    return measurements


def extract_measurement_timestamp(measurement):
    period = measurement.get("period") or {}
    datetime_from = period.get("datetimeFrom") or period.get("datetime_from") or {}
    if isinstance(datetime_from, dict):
        return parse_utc_datetime(datetime_from.get("utc"))
    return parse_utc_datetime(datetime_from)


def extract_measurement_rows(location, sensor, measurements, latest_ts):
    rows = []
    for measurement in measurements:
        timestamp_utc = extract_measurement_timestamp(measurement)
        if timestamp_utc is None:
            continue
        if latest_ts and timestamp_utc <= latest_ts:
            continue

        parameter = measurement.get("parameter") or sensor.get("parameter") or {}
        rows.append(
            {
                "station_id": location["id"],
                "parameter_id": parameter.get("id"),
                "value": measurement.get("value"),
                "timestamp_utc": timestamp_utc,
            }
        )
    return rows


def run_regional_ingestion(conn):
    print("🚀 Iniciando ingesta por regiones de Mexico...")
    locations = discover_locations_by_regions()
    if not locations:
        print("⚠️ No se encontraron ubicaciones en las regiones objetivo.")
        return 0

    total_inserted = 0
    run_id = create_etl_run(conn, EXTRACTION_MODE)
    log_etl_event(conn, run_id, "discover", "running", f"Se encontraron {len(locations)} ubicaciones en las regiones objetivo.", {"locations": len(locations)})

    for location in locations:
        try:
            upsert_station(conn, location)
            sensors = location.get("sensors") or []
            log_etl_event(conn, run_id, "station", "running", f"Procesando estacion {location.get('name')}", {"station_id": location.get("id"), "sensor_count": len(sensors)})
            print(f"\n--- Procesando estacion {location.get('id')} | {location.get('name')} | sensores: {len(sensors)} ---")

            for sensor in sensors:
                try:
                    parameter = sensor.get("parameter") or {}
                    if not sensor.get("id") or not parameter.get("id"):
                        continue

                    canonical_parameter_id = upsert_parameter(conn, parameter)
                    latest_ts = get_latest_timestamp(conn, location["id"], canonical_parameter_id)
                    date_from = (latest_ts + timedelta(seconds=1)) if latest_ts else (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS))

                    print(
                        f"📡 Consultando sensor {sensor['id']} ({parameter.get('name')}) desde {date_from.strftime('%Y-%m-%d %H:%M:%S %Z')}..."
                    )
                    measurements = get_measurements_for_sensor(sensor["id"], date_from)
                    if not measurements:
                        print("✅ No se encontraron nuevos registros en la API.")
                        log_etl_event(conn, run_id, "sensor", "success", f"Sin nuevos registros para sensor {sensor['id']}", {"sensor_id": sensor["id"], "parameter_id": canonical_parameter_id})
                        continue

                    rows = extract_measurement_rows(location, sensor, measurements, latest_ts)
                    if not rows:
                        print("ℹ️ Las mediciones recibidas ya existian en la base de datos.")
                        log_etl_event(conn, run_id, "sensor", "success", f"Mediciones duplicadas descartadas para sensor {sensor['id']}", {"sensor_id": sensor["id"], "parameter_id": canonical_parameter_id})
                        continue

                    df = pd.DataFrame(rows)
                    df["parameter_id"] = canonical_parameter_id
                    df_to_insert = df[["station_id", "parameter_id", "value", "timestamp_utc"]]
                    total_inserted += insert_dataframe_to_db(conn, df_to_insert)
                    log_etl_event(conn, run_id, "sensor", "success", f"Insertados registros para sensor {sensor['id']}", {"sensor_id": sensor["id"], "parameter_id": canonical_parameter_id, "inserted_rows": len(df_to_insert)})
                except Exception as sensor_exc:
                    log_etl_event(conn, run_id, "sensor", "error", f"Error en sensor {sensor.get('id')}", {"sensor_id": sensor.get("id"), "station_id": location.get("id"), "error": str(sensor_exc)})
                    print(f"⚠️ Error en sensor {sensor.get('id')} de estación {location.get('id')}: {sensor_exc}")
                    continue

        except Exception as exc:
            print(f"❌ Ocurrió un error procesando la estacion {location.get('id')}: {exc}")
            log_etl_event(conn, run_id, "station", "error", f"Error procesando estacion {location.get('id')}", {"station_id": location.get("id"), "error": str(exc)})

    finish_etl_run(conn, run_id, "success", len(locations), total_inserted)
    return total_inserted


def run_legacy_ingestion(conn):
    if openaq is None:
        print("❌ La libreria openaq no esta disponible y el modo legacy requiere esa dependencia.")
        return 0

    print("🚀 Iniciando proceso de ingesta de datos con la libreria oficial de OpenAQ...")
    total_inserted = 0
    run_id = create_etl_run(conn, EXTRACTION_MODE)
    log_etl_event(conn, run_id, "discover", "running", "Se ejecuto el flujo legacy sobre la estacion India.", {"location_id": LEGACY_LOCATION_ID})
    with openaq.OpenAQ(api_key=OPENAQ_API_KEY) as api:
        for sensor_id, parameter_id in LEGACY_SENSOR_PARAMETER_MAPPING.items():
            print(f"\n--- Procesando Sensor ID: {sensor_id} (Parametro: {parameter_id}) ---")

            latest_ts = get_latest_timestamp(conn, LEGACY_LOCATION_ID, parameter_id)
            date_from = (latest_ts + timedelta(seconds=1)) if latest_ts else (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS))

            try:
                print(f"📡 Consultando API para sensor {sensor_id} desde {date_from.strftime('%Y-%m-%d')}...")

                resp = api.measurements.list(
                    sensors_id=sensor_id,
                    datetime_from=date_from,
                    limit=1000,
                )

                if not resp.results:
                    print("✅ No se encontraron nuevos registros en la API.")
                    log_etl_event(conn, run_id, "sensor", "success", f"Sin nuevos registros para sensor {sensor_id}", {"sensor_id": sensor_id, "parameter_id": parameter_id})
                    continue

                rows = []
                for measurement in resp.results:
                    rows.append(
                        {
                            "timestamp_utc": measurement.period.datetime_from.utc,
                            "value": measurement.value,
                        }
                    )

                df = pd.DataFrame(rows)
                df["station_id"] = LEGACY_LOCATION_ID
                df["parameter_id"] = parameter_id

                df_to_insert = df[["station_id", "parameter_id", "value", "timestamp_utc"]]
                total_inserted += insert_dataframe_to_db(conn, df_to_insert)
                log_etl_event(conn, run_id, "sensor", "success", f"Insertados registros para sensor {sensor_id}", {"sensor_id": sensor_id, "parameter_id": parameter_id, "inserted_rows": len(df_to_insert)})

            except Exception as exc:
                print(f"❌ Ocurrio un error procesando el sensor {sensor_id}: {exc}")
                log_etl_event(conn, run_id, "sensor", "error", f"Error procesando sensor {sensor_id}", {"sensor_id": sensor_id, "parameter_id": parameter_id, "error": str(exc)})

    finish_etl_run(conn, run_id, "success", 1, total_inserted)
    return total_inserted


def main():
    conn = get_db_connection()
    if not conn:
        sys.exit(1)

    total_inserted = 0
    try:
        ensure_etl_monitor_schema(conn)
        if EXTRACTION_MODE in {"legacy", "india"}:
            total_inserted = run_legacy_ingestion(conn)
        elif EXTRACTION_MODE in {"regional", "regions", "states", "hybrid"}:
            total_inserted = run_regional_ingestion(conn)
            if total_inserted == 0 and EXTRACTION_MODE == "hybrid":
                print("ℹ️ No hubo carga regional; cambiando a modo legacy como respaldo.")
                total_inserted = run_legacy_ingestion(conn)
        else:
            print(f"⚠️ EXTRACTION_MODE={EXTRACTION_MODE!r} no reconocido. Usando modo regional por defecto.")
            total_inserted = run_regional_ingestion(conn)
    finally:
        if conn:
            conn.close()
            print("\n🔌 Conexion a la base de datos cerrada.")

    print(f"\n✨ Proceso de ingesta finalizado. Total de registros nuevos: {total_inserted}")


if __name__ == "__main__":
    main()