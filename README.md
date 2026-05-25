# 🚀 OpenAQ Data Pipeline and Visualization Dashboard

Un sistema completo de ingesta de datos, almacenamiento y visualización que consume datos reales de la API de OpenAQ, los procesa y los presenta en un dashboard interactivo de Streamlit.

**Diseñado como un proyecto final robusto que demuestra un pipeline de datos de punta a punta.**

## 📋 Arquitectura del Sistema

El proyecto sigue una arquitectura de pipeline de datos moderna y desacoplada.

```
┌────────────────┐      ┌─────────────────────────────┐      ┌─────────────────────┐      ┌────────────────────────────┐      ┌───────────────┐
│                │      │   Servicio de Ingesta (ETL) │      │                     │      │  Servicio de Visualización │      │               │
│  OpenAQ API    ├─────►│     (Python / Docker)       ├─────►│   PostgreSQL        ├─────►│    (Streamlit / Docker)    ├─────►│ Usuario Final │
│ (Fuente Externa) │      │                             │      │   (Docker)          │      │                            │      │ (Navegador Web) │
│                │      │                             │      │                     │      │                            │      │               │
└────────────────┘      └─────────────────────────────┘      └─────────────────────┘      └────────────────────────────┘      └───────────────┘
```

## 🎯 Componentes Principales

### 1. **Fuente de Datos: OpenAQ API**
- **Descripción**: API pública que provee datos de monitoreo de calidad del aire de estaciones a nivel mundial.
- **Función**: Actúa como la fuente de datos crudos para nuestro pipeline.
- **Seguridad**: El acceso requiere una API Key, gestionada de forma segura a través de un archivo `.env`.

### 2. **Servicio de Ingesta (ETL)**
- **Contenedor**: `ingestion`
- **Descripción**: Un script de Python (`run_publisher.py`) que se ejecuta en un bucle dentro de un contenedor Docker. Es el corazón del pipeline y realiza el proceso de **Extracción, Transformación y Carga (ETL)**.
- **Funcionamiento**: Se conecta a la API de OpenAQ, extrae los datos, los transforma a un formato adecuado y los carga en la base de datos PostgreSQL.

### 3. **Base de Datos PostgreSQL**
- **Contenedor**: `postgres_db`
- **Descripción**: Base de datos relacional que almacena los datos de calidad del aire en un **modelo dimensional** (esquema de estrella), lo que optimiza las consultas analíticas.
- **Esquema**:
    - `dim_stations`: Almacena metadatos de las estaciones.
    - `dim_parameters`: Almacena metadatos de los contaminantes.
    - `fact_measurements`: Almacena cada medición individual.
- **Inicialización**: El esquema se crea automáticamente al iniciar el contenedor gracias al script `init.sql`.

### 4. **Dashboard de Streamlit**
- **Contenedor**: `streamlit_app`
- **Descripción**: Una aplicación web interactiva para la visualización y análisis de los datos.
- **Funcionalidades**:
    - **Vista General**: KPIs, serie temporal, mapa de la estación y tabla de datos crudos.
    - **Análisis Avanzado**: 4 gráficas adicionales (Gauge, Barras, Heatmap, Box Plot) para descubrir patrones.
    - **Explorador SQL**: Una consola para ejecutar consultas `SELECT` personalizadas directamente sobre la base de datos.
    - **ETL Monitor**: Vista tipo panel operativo con ejecuciones, eventos y estado del pipeline sin usar Airflow.

### 5. **ETL Regional**
- **Modo por defecto**: `regional`
- **Cobertura**: descubre estaciones por geografía para Guanajuato, Estado de México, CDMX, Querétaro e Hidalgo.
- **Respaldo**: `legacy` conserva el flujo original de India si necesitas comparar resultados o depurar.

---

## 🚀 Inicio Rápido (2 Pasos)

1.  **Configurar Variables de Entorno**:
    *   Renombra el archivo `.env.example` a `.env`.
    *   Abre el archivo `.env` y pega tu API Key de OpenAQ en la variable `OPENAQ_API_KEY`.

2.  **Iniciar todos los servicios con Docker Compose**:
    ```bash
    docker compose up --build
    ```
    *   El flag `--build` es importante para construir las imágenes con la configuración correcta la primera vez.

**¡Eso es todo!** El sistema está corriendo. El script de ingesta comenzará a poblar la base de datos y el dashboard estará disponible.

### Acceso a Servicios

- 📊 **Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)
- 🗄️ **PostgreSQL**: `localhost:5432` (usuario: `user`, contraseña: `password`, bd: `sensordata`)

