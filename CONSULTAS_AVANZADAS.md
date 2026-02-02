# Documentación de Consultas SQL Avanzadas

Este documento presenta una serie de consultas SQL complejas diseñadas para demostrar capacidades analíticas avanzadas sobre el conjunto de datos de calidad del aire. Estas consultas pueden ser ejecutadas directamente en la pestaña "Explorador SQL" del dashboard.

---

### Consulta 1: Resumen Agregado por Contaminante

**Objetivo**: Obtener un resumen estadístico completo (promedio, máximo, mínimo y conteo de registros) para cada tipo de contaminante disponible en toda la base de datos.

**Utilidad**: Permite comparar de un vistazo qué contaminantes tienden a tener valores más altos o mayor variabilidad.

```sql
SELECT 
    p.display_name AS contaminante,
    p.units AS unidades,
    COUNT(fm.value) AS total_mediciones,
    ROUND(AVG(fm.value)::numeric, 2) AS promedio_valor,
    MAX(fm.value) AS maximo_valor,
    MIN(fm.value) AS minimo_valor
FROM 
    fact_measurements fm
JOIN 
    dim_parameters p ON fm.parameter_id = p.id
GROUP BY 
    p.display_name, p.units
ORDER BY 
    contaminante;
```

**Técnicas Avanzadas Utilizadas**:
*   **`JOIN`**: Se une la tabla de hechos (`fact_measurements`) con la tabla de dimensión (`dim_parameters`) para poder agrupar y mostrar el nombre legible del contaminante en lugar de solo su ID.
*   **`GROUP BY`**: Agrupa millones de registros de mediciones en filas únicas por cada tipo de contaminante.
*   **Funciones de Agregación**: Se utilizan `COUNT`, `AVG`, `MAX`, y `MIN` para calcular las métricas estadísticas para cada grupo.
*   **`ROUND` y `::numeric`**: Se usan para formatear el resultado del promedio a dos decimales, mejorando la legibilidad.

---

### Consulta 2: Comparación con Medición Anterior (Función de Ventana)

**Objetivo**: Para un contaminante específico (en este ejemplo, PM2.5, `parameter_id = 2`), obtener cada medición junto con la medición inmediatamente anterior en el tiempo. Esto permite calcular la diferencia o el cambio instantáneo.

**Utilidad**: Es fundamental para análisis de tendencias y alertas. Permite responder: "¿El nivel de contaminación está subiendo o bajando ahora mismo en comparación con la última hora?".

```sql
SELECT 
    timestamp_utc,
    value AS valor_actual,
    LAG(value, 1) OVER (ORDER BY timestamp_utc) AS valor_anterior,
    (value - LAG(value, 1) OVER (ORDER BY timestamp_utc)) AS diferencia
FROM 
    fact_measurements
WHERE 
    parameter_id = 2 -- Filtrando por PM2.5 (ajustar ID según sea necesario)
ORDER BY 
    timestamp_utc DESC
LIMIT 100;
```

**Técnicas Avanzadas Utilizadas**:
*   **Función de Ventana `LAG()`**: Esta es la técnica clave. `LAG(value, 1) OVER (ORDER BY timestamp_utc)` mira "hacia atrás" en la fila anterior (ordenada por tiempo) y trae el valor de esa fila a la fila actual. Esto permite hacer cálculos entre una medición y su antecesora directa en la misma fila.
*   **`OVER (ORDER BY ...)`**: Define la "ventana" o el conjunto de filas sobre el cual operará la función `LAG`. En este caso, la ventana es el conjunto de datos completo, ordenado por tiempo.

---

### Consulta 3: Días con Alta Contaminación (CTE - Common Table Expression)

**Objetivo**: Identificar los días en que el promedio de un contaminante (ej. PM2.5) superó un umbral específico (ej. 35 µg/m³), y luego mostrar las 5 mediciones más altas registradas exclusivamente en esos días de alta contaminación.

**Utilidad**: Permite un análisis en dos pasos. Primero, se aísla un conjunto de "días problemáticos" y, segundo, se profundiza el análisis solo en ese subconjunto de datos para encontrar los picos extremos.

```sql
WITH dias_alta_contaminacion AS (
    -- Primer paso: Encontrar las fechas de los días cuyo promedio superó 35
    SELECT 
        timestamp_utc::date AS dia
    FROM 
        fact_measurements
    WHERE 
        parameter_id = 2 -- PM2.5
    GROUP BY 
        dia
    HAVING 
        AVG(value) > 35
)
-- Segundo paso: Usar la lista de días para encontrar los valores más altos
SELECT
    fm.timestamp_utc,
    fm.value
FROM
    fact_measurements fm
WHERE
    fm.timestamp_utc::date IN (SELECT dia FROM dias_alta_contaminacion)
    AND fm.parameter_id = 2 -- PM2.5
ORDER BY
    fm.value DESC
LIMIT 5;

```

**Técnicas Avanzadas Utilizadas**:
*   **Expresión de Tabla Común (CTE)**: La cláusula `WITH dias_alta_contaminacion AS (...)` crea una tabla temporal virtual que existe solo durante la ejecución de la consulta. Esto hace que las consultas complejas y de varios pasos sean mucho más legibles y organizadas que anidar múltiples subconsultas.
*   **`HAVING`**: Se usa después de `GROUP BY` para filtrar los *grupos* basados en una condición de agregación (en este caso, donde el promedio `AVG(value)` es mayor a 35).
*   **Subconsulta en `WHERE IN`**: La consulta final filtra las mediciones para incluir solo aquellas cuyo día (`fm.timestamp_utc::date`) está en el conjunto de "días problemáticos" devuelto por la CTE.
