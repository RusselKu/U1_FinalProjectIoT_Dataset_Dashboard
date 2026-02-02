# Diseño y Modelo Detallado de la Base de Datos

Este documento describe el esquema de la base de datos PostgreSQL utilizada en el proyecto, su diseño y las relaciones entre sus entidades. El objetivo es proporcionar una visión completa del modelo de datos para fines de documentación y comprensión.

---

## 1. Introducción al Modelo de Datos

La base de datos utiliza un **modelo dimensional** o "esquema estrella", que es ideal para aplicaciones de análisis y dashboards. Este modelo separa los datos en dos tipos principales de tablas:
*   **Tablas de Dimensión (`dim_`)**: Contienen información descriptiva y contextual (el "qué", "quién", "dónde").
*   **Tablas de Hechos (`fact_`)**: Contienen las mediciones o eventos centrales (el "cuánto", "cuándo").

Este diseño facilita las consultas analíticas rápidas y la comprensión del negocio.

---

## 2. Diagrama de Relación (Representación Textual)

A continuación, se presenta una representación textual simplificada de las relaciones entre las tablas:

```
+----------------+       +-------------------------+       +------------------+
|  dim_stations  | <---- |    fact_measurements    | ----> |  dim_parameters  |
|----------------|       |-------------------------|       |------------------|
| id (PK)        |       | id (PK)                 |       | id (PK)          |
| name           |       | station_id (FK)         |       | name             |
| city           |       | parameter_id (FK)       |       | display_name     |
| country_code   |       | value                   |       | units            |
| latitude       |       | timestamp_utc           |       |                  |
| longitude      |       |                         |       |                  |
+----------------+       +-------------------------+       +------------------+

```
**Explicación de las relaciones:**
*   `fact_measurements.station_id` es una Clave Foránea (`FK`) que referencia a `dim_stations.id`.
*   `fact_measurements.parameter_id` es una Clave Foránea (`FK`) que referencia a `dim_parameters.id`.

---

## 3. Descripción Detallada de las Tablas

### 3.1. `dim_stations` (Tabla de Dimensión: Estaciones de Monitoreo)

Esta tabla almacena los metadatos de las estaciones de monitoreo de calidad del aire.

| Nombre de la Columna | Tipo de Dato       | Descripción                                      | Restricciones / Índices       |
| :------------------- | :----------------- | :----------------------------------------------- | :---------------------------- |
| `id`                 | `INTEGER`          | Clave primaria de la estación.                   | `PRIMARY KEY`, `NOT NULL`     |
| `name`               | `VARCHAR(255)`     | Nombre oficial de la estación.                   | `NOT NULL`                    |
| `city`               | `VARCHAR(255)`     | Ciudad donde se ubica la estación.               | `NOT NULL`                    |
| `country_code`       | `VARCHAR(10)`      | Código ISO del país (ej. "IN" para India).       | `NOT NULL`                    |
| `latitude`           | `DOUBLE PRECISION` | Latitud geográfica de la estación.               | `NOT NULL`                    |
| `longitude`          | `DOUBLE PRECISION` | Longitud geográfica de la estación.              | `NOT NULL`                    |

### 3.2. `dim_parameters` (Tabla de Dimensión: Parámetros/Contaminantes)

Esta tabla almacena los metadatos de los diferentes parámetros (contaminantes) medidos.

| Nombre de la Columna | Tipo de Dato       | Descripción                                      | Restricciones / Índices       |
| :------------------- | :----------------- | :----------------------------------------------- | :---------------------------- |
| `id`                 | `INTEGER`          | Clave primaria del parámetro.                    | `PRIMARY KEY`, `NOT NULL`     |
| `name`               | `VARCHAR(50)`      | Nombre técnico del parámetro (ej. "pm25").       | `NOT NULL`, `UNIQUE`          |
| `display_name`       | `VARCHAR(255)`     | Nombre legible para mostrar (ej. "PM2.5").       | `NOT NULL`                    |
| `units`              | `VARCHAR(50)`      | Unidades de medida (ej. "µg/m³", "ppb").         | `NOT NULL`                    |

### 3.3. `fact_measurements` (Tabla de Hechos: Mediciones de Calidad del Aire)

Esta es la tabla central que almacena cada medición individual de calidad del aire.

