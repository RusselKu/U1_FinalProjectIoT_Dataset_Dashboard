# AgroAire: Plataforma de Monitoreo de Calidad del Aire para el Sector Agropecuario

---

## 1. Título del Proyecto

**"AgroAire: Sistema de Análisis de Datos de Calidad del Aire para la Protección de Cultivos y Ganadería Local"**

---

## 2. La Problemática Detallada (El "Business Case")

El cliente es un productor agrícola o ganadero de la región (ej. un productor de maíz, hortalizas o ganadería bovina en el sureste mexicano) que opera en zonas rurales o periurbanas donde la calidad del aire está siendo afectada por fuentes externas: industria cercana, quemas agrícolas, tráfico pesado o actividad urbana en expansión.

Actualmente enfrentan:

**Desconocimiento del Riesgo Ambiental:**
Los productores no tienen acceso a datos de contaminación atmosférica en tiempo real. Parámetros como PM2.5, PM10, NO₂, SO₂ y O₃ afectan directamente la salud de los cultivos y el ganado, pero no se monitorean localmente.

**Pérdidas no explicadas en la producción:**
Enfermedades respiratorias en el ganado, reducción del rendimiento fotosintético en cultivos y estrés hídrico se atribuyen al clima, cuando en realidad pueden ser consecuencia directa de la calidad del aire.

**Falta de evidencia para reclamaciones:**
Sin datos históricos de contaminación, los productores no pueden demostrar ante autoridades o aseguradoras que una pérdida fue causada por un evento de contaminación (p. ej., una quema industrial).

**Datos disponibles pero inaccesibles:**
Existen redes de monitoreo como OpenAQ que publican datos públicamente, pero el productor promedio no tiene la infraestructura técnica para consumirlos, procesarlos y visualizarlos de forma accionable.

---

## 3. Rol del Ingeniero de Datos en este Proyecto

No se trata de construir la aplicación del productor directamente, sino de ser el **arquitecto de la inteligencia de datos**. Las responsabilidades técnicas son:

| Área | Tarea Técnica |
|---|---|
| **Ingesta** | Pipeline ETL que consume la API de OpenAQ y almacena mediciones en PostgreSQL |
| **Procesamiento** | Normalización de parámetros (PM2.5, NO₂, O₃) por estación y por ventana de tiempo |
| **Análisis** | Correlación entre picos de contaminación y fechas/horas críticas para el campo |
| **Visualización** | Dashboard interactivo con alertas visuales por umbral de contaminante |
| **Infraestructura** | Optimización del servidor de ingesta para garantizar disponibilidad continua |

---

## 4. Objetivos del Proyecto

### Objetivo Principal
Implementar una plataforma de análisis de calidad del aire que permita a productores agropecuarios **tomar decisiones preventivas** (riego, cosecha, traslado de ganado) basadas en datos, reduciendo pérdidas por eventos de contaminación en un 20% en los primeros 6 meses.

### Objetivos Específicos
- Conectar al menos **3 estaciones de monitoreo** de OpenAQ relevantes a zonas agrícolas de la región en las primeras 4 semanas.
- Generar alertas automáticas cuando un parámetro supere los **umbrales de la OMS** (p. ej., PM2.5 > 25 µg/m³ en 24 h).
- Crear un tablero de control que muestre el **Índice de Calidad del Aire (AQI)** por zona geográfica en tiempo casi real.
- Construir un histórico de al menos **6 meses de datos** para identificar patrones estacionales de contaminación.

---

## 5. ¿Por Qué le Importa la Contaminación al Productor Agropecuario?

### Impacto en Cultivos

| Contaminante | Umbral Crítico | Efecto en el Cultivo |
|---|---|---|
| O₃ (Ozono) | > 40 ppb (8h) | Reduce la fotosíntesis; necrosis foliar en trigo, maíz y jitomate |
| SO₂ | > 0.05 ppm (24h) | Daño en estomas; clorosis y defoliación prematura |
| NO₂ | > 0.1 ppm | Inhibe el crecimiento; afecta la absorción de nitrógeno natural |
| PM2.5 / PM10 | > 25 / 50 µg/m³ | Bloquea la luz solar; se deposita en hojas impidiendo la respiración |

### Impacto en Ganadería

