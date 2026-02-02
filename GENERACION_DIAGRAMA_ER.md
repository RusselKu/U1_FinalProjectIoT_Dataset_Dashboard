# Tutorial: Generación Automática del Diagrama Entidad-Relación (ERD)

Este documento te guiará para generar un Diagrama Entidad-Relación (ERD) de tu base de datos PostgreSQL de forma automática usando un script de Python. Esto te ahorrará el tiempo de dibujarlo manualmente y te dará una representación precisa de tu esquema.

---

## Paso 1: Instalar Prerrequisitos (En tu Máquina Local)

Para que el script funcione, necesitas instalar dos cosas en tu computadora (no dentro de Docker).

### 1.1. Instalar GraphViz

GraphViz es el motor que dibuja el diagrama. La librería de Python lo necesita para funcionar.

- **Opción A (Recomendada - con Winget):**
  1. Abre una terminal de PowerShell como **Administrador**.
  2. Ejecuta el siguiente comando:
     ```powershell
     winget install -e --id Graphviz.Graphviz
     ```
  3. Cierra y vuelve a abrir tu terminal (como VS Code) para que reconozca los nuevos cambios del sistema.

- **Opción B (Manual):**
  1. Ve a la página oficial de descargas de GraphViz: [https://graphviz.org/download/](https://graphviz.org/download/)
  2. Descarga e instala la última versión para Windows.
  3. **¡MUY IMPORTANTE!** Durante la instalación, asegúrate de marcar la casilla que dice **"Add Graphviz to the system PATH for all users"** o similar. Si no haces esto, el script no funcionará.

### 1.2. Instalar Librerías de Python

En tu terminal (la misma que usas para `docker compose`), ejecuta el siguiente comando para instalar las librerías necesarias en tu entorno de Python local:

```bash
pip install eralchemy2 "sqlalchemy<2.0" psycopg2-binary python-dotenv
```
*Nota: Se especifica `sqlalchemy<2.0` porque `eralchemy2` tiene mejor compatibilidad con esa versión.*

---

## Paso 2: Crear el Script de Generación

Crea un nuevo archivo en la raíz de tu proyecto llamado `generar_diagrama.py` y pega el siguiente contenido exacto en él.

```python
import os
from dotenv import load_dotenv

def generar_diagrama_erd():
    """
    Genera un diagrama Entidad-Relación de la base de datos PostgreSQL.
    """
    print("🚀 Iniciando la generación del diagrama ERD...")

    # 1. Cargar las variables de entorno desde el archivo .env
    print("   - Cargando credenciales de la base de datos...")
    load_dotenv()
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "sensordata")
    db_user = os.getenv("DB_USER", "user")
    db_password = os.getenv("DB_PASSWORD", "password")

    # Asegurarnos de que estamos apuntando a localhost, ya que el script corre
    # en tu máquina, no en Docker.
    if db_host != "localhost":
        print(f"   - ADVERTENCIA: El DB_HOST es '{db_host}'. Cambiando a 'localhost' para la conexión local.")
        db_host = "localhost"

    # 2. Construir la cadena de conexión para SQLAlchemy
    # Formato: postgresql+psycopg2://user:password@host:port/database
    db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print(f"   - Cadena de conexión generada para el host: {db_host}")

    # 3. Importar eralchemy2 y renderizar el diagrama
    try:
        from eralchemy2 import render_er
        output_file = "diagrama_entidad_relacion.png"
        print(f"   - Renderizando el diagrama... Esto puede tardar unos segundos.")
        
        # Esta es la función mágica que se conecta a la BD y dibuja todo
        render_er(db_uri, output_file)
        
        print(f"\n✅ ¡Éxito! El diagrama ha sido guardado como: {output_file}")

    except ImportError:
        print("\n❌ ERROR: No se pudo importar 'eralchemy2'.")
        print("   Por favor, asegúrate de haberlo instalado con: pip install eralchemy2")
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")
        print("   - Verifica que los contenedores de Docker (especialmente postgres_db) estén corriendo.")
        print("   - Verifica que GraphViz esté instalado y en el PATH del sistema.")
        print("   - Verifica que las credenciales en tu archivo .env sean correctas.")

if __name__ == "__main__":
    generar_diagrama_erd()

```

---

## Paso 3: Ejecutar el Script

1.  **Asegúrate de que tus contenedores de Docker estén corriendo**, especialmente `postgres_db`. Puedes verificarlo con:
    ```bash
docker compose ps
    ```
    Deberías ver el contenedor `postgres_db` en estado `Up` y saludable.

2.  **Ejecuta el script** desde tu terminal:
    ```bash
python generar_diagrama.py
    ```

3.  El script se conectará a tu base de datos, leerá el esquema (tablas, columnas, relaciones) y generará un archivo de imagen.

---

## Paso 4: El Resultado

Si todo ha ido bien, aparecerá un nuevo archivo en tu proyecto llamado **`diagrama_entidad_relacion.png`**.

Al abrirlo, verás una imagen como esta, mostrando tus tres tablas y las flechas que indican las relaciones de clave foránea (`Foreign Key`) desde `fact_measurements` hacia `dim_stations` y `dim_parameters`.

![Ejemplo de Diagrama ERD](https://i.imgur.com/your-example-image.png)  *(Esta es solo una imagen de ejemplo, la tuya mostrará tus tablas)*

Este archivo de imagen es la evidencia perfecta para tu reporte del "Entity and relationship modeling" y "Database schema design".
