-- Esquema Relacional Robusto para Series de Tiempo de Calidad del Aire

-- 1. Catálogo de Parámetros (Basado en /v3/parameters de OpenAQ)
-- Almacena información sobre cada tipo de contaminante que medimos.
CREATE TABLE IF NOT EXISTS dim_parameters (
    id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'pm25', 'pm10', 'no2'
    display_name VARCHAR(100),
    units VARCHAR(20)
);

-- 2. Registro de Estaciones (Basado en /v3/locations de OpenAQ)
-- Almacena metadatos de cada estación de monitoreo.
CREATE TABLE IF NOT EXISTS dim_stations (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    country_code CHAR(2),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

-- 3. Tabla de Hechos: Mediciones
-- Tabla principal que almacena cada medición individual. Optimizada para inserciones rápidas y consultas de series de tiempo.
CREATE TABLE IF NOT EXISTS fact_measurements (
    id BIGSERIAL PRIMARY KEY,
    station_id INT REFERENCES dim_stations(id),
    parameter_id INT REFERENCES dim_parameters(id),
    value FLOAT NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    -- Restricción para evitar duplicados en la ingesta incremental
    CONSTRAINT unique_measurement UNIQUE(station_id, parameter_id, timestamp_utc)
);

-- Índice para acelerar los gráficos de series de tiempo del Dashboard
CREATE INDEX IF NOT EXISTS idx_measurements_time ON fact_measurements (timestamp_utc DESC);

-- --- PRE-POBLACIÓN DE DATOS DIMENSIONALES ---

-- Insertar los parámetros que vamos a utilizar de la estación R K Puram, Delhi - DPCC
-- Asegura la integridad referencial para la llave foránea en fact_measurements.
INSERT INTO dim_parameters (id, name, display_name, units) VALUES
(102, 'co', 'CO', 'ppb'),
(24, 'no', 'NO', 'ppb'),
(15, 'no2', 'NO₂', 'ppb'),
(23, 'nox', 'NOx', 'ppb'),
(3, 'o3', 'O₃', 'µg/m³'), -- Nota: el usuario solicitó ppm, pero el sensor disponible reporta en µg/m³
(1, 'pm10', 'PM10', 'µg/m³'),
(2, 'pm25', 'PM2.5', 'µg/m³'),
(101, 'so2', 'SO₂', 'ppb')
ON CONFLICT (id) DO NOTHING;

-- Insertar la estación que vamos a monitorear
-- También por integridad referencial.
INSERT INTO dim_stations (id, name, city, country_code, latitude, longitude) VALUES
(17, 'R K Puram, Delhi - DPCC', 'Delhi', 'IN', 28.563262, 77.186937)
ON CONFLICT (id) DO NOTHING;

-- Mensaje final de éxito
SELECT '✅ Esquema de base de datos creado y poblado exitosamente.' as status;