- **PM2.5 y PM10 elevados** provocan enfermedades respiratorias (neumonía, bronquitis) en bovinos y porcinos, incrementando costos veterinarios.
- **Ozono alto** reduce la calidad del forraje, disminuyendo el valor nutritivo del pasto y la productividad de leche.
- **NH₃ (amoníaco)** en zonas de feedlot puede superar concentraciones de 35 ppm, causando estrés crónico y baja en conversión alimenticia.

### ¿Cuándo actuar?

```
AQI 0 – 50    → BUENO       → Operaciones normales
AQI 51 – 100  → MODERADO    → Revisar cultivos sensibles
AQI 101 – 150 → MALO        → Evitar aplicación de agroquímicos; mover ganado a interiores
AQI > 150     → MUY MALO    → Cosecha de emergencia si aplica; alertar a veterinario
```

---

## 6. Estructura de Desglose de Trabajo (EDT / WBS)

### Fase 1 — Diagnóstico y Adquisiciones *(Semanas 1–2)*
- Identificar estaciones OpenAQ en el área de influencia de los productores objetivo.
- Definir los parámetros críticos por tipo de producción (agrícola vs. ganadera).
- Seleccionar infraestructura de cómputo (servidor local vs. cloud).

### Fase 2 — Arquitectura de Datos *(Semanas 3–5)*
- Configurar PostgreSQL con esquema dimensional:
  - `dim_stations` — metadatos de estaciones de monitoreo.
  - `dim_parameters` — catálogo de contaminantes y sus umbrales.
  - `fact_measurements` — mediciones con timestamp, valor, unidad y estación.
- Desarrollar el script `run_publisher.py` como servicio de ingesta continua (loop periódico).
- Dockerizar todos los servicios: ingesta, base de datos y dashboard.

### Fase 3 — Desarrollo del Dashboard *(Semanas 6–8)*
- Construir visualizaciones clave en Streamlit:
  - Mapa interactivo de estaciones con color por AQI.
  - Serie de tiempo por parámetro con anotación de umbrales OMS.
  - Heatmap hora/día para identificar patrones recurrentes de contaminación.
  - Gauge de nivel de riesgo actual por zona.
- Implementar el Explorador SQL para consultas ad hoc del productor.

### Fase 4 — Optimización de la Infraestructura de Ingesta *(Semanas 9–10)*
- Ver sección 7 (áreas de mejora técnica).

### Fase 5 — Piloto y Cierre *(Semanas 11–12)*
- Presentar el sistema a 2–3 productores piloto.
- Comparativa "Antes vs. Después": decisiones empíricas vs. basadas en datos.
- Entrega de documentación técnica completa.

---

## 7. Áreas de Mejora: Servidor e Ingesta de Datos

Esta sección documenta las brechas técnicas actuales y las mejoras necesarias para que el sistema sea robusto, eficiente y escalable.

### 7.1 Ingesta: Limitaciones Actuales

| Problema | Descripción | Impacto |
|---|---|---|
| **Polling síncrono** | `run_publisher.py` hace llamadas secuenciales a la API por cada estación | Lento cuando hay muchas estaciones; bloquea el proceso |
| **Sin manejo de backpressure** | Si la API responde lento, el loop de ingesta se retrasa indefinidamente | Gaps en los datos históricos |
| **Sin reintentos inteligentes** | Un error HTTP 429 (rate limit) detiene la ingesta sin reintento exponencial | Pérdida de datos en ventanas críticas |
| **Inserciones row-by-row** | Se inserta una medición a la vez en PostgreSQL | Bajo throughput; alta carga en el motor de BD |

### 7.2 Mejoras Recomendadas para la Ingesta

**a) Ingesta Asíncrona (asyncio + aiohttp)**
```python
# En lugar de llamadas secuenciales, paralelizar por estación:
import asyncio, aiohttp

async def fetch_station(session, station_id):
    async with session.get(f"/measurements?location_id={station_id}") as r:
        return await r.json()

async def ingest_all(station_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_station(session, sid) for sid in station_ids]
        return await asyncio.gather(*tasks)
```

**b) Inserciones en Batch (COPY o executemany)**
```python
# Acumular registros y hacer un único INSERT masivo
conn.executemany(
    "INSERT INTO fact_measurements VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
    batch_records
)
```

