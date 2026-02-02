
---

## 1. Infraestructura de Datos: Esquema Relacional Robusto

Para cumplir con la rúbrica sobre **Modelado de Entidades y Relaciones**, se implementará un esquema que soporte series de tiempo eficientes en PostgreSQL.

### Definición de Datos (DDL Avanzado)

```sql
-- 1. Catálogo de Parámetros (Basado en /v3/parameters de OpenAQ)
CREATE TABLE dim_parameters (
    id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL, -- e.g., 'pm25', 'pm10', 'no2'
    display_name VARCHAR(100),
    units VARCHAR(20)
);

-- 2. Registro de Estaciones (Basado en /v3/locations de OpenAQ)
CREATE TABLE dim_stations (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    country_code CHAR(2),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    first_updated TIMESTAMPTZ,
    last_updated TIMESTAMPTZ
);

-- 3. Tabla de Hechos: Mediciones (Optimizada para JOINs y consultas de Dashboard)
CREATE TABLE fact_measurements (
    id BIGSERIAL PRIMARY KEY,
    station_id INT REFERENCES dim_stations(id),
    parameter_id INT REFERENCES dim_parameters(id),
    value FLOAT NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    [cite_start]-- Restricción para evitar duplicados en la ingesta incremental [cite: 142]
    CONSTRAINT unique_measurement UNIQUE(station_id, parameter_id, timestamp_utc)
);

[cite_start]-- Índice para acelerar los gráficos de series de tiempo del Dashboard [cite: 144]
CREATE INDEX idx_measurements_time ON fact_measurements (timestamp_utc DESC);

```

---

## 2. Motor de Ingesta (ETL Python): Especificaciones de la API v3

El script de ingesta debe automatizar el flujo desde el JSON de OpenAQ hacia las tablas anteriores.

### Detalles de la API y Mapeo

* **Endpoint Principal:** `GET https://api.openaq.org/v3/locations/{id}/measurements`.
* **Headers:** Requiere `X-API-Key`.
* **Parámetros de Consulta:** Usar `limit=1000` y `date_from` (ISO 8601) para capturar solo datos nuevos.

### Lógica de Transformación "On-the-fly"

1. **Parsing de JSON:** El campo `results` de la API contiene objetos anidados. Debes extraer:
* `parameter.id`  `parameter_id` en DB.
* `period.datetime_from.utc`  `timestamp_utc` (convertir a objeto `datetime` con zona horaria).
* `value`  `value` (tipo float).


2. **Control de Calidad (Validation):**
* 
**Filtro de Rangos:** Si el valor es  (error de sensor) o  (outlier/saturación), debe marcarse o descartarse para no sesgar el promedio.


* 
**Detección de NAs:** Si el campo `value` es nulo, registrar la fila pero con una bandera de error para el análisis de "Missingness" requerido.





---

## 3. Visualización y Acceso a Datos (Streamlit)

El dashboard no leerá archivos CSV; consultará la base de datos mediante **SQL dinámico**.

Consultas Requeridas para los Gráficos 

* **Para el Gráfico de Líneas (Series Behavior):**
```sql
SELECT timestamp_utc, value, p.name 
FROM fact_measurements m
JOIN dim_parameters p ON m.parameter_id = p.id
WHERE m.station_id = :selected_id
ORDER BY timestamp_utc ASC;

```


* 
**Para el Análisis de Calidad (Missingness):** Realizar un `COUNT` agrupado por día para comparar los registros esperados (24 por parámetro) vs los reales en la DB.



### Componentes de la Interfaz

1. **Sidebar:** Filtros de fecha (`st.date_input`) y selección de contaminante.
2. **Métricas Clave:** `st.metric` mostrando el último valor de PM2.5 y su tendencia (delta) respecto a la hora anterior.
3. **Mapa:** `st.pydeck_chart` usando las coordenadas de `dim_stations`.

---

## 4. Perspectiva de Ingeniería de Datos (Para el Reporte LaTeX)

Para obtener el puntaje máximo en la sección de "Data Engineering Perspective", el plan contempla discutir:

* 
**Volumen:** Análisis de cuántos registros genera una sola estación al mes ( filas por parámetro).


* 
**Velocidad:** Definir la frecuencia de ingesta (ej. cada hora) para simular un entorno de monitoreo real.


* 
**Variedad:** Integración de datos de contaminantes (gases/partículas) con metadatos de ubicación.


* 
**Estrategia de Almacenamiento:** Justificar el uso de índices y llaves foráneas para mantener la integridad referencial en un flujo de datos IoT.



---