| Nombre de la Columna | Tipo de Dato        | Descripción                                      | Restricciones / Índices                         |
| :------------------- | :------------------ | :----------------------------------------------- | :---------------------------------------------- |
| `id`                 | `SERIAL`            | Clave primaria auto-incremental de la medición.  | `PRIMARY KEY`, `NOT NULL`                       |
| `station_id`         | `INTEGER`           | ID de la estación donde se realizó la medición.  | `NOT NULL`, `FOREIGN KEY (dim_stations.id)`   |
| `parameter_id`       | `INTEGER`           | ID del parámetro medido.                         | `NOT NULL`, `FOREIGN KEY (dim_parameters.id)` |
| `value`              | `DOUBLE PRECISION`  | Valor numérico de la medición.                   | `NOT NULL`                                      |
| `timestamp_utc`      | `TIMESTAMP WITH TIME ZONE` | Fecha y hora de la medición en UTC.              | `NOT NULL`                                      |
| `UNIQUE (station_id, parameter_id, timestamp_utc)` | | Impide duplicados para la misma estación, parámetro y tiempo. | `Índice de Unicidad` |

---

## 4. Código SQL para la Reconstrucción del Esquema

A continuación, se presentan las sentencias SQL `CREATE TABLE` utilizadas para definir estas tablas, tal como se encuentran en el archivo `init.sql`:

```sql
-- Creación de la tabla dim_stations (Dimension: Estaciones de Monitoreo)
CREATE TABLE IF NOT EXISTS dim_stations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL
);

-- Creación de la tabla dim_parameters (Dimension: Parámetros/Contaminantes)
CREATE TABLE IF NOT EXISTS dim_parameters (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    units VARCHAR(50) NOT NULL
);

-- Creación de la tabla fact_measurements (Hechos: Mediciones de Calidad del Aire)
CREATE TABLE IF NOT EXISTS fact_measurements (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL,
    parameter_id INTEGER NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    timestamp_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Restricciones de Clave Foránea
    CONSTRAINT fk_station
        FOREIGN KEY (station_id)
        REFERENCES dim_stations (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_parameter
        FOREIGN KEY (parameter_id)
        REFERENCES dim_parameters (id)
        ON DELETE CASCADE,
    -- Restricción de unicidad para evitar registros duplicados
    CONSTRAINT unique_measurement UNIQUE (station_id, parameter_id, timestamp_utc)
);

-- Inserción de datos iniciales para dim_stations (Estación "R K Puram, Delhi - DPCC" ID: 17)
INSERT INTO dim_stations (id, name, city, country_code, latitude, longitude) VALUES
(17, 'R K Puram, Delhi - DPCC', 'Delhi', 'IN', 28.56, 77.17)
ON CONFLICT (id) DO NOTHING;

-- Inserción de datos iniciales para dim_parameters (Parámetros relevantes para la estación 17)
INSERT INTO dim_parameters (id, name, display_name, units) VALUES
(102, 'co', 'CO', 'ppb'),
(24, 'no', 'NO', 'ppb'),
(15, 'no2', 'NO2', 'ppb'),
(23, 'nox', 'NOx', 'ppb'),
(3, 'o3', 'O3', 'µg/m³'),
(1, 'pm10', 'PM10', 'µg/m³'),
(2, 'pm25', 'PM2.5', 'µg/m³'),
(101, 'so2', 'SO2', 'ppb')
ON CONFLICT (id) DO NOTHING;
```

---

## 5. Racional del Modelo Dimensional

La elección de un modelo dimensional para esta base de datos se basa en varias ventajas clave para el contexto de un dashboard analítico:

*   **Optimización para Consultas Analíticas**: Las consultas que involucran agregaciones (AVG, MAX, MIN) y filtros sobre dimensiones son extremadamente eficientes en un esquema estrella.
*   **Claridad y Comprensión del Negocio**: Separa claramente los "hechos" (las mediciones numéricas) de los "atributos" (la descripción de la estación o del contaminante), facilitando la comprensión de los datos por parte de los analistas.
*   **Reducción de Redundancia**: La información de las estaciones y parámetros se almacena una sola vez en sus respectivas tablas de dimensión, reduciendo la duplicación de datos.
*   **Flexibilidad para Cambios**: Es fácil añadir nuevos atributos a una dimensión sin afectar la tabla de hechos, o añadir nuevas dimensiones.
*   **Facilidad de Extracción de Información**: Permite a las herramientas de BI (Business Intelligence) y a los dashboards (como Streamlit) generar informes y visualizaciones de manera más directa y rápida.
