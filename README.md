Sistema De tickets de la UPRIT

## 🛠️ Requisitos Previos

- Python 3.10.7 o superior
- PostgreSQL 13 o superior
- pip (gestor de paquetes de Python)

## 🚀 Instalación

1. Clonar el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd sisoai
   ```

2. Crear y activar un entorno virtual (recomendado):
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Unix o MacOS:
   source venv/bin/activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   - Copiar el archivo `.env.example` a `.env`
   - Configurar las credenciales de la base de datos en `.env`

5. Inicializar la base de datos:
   ```bash
   python -c "from database import create_tables; create_tables()"
   ```

## 🏃 Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 🔒 Credenciales por Defecto

- **Usuario:** admin
- **Contraseña:** admin

¡Recuerda cambiar estas credenciales en producción!

## 🏗️ Estructura del Proyecto

```
sisoai/
├── app.py               # Aplicación principal de Streamlit
├── models.py            # Modelos de base de datos
├── database.py          # Configuración de la base de datos
├── config.py            # Configuración de la aplicación
├── requirements.txt     # Dependencias del proyecto
└── .env.example         # Plantilla de variables de entorno
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
