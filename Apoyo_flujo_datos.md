# Flujo de Datos y Lógica de Implementación

Este documento detalla la lógica interna de los scripts que componen el pipeline de datos y el dashboard de visualización, desde cómo se obtienen los datos hasta cómo se presentan.

---

## 1. Flujo de Ingesta de Datos (Backend)

- **Objetivo**: Poblar la base de datos PostgreSQL con datos de calidad del aire desde la API de OpenAQ de forma automatizada y robusta.
- **Script Principal**: `run_publisher.py`
- **Ubicación**: Se ejecuta dentro del contenedor Docker `ingestion`.

### Lógica Detallada del Script de Ingesta

El script sigue un proceso ETL (Extracción, Transformación y Carga) bien definido:

#### **Paso 1: Configuración y Conexión**
1.  **Carga de Secretos**: Se utiliza la librería `dotenv` para cargar de forma segura la `OPENAQ_API_KEY` y las credenciales de la base de datos desde un archivo `.env`.
2.  **Conexión a la BD**: Se establece una conexión con la base de datos PostgreSQL usando `psycopg2`. La función de conexión incluye reintentos para manejar casos donde el contenedor de la BD tarde un poco en arrancar.

#### **Paso 2: Extracción (E)**
1.  **Instancia del Cliente**: Se crea una instancia del cliente de la API de OpenAQ: `openaq.OpenAQ(api_key=...)`.
2.  **Iteración de Sensores**: El script itera sobre un diccionario predefinido (`SENSOR_PARAMETER_MAPPING`) que mapea los IDs de los sensores de la estación a los IDs de los parámetros en nuestra base de datos.
3.  **Determinación del Rango de Fechas**: Para cada sensor, el script es inteligente:
    - Primero, consulta la tabla `fact_measurements` para encontrar el `timestamp` más reciente que ya ha sido guardado.
    - Si encuentra un `timestamp`, la consulta a la API pedirá datos a partir de ese momento (`latest_ts + 1 segundo`), evitando descargar datos duplicados.
    - Si no hay datos para ese sensor, por defecto solicita los datos de los últimos 7 días.
4.  **Llamada a la API**: Se realiza la llamada usando `api.measurements.list()`. Durante el desarrollo, se corrigieron varios errores clave en los parámetros de esta llamada:
    - Se usa `sensors_id` (no `sensor`).
    - Se usa `datetime_from` (no `date_from`).
    - El `limit` se ajustó a `1000` (el máximo permitido por la librería).

#### **Paso 3: Transformación (T)**
1.  **Manejo de la Respuesta**: La respuesta de la librería (`resp.results`) es una lista de objetos `Measurement`.
2.  **Acceso a Datos**: Se itera sobre esta lista y se extraen los datos relevantes. Se descubrió que la ruta correcta para el timestamp era `r.period.datetime_from.utc`.
3.  **Estructuración en DataFrame**: Los datos extraídos se cargan en un DataFrame de `pandas`, que es una estructura ideal para la manipulación de datos tabulares. Se añaden las columnas faltantes (`station_id`, `parameter_id`) para que coincida con el esquema de la tabla de destino.

#### **Paso 4: Carga (L)**
1.  **Inserción Masiva**: En lugar de insertar fila por fila (lo cual es muy ineficiente), se utiliza la función `psycopg2.extras.execute_values`. Esta convierte el DataFrame en una lista de tuplas y las inserta todas en una sola transacción a la base de datos.
2.  **Manejo de Conflictos**: La consulta de `INSERT` incluye la cláusula `ON CONFLICT (station_id, parameter_id, timestamp_utc) DO NOTHING`. Esto es crucial para la robustez del sistema, ya que si el script se ejecuta varias veces con los mismos datos, simplemente ignora los registros duplicados en lugar de fallar.

---

## 2. Flujo de Visualización de Datos (Frontend)

- **Objetivo**: Presentar los datos almacenados en PostgreSQL de una forma interactiva, clara y estéticamente agradable.
- **Framework**: Streamlit
- **Ubicación**: Se ejecuta dentro del contenedor Docker `streamlit_app`.

### Lógica Detallada del Dashboard

