# Arquitectura Final del Sistema de Dashboard de Calidad del Aire

## 1. Resumen Ejecutivo

Este documento describe la arquitectura final del sistema de monitoreo de calidad del aire. El objetivo del proyecto es ingerir datos de una fuente externa, procesarlos, almacenarlos en una base de datos robusta y visualizarlos en un dashboard interactivo.

La arquitectura final ha evolucionado desde un sistema basado en MQTT con datos simulados a un pipeline de datos real y desacoplado que consume información de la API pública de **OpenAQ**. Todo el sistema está orquestado con **Docker Compose**, garantizando la portabilidad y facilidad de despliegue.

La pila tecnológica final es:
- **Fuente de Datos**: OpenAQ API v3
- **Ingesta de Datos (ETL)**: Python (con librerías `openaq` y `pandas`)
- **Base de Datos**: PostgreSQL 13
- **Visualización**: Streamlit
- **Orquestación**: Docker & Docker Compose

---

## 2. Diagrama de Arquitectura

El flujo de datos sigue una secuencia lógica y desacoplada, desde la fuente de datos hasta el usuario final.

```
+----------------+      +-----------------------------+      +-------------------------+      +--------------------------------+      +---------------+
|                |      |                             |      |                         |      |                                |      |               |
|  OpenAQ API    |----->|   Servicio de Ingesta (ETL) |----->|   Base de Datos         |----->|   Servicio de Visualización    |----->| Usuario Final |
|  (Fuente Externa) |      |   (Python / Docker)         |      |   (PostgreSQL / Docker) |      |   (Streamlit / Docker)         |      | (Navegador Web) |
|                |      |                             |      |                         |      |                                |      |               |
+----------------+      +-----------------------------+      +-------------------------+      +--------------------------------+      +---------------+
```

---

## 3. Descripción de Componentes

### 3.1. Fuente de Datos (OpenAQ API)

- **Descripción**: Es una API pública y gratuita que agrega datos de calidad del aire de estaciones de monitoreo a nivel mundial. Se utilizó la **versión 3** de la API.
- **Función**: Provee los datos crudos de las mediciones de los sensores (ej. valor de PM2.5 en un momento dado).
- **Seguridad**: El acceso a la API requiere una **API Key**, que se gestiona de forma segura a través de un archivo `.env` para no exponerla en el código fuente.

### 3.2. Servicio de Ingesta (ETL)

- **Contenedor Docker**: `ingestion`
- **Script Principal**: `run_publisher.py`
- **Descripción**: Este servicio es el corazón del pipeline de datos. Es un script de Python que realiza el proceso de **Extracción, Transformación y Carga (ETL)**.
- **Funcionamiento**:
    1.  **Extracción**: Se conecta a la API de OpenAQ utilizando la **librería oficial `openaq` de Python**, lo que simplifica las llamadas y el manejo de errores.
    2.  **Transformación**: Los datos recibidos de la API son procesados y estructurados en un DataFrame de `pandas` para alinear las columnas con el esquema de la base de datos.
    3.  **Carga**: Se conecta a la base de datos PostgreSQL y carga los datos transformados de forma masiva y eficiente, evitando duplicados.
- **Orquestación**: Se ejecuta después de que el servicio de base de datos esté completamente listo, gracias a la directiva `depends_on` en `docker-compose.yml`.

### 3.3. Servicio de Base de Datos (PostgreSQL)

- **Contenedor Docker**: `postgres_db`
- **Descripción**: Es el sistema de almacenamiento de datos. Se utiliza una imagen oficial de **PostgreSQL 13**.
- **Esquema de Datos**: Al iniciar, el contenedor ejecuta el script `init.sql`, que crea un **modelo dimensional** robusto:
    - `dim_stations`: Almacena metadatos de las estaciones (nombre, ubicación, etc.).
    - `dim_parameters`: Almacena metadatos de los contaminantes (nombre, unidades, etc.).
    - `fact_measurements`: Almacena cada medición individual, vinculada a las tablas de dimensión. Este diseño es escalable y evita la redundancia de datos.
- **Healthcheck**: Se implementó una comprobación de estado (`healthcheck`) en `docker-compose.yml` para asegurar que el servicio de ingesta no intente conectarse antes de que la base de datos esté lista para aceptar conexiones. Esto fue **clave para resolver errores de conexión** durante el arranque.

### 3.4. Servicio de Visualización (Streamlit)

- **Contenedor Docker**: `streamlit_app`
- **Descripción**: Es la interfaz de usuario final. Es una aplicación web desarrollada con **Streamlit** que permite a los usuarios explorar los datos de forma interactiva.
- **Funcionamiento**:
    1.  **Conexión a la BD**: La aplicación se conecta directamente a la base de datos PostgreSQL para realizar consultas. La comunicación entre contenedores se realiza de forma segura a través de la red interna de Docker.
    2.  **Interactividad**: Ofrece filtros dinámicos (selector de contaminante, rango de fechas) que permiten al usuario personalizar las visualizaciones.
    3.  **Visualización**: Presenta los datos a través de componentes interactivos como tarjetas de métricas (KPIs), gráficos de series temporales (con Plotly) y mapas de geolocalización.

---

## 4. Orquestación con Docker Compose

El archivo `docker-compose.yml` es el director de orquesta que define y conecta todos los servicios.

- **Servicios**: Define los tres contenedores (`postgres_db`, `ingestion`, `streamlit`) y sus configuraciones (imagen a usar, puertos, variables de entorno).
- **Redes**: Crea una red virtual (`data_pipeline_net`) para que los contenedores puedan comunicarse entre sí por su nombre de servicio (ej. el servicio `streamlit` se conecta a `postgres_db` a través del host `DB_HOST=postgres_db`).
- **Dependencias**: La directiva `depends_on` gestiona el orden de arranque de los servicios, asegurando que la base de datos inicie primero, seguida por la ingesta y el dashboard.