
# Guía de Integración: OpenAQ API para Proyecto Escolar

Esta documentación detalla el uso de la API v3 de OpenAQ para la extracción de datos de calidad del aire en un entorno local de desarrollo.

## 1. Configuración Inicial (Local)
Para un proyecto escolar no productivo, puedes utilizar una **API Key gratuita**.
- **Registro:** Regístrate en [OpenAQ Explorer](https://explore.openaq.org/) para obtener tu llave.
- **Uso:** La llave debe enviarse en el encabezado (header) de cada solicitud HTTP.

**Header Requerido:**
`X-API-Key: TU_API_KEY_AQUI`

## 2. Cómo Aislar una Sola Estación (Location)
Es totalmente posible filtrar los datos para una única estación mediante su **Location ID**.

### A. Encontrar el ID de la estación
Primero, busca estaciones en una ciudad o coordenadas específicas:
`GET https://api.openaq.org/v3/locations?countries_id=MX&limit=10`
*(Ejemplo para México. Revisa el campo `"id"` en la respuesta JSON)*.

### B. Obtener Metadatos de una Estación Específica
Una vez que tengas el ID (ejemplo: `8118`), puedes consultar solo esa ubicación:
`GET https://api.openaq.org/v3/locations/8118`.

### C. Obtener Mediciones de una sola Estación
Para tu pipeline de datos, este es el endpoint más importante para extraer lecturas históricas o recientes de esa estación:
`GET https://api.openaq.org/v3/locations/8118/measurements`.

## 3. Parámetros Críticos para el Pipeline
Para alimentar tu base de datos **PostgreSQL**, utiliza estos parámetros de consulta (Query Params):

| Parámetro | Tipo | Descripción |
| :--- | :--- | :--- |
| `parameters_id` | Integer | Filtra por contaminante (ej: PM2.5, PM10, CO). |
| `date_from` | ISO Date | Fecha de inicio (ej: `2024-01-01T00:00:00Z`). |
| `date_to` | ISO Date | Fecha final. |
| `limit` | Integer | Cantidad de registros por página (Max 1000). |
| `period_name` | String | Agregación (ej: `hourly` para datos cada hora). |

## 4. Flujo de Datos Recomendado (Arquitecto de Datos)
1. **Extracción:** Script en Python usando la librería `requests` para consultar el endpoint de `measurements` filtrado por el `location_id` elegido.
2. **Transformación:** Convertir el JSON de la API a una estructura plana (Dataframe o Diccionario).
3. **Carga:** Insertar en PostgreSQL.
   - *Nota:* Crea una tabla que use el ID de la estación como llave foránea si planeas agregar más estaciones después.
4. **Visualización:** Conectar Power BI a la tabla de PostgreSQL para ver las tendencias.

## 5. Ejemplo de Respuesta JSON (Simplificado)
```json
{
  "results": [
    {
      "period": { "label": "hourly", "interval": "01:00:00" },
      "value": 15.4,
      "parameter": { "name": "pm25", "units": "µg/m³" },
      "date": { "utc": "2026-01-17T08:00:00Z" }
    }
  ]
}

```

```

### Consejos adicionales para tu proyecto:
* **Aislamiento:** Al usar el endpoint `/v3/locations/{id}/measurements`, garantizas que **solo** recibes datos de esa estación específica.
* **Streaming Local:** Dado que OpenAQ actualiza datos en lapsos de tiempo (algunos cada 10-20 min), puedes programar tu script para que corra cada hora y así simular un flujo constante de datos hacia tu base de datos.

```