**c) Retry con Backoff Exponencial**
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def call_openaq_api(url, params):
    ...
```

**d) Cola de Mensajes (Redis / RabbitMQ) — Mejora Avanzada**
- Separar el proceso de **extracción** (productor) del proceso de **escritura en BD** (consumidor).
- Permite escalar horizontalmente: múltiples workers de escritura sin modificar la lógica de extracción.

### 7.3 Mejoras Recomendadas para el Servidor / Infraestructura

| Componente | Estado Actual | Mejora Propuesta |
|---|---|---|
| **Base de datos** | PostgreSQL estándar | Agregar índice en `(timestamp, station_id)` para consultas de series de tiempo |
| **Particionamiento** | Sin particiones | Particionar `fact_measurements` por mes (`PARTITION BY RANGE (timestamp)`) |
| **Caché** | Sin caché | Agregar Redis para cachear el AQI actual por estación (TTL: 5 min) |
| **Monitoreo de ingesta** | Sin alertas | Healthcheck en Docker + alertas si el loop de ingesta se detiene |
| **Escalabilidad del dashboard** | Streamlit single-process | Considerar Gunicorn o despliegue en Streamlit Cloud para múltiples usuarios |
| **Datos históricos** | Solo lo que entra en RAM | Configurar `work_mem` y `shared_buffers` en PostgreSQL según recursos del servidor |

### 7.4 Configuración PostgreSQL Recomendada para Series de Tiempo

```sql
-- Índice compuesto crítico para queries del dashboard
CREATE INDEX idx_fact_time_station
  ON fact_measurements (measured_at DESC, station_id, parameter_id);

-- Particionamiento por mes para mantener performance con millones de filas
CREATE TABLE fact_measurements (
  ...
) PARTITION BY RANGE (measured_at);

CREATE TABLE fact_measurements_2025_01
  PARTITION OF fact_measurements
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

## 8. Riesgos Críticos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| 1 | **API de OpenAQ sin datos para la región** | Media | Alto | Validar cobertura geográfica antes del arranque; contemplar otras fuentes (SEMARNAT, INECC) |
| 2 | **Pérdida de conexión durante la ingesta nocturna** | Alta | Medio | Implementar reintentos y guardar un log de gaps para rellenar datos después |
| 3 | **Resistencia del productor al uso de tecnología** | Alta | Medio | Diseñar el dashboard con lenguaje no técnico; usar semáforos de colores y alertas simples |
| 4 | **Cambios en la API de OpenAQ (versiones)** | Baja | Alto | Pinear la versión del endpoint en la configuración; tests de contrato automatizados |
| 5 | **Sobrecarga del servidor con muchas estaciones** | Media | Medio | Limitar el número de estaciones iniciales; implementar ingesta asíncrona (Sección 7.2) |

---

## 9. Valor del Proyecto para Gestión de Proyectos (PM)

Este proyecto es un excelente caso de estudio para practicar:

- **Gestión de Adquisiciones:** Evaluación de fuentes de datos gratuitas (OpenAQ, INECC) vs. pagadas (sensores IoT propios); decisión de build vs. buy para el hardware de campo.
- **Análisis de Costo-Beneficio:** Comparar el costo de implementación contra el costo promedio de pérdida de cosecha por un evento de contaminación no detectado.
- **Gestión de Stakeholders:** El productor agropecuario no es un usuario técnico; la comunicación debe centrarse en impacto económico, no en arquitectura de datos.
- **Control de Calidad de Datos:** Definir qué hacer cuando una estación reporta valores nulos o anómalos (¿imputación, descarte, alerta?).

---

## 10. Métricas de Éxito

| Métrica | Meta | Cómo Medirla |
|---|---|---|
| Disponibilidad del pipeline de ingesta | ≥ 95% del tiempo | Logs de Docker + healthcheck |
| Latencia de datos en dashboard | < 15 minutos respecto a medición real | Comparar timestamp de OpenAQ vs. timestamp en BD |
| Adoption rate por productores piloto | ≥ 2 sesiones/semana por productor | Logs de acceso al dashboard |
| Reducción de incidentes no detectados | ≥ 1 evento prevenido en 6 meses | Entrevista con productores piloto |

---

*Documento generado como parte del proyecto final de Ingeniería de Datos — 2025.*