#### **Módulo de Acceso a Datos (`utils/db_connection.py`)**

Este módulo centraliza toda la lógica de consultas a la base de datos.

1.  **Conexión Cacheada**: La función `get_db_connection()` está decorada con `@st.cache_resource`. Esto es una optimización clave de Streamlit que asegura que la conexión a la base de datos se establezca **una sola vez** y se reutilice en todas las interacciones del usuario, en lugar de abrir y cerrar conexiones constantemente.
2.  **Funciones de Consulta Cacheadas**: Las funciones que leen datos (ej. `get_measurements_data`) usan `@st.cache_data(ttl=...)`. Esto significa que si un usuario no cambia los filtros, Streamlit no volverá a ejecutar la consulta a la base de datos, sino que servirá los resultados desde la memoria cache, haciendo la aplicación mucho más rápida.
3.  **Consultas con `JOIN`**: Las consultas están diseñadas para el modelo dimensional. Por ejemplo, `get_measurements_data` une `fact_measurements` con `dim_parameters` para obtener el nombre y las unidades del contaminante junto con sus valores.

#### **Aplicación Principal (`app.py`)**

1.  **Carga Inicial**: Al iniciar la app, se obtienen los parámetros disponibles (`get_available_parameters`) para construir dinámicamente el menú de filtros.
2.  **Interfaz de Usuario y Filtros**:
    - Se utiliza `st.sidebar` para agrupar todos los controles (selector de parámetro y rango de fechas).
    - El selector de parámetros se crea a partir de los datos reales de la base de datos, asegurando que solo se puedan seleccionar contaminantes para los que existen datos.
3.  **Flujo Reactivo**:
    - El usuario interactúa con los filtros de la barra lateral.
    - Al presionar el botón "Aplicar Filtros", Streamlit re-ejecuta el script.
    - Las funciones de `db_connection.py` son llamadas con los nuevos valores de los filtros.
    - Como las funciones están cacheadas, solo se ejecutarán nuevas consultas a la BD si los filtros han cambiado.
4.  **Renderizado de Componentes**:
    - **KPIs**: Las tarjetas de métricas (`st.metric`) se rellenan con los datos de la función `get_summary_stats`.
    - **Gráfica Principal**: Los datos de `get_measurements_data` se pasan a una figura de `Plotly`, que ofrece una visualización interactiva (zoom, paneo, etc.) y un "rangeslider" para una navegación de fechas más cómoda.
    - **Mapa y Tabla**: Los datos de la estación y las mediciones se utilizan para renderizar el mapa (`st.map`) y la tabla de datos crudos (`st.dataframe`) en sus respectivas pestañas.

---

## 3. Modelo de Datos (Esquema de la BD)

- **Archivo de Definición**: `init.sql`
- **Modelo**: Dimensional, compuesto por tablas de hechos y tablas de dimensión.

- **`dim_stations` (Tabla de Dimensión)**
    - **Propósito**: Almacena atributos de las estaciones de monitoreo.
    - **Campos Clave**: `id` (PK), `name`, `city`, `latitude`, `longitude`.
    - **Ventaja**: Evita repetir la información de la estación en cada registro de medición.

- **`dim_parameters` (Tabla de Dimensión)**
    - **Propósito**: Describe los parámetros o contaminantes medidos.
    - **Campos Clave**: `id` (PK), `name` (ej. "pm25"), `display_name` (ej. "PM2.5"), `units` (ej. "µg/m³").
    - **Ventaja**: Centraliza la información de los contaminantes.

- **`fact_measurements` (Tabla de Hechos)**
    - **Propósito**: Es la tabla principal que almacena cada medición individual.
    - **Campos Clave**: `id` (PK), `station_id` (FK a `dim_stations`), `parameter_id` (FK a `dim_parameters`), `value`, `timestamp_utc`.
    - **Ventaja**: Este diseño es muy eficiente para realizar consultas analíticas (ej. "dame el promedio de PM2.5 para la estación X en el último mes").
    - **Índices**: La clave primaria compuesta `(station_id, parameter_id, timestamp_utc)` no solo garantiza la unicidad, sino que también actúa como un índice que acelera enormemente las consultas filtradas por estos campos.