## 📁 Estructura del Proyecto Clave

```
U1_FinalProjectIoT_Dataset_Dashboard/
├── docker-compose.yml          # Orquestación de todos los servicios Docker
├── init.sql                    # Script de inicialización de la BD
├── .env                        # Archivo para tus variables de entorno (API Key, etc.)
├── run_publisher.py            # Script principal del servicio de ingesta (ETL)
├── Dockerfile                  # Define la imagen para el servicio de ingesta
│
├── streamlit_app/
│   ├── Dockerfile              # Define la imagen para el servicio de Streamlit
│   ├── app.py                  # Código principal del dashboard
│   └── utils/
│       └── db_connection.py    # Lógica para conectar Streamlit a la BD
│
└── [Documentación]
    ├── README.md               # Este archivo
    ├── DISEÑO_DB.md            # Descripción detallada del esquema de la BD
    ├── CONSULTAS_AVANZADAS.md  # Ejemplos de queries SQL complejas
    └── ...
```

## 🔧 Configuración (`.env`)

Asegúrate de que tu archivo `.env` contenga lo siguiente:

```env
# API Key para la API de OpenAQ
OPENAQ_API_KEY=TU_API_KEY_AQUI

# Configuración de la Base de Datos (usada por los scripts y Streamlit)
DB_HOST=postgres_db
DB_PORT=5432
DB_NAME=sensordata
DB_USER=user
DB_PASSWORD=password

# Control de extracción
EXTRACTION_MODE=regional
OPENAQ_LOOKBACK_DAYS=7
```

## 🐳 Comandos Docker Principales

```bash
# Construir e iniciar todos los servicios en segundo plano
docker compose up -d --build

# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico (ej. streamlit)
docker compose logs -f streamlit

# Detener todos los servicios
docker compose down

# Detener servicios y eliminar volúmenes de datos (reinicio limpio)
docker compose down --volumes
```

## 📊 SQL Queries de Ejemplo

Estas consultas se pueden ejecutar en la pestaña "Explorador SQL" del dashboard.

### Resumen por Contaminante
```sql
SELECT
    p.display_name AS contaminante,
    p.units AS unidades,
    COUNT(fm.value) AS total_mediciones,
    ROUND(AVG(fm.value)::numeric, 2) AS promedio_valor
FROM fact_measurements fm
JOIN dim_parameters p ON fm.parameter_id = p.id
GROUP BY p.display_name, p.units
ORDER BY contaminante;
```

### Comparación con Medición Anterior
```sql
SELECT
    timestamp_utc,
    value AS valor_actual,
    LAG(value, 1) OVER (ORDER BY timestamp_utc) AS valor_anterior
FROM fact_measurements
WHERE parameter_id = 2 -- PM2.5
ORDER BY timestamp_utc DESC
LIMIT 100;
```

## 🐛 Solución de Problemas

### Error: "cannot allocate memory" durante `docker compose up --build`
- **Causa**: Docker no tiene suficiente RAM para compilar dependencias.
- **Solución**: Se ha optimizado el `Dockerfile` para no instalar `gcc`, lo que resuelve este problema. Si persiste, aumenta la memoria asignada a Docker Desktop en `Settings > Resources`.

### Dashboard sin datos o con el error "No hay parámetros disponibles"
- **Causa**: El script de ingesta aún no ha cargado datos.
- **Solución**: Espera 1-2 minutos después de iniciar los contenedores para que el primer ciclo de ingesta se complete. Refresca la página del dashboard.

### Error de Conexión a la Base de Datos desde Streamlit
- **Causa**: El contenedor de Streamlit inició antes de que la base de datos estuviera lista.
- **Solución**: El `docker-compose.yml` está configurado con `depends_on` y `healthcheck` para evitar esto. Un `docker compose restart streamlit` debería solucionarlo si ocurre.

## 🎓 Este Proyecto Demuestra
- ✅ Diseño de un pipeline de datos real (ETL).
- ✅ Consumo de una API externa (OpenAQ).
- ✅ Diseño de base de datos con un modelo dimensional (esquema de estrella).
- ✅ Orquestación de microservicios con Docker Compose.
- ✅ Desarrollo de un dashboard interactivo y analítico con Streamlit.
- ✅ Uso de SQL avanzado (JOINs, Funciones de Ventana, Agregaciones).

---

**Estado**: ✅ Listo para Producción (Nivel Educativo)
**Última actualización**: Febrero 2026
**Diseño**: Proyecto Final de IoT

¡Listo para desplegar y presentar! 🎉
