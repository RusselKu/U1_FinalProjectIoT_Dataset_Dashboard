import streamlit as st
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os

# Importar las nuevas funciones de conexión
from utils.db_connection import (
    get_station_info,
    get_available_parameters,
    get_summary_stats,
    get_enriched_measurements,
    query_data, # Importamos la función genérica de consulta
)

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Dashboard de Calidad del Aire",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Función para Cargar CSS Externo ---
def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Cargar Estilos y Título Principal ---
load_css("styles/main.css")
st.markdown('<h1 style="text-align: center; color: #1E88E5;">Dashboard de Calidad del Aire</h1>', unsafe_allow_html=True)

# --- Carga de Datos Inicial ---
station_info = get_station_info()
available_params = get_available_parameters()

# --- Barra Lateral de Filtros ---
with st.sidebar:
    st.header("⚙️ Filtros del Dashboard")
    st.markdown("---")

    if not available_params.empty:
        selected_param = st.selectbox(
            "Selecciona un Parámetro",
            options=available_params.to_dict("records"),
            format_func=lambda p: f"{p['display_name']} ({p['units']})",
        )
        selected_param_id = selected_param["id"]
        selected_param_name = selected_param["display_name"]
        selected_param_units = selected_param["units"]
    else:
        st.error("No hay parámetros disponibles.")
        st.stop()

    st.markdown("**Rango de Fechas**")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Desde", date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("Hasta", date.today())

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    st.markdown("---")
    if st.button("🔄 Aplicar Filtros y Refrescar", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("📍 Estación Monitoreada")
    if station_info is not None:
        st.info(f"**Nombre:** {station_info['name']}\n\n**Ciudad:** {station_info['city']}\n\n**País:** {station_info['country_code']}")

# --- Carga de Datos Principal ---
stats = get_summary_stats(selected_param_id, start_datetime, end_datetime)
enriched_df = get_enriched_measurements(selected_param_id, start_datetime, end_datetime)

# --- Pestañas Principales ---
tab_main, tab_advanced, tab_sql, tab_info = st.tabs(["📈 Vista General", "🔬 Análisis Avanzado", "🔍 Explorador SQL", "ℹ️ Info del Proyecto"])

# ======================= PESTAÑA 1: VISTA GENERAL =======================
with tab_main:
    if enriched_df.empty or stats is None:
        st.warning("⚠️ No se encontraron datos para los filtros seleccionados. Por favor, ajusta el rango de fechas o el parámetro.")
    else:
        st.header(f"Visualización de {selected_param_name}", divider="rainbow")
        st.subheader("Resumen del Periodo")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor Promedio", f"{stats['average_value']:.2f} {selected_param_units}")
        col2.metric("Valor Máximo", f"{stats['max_value']:.2f} {selected_param_units}")
        col3.metric("Valor Mínimo", f"{stats['min_value']:.2f} {selected_param_units}")
        col4.metric("Último Valor Registrado", f"{stats['latest_value']:.2f} {selected_param_units}")
        st.markdown("---")

        st.subheader(f"Evolución de {selected_param_name} a lo largo del tiempo")
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=enriched_df['timestamp_utc'], y=enriched_df['value'], mode='lines', name=selected_param_name, line=dict(color='#1E88E5', width=3)))
        fig_line.update_layout(xaxis_title="Fecha y Hora (UTC)", yaxis_title=f"Valor ({selected_param_units})", hovermode='x unified', height=500, xaxis_rangeslider_visible=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig_line, use_container_width=True)
        st.markdown("---")
        
        tab_map, tab_raw_data = st.tabs(["🗺️ Mapa de la Estación", "📋 Datos Crudos"])
        with tab_map:
            st.subheader(f"Ubicación de la Estación: {station_info['name']}")
            if station_info is not None and 'latitude' in station_info and 'longitude' in station_info:
                map_data = pd.DataFrame({'lat': [station_info['latitude']], 'lon': [station_info['longitude']]})
                st.map(map_data, zoom=12)
        with tab_raw_data:
            st.subheader("Explorador de Datos Crudos")
            st.dataframe(enriched_df[['timestamp_utc', 'value']].sort_values(by='timestamp_utc', ascending=False), use_container_width=True)

# ======================= PESTAÑA 2: ANÁLISIS AVANZADO =======================
with tab_advanced:
    if enriched_df.empty or stats is None:
        st.warning("⚠️ No se encontraron datos para los filtros seleccionados.")
    else:
        st.header(f"Análisis de Patrones para {selected_param_name}", divider="rainbow")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Nivel Actual (Último Valor)")
            latest_val = stats['latest_value']
            fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=latest_val, title={'text': f"Último Valor ({selected_param_units})"}, gauge={'axis': {'range': [None, max(latest_val * 2, 50)]}, 'bar': {'color': "#1a1a1a"}, 'steps': [{'range': [0, 50], 'color': "lightgreen"}, {'range': [50, 100], 'color': "yellow"}, {'range': [100, 150], 'color': "orange"}, {'range': [150, 200], 'color': "red"}, {'range': [200, 300], 'color': "purple"}]}))
            fig_gauge.update_layout(height=350, margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_gauge, use_container_width=True)
        with col2:
            st.subheader("Promedio por Día de la Semana")
            day_map = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
            daily_avg = enriched_df.groupby('day_of_week')['value'].mean().reset_index()
            daily_avg['day_name'] = daily_avg['day_of_week'].map(day_map)
            daily_avg.sort_values('day_of_week', inplace=True)
            fig_bar = px.bar(daily_avg, x='day_name', y='value', text_auto='.2s', title="Promedio del Contaminante por Día")
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            fig_bar.update_layout(height=350, xaxis_title="Día de la Semana", yaxis_title=f"Valor Promedio ({selected_param_units})", margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Concentración por Hora y Día")
            heatmap_data = enriched_df.pivot_table(index='day_of_week', columns='hour_of_day', values='value', aggfunc='mean').sort_index()
            heatmap_data.index = heatmap_data.index.map(day_map)
            fig_heatmap = px.imshow(heatmap_data, labels=dict(x="Hora del Día", y="Día de la Semana", color=f"Promedio ({selected_param_units})"), x=heatmap_data.columns, y=heatmap_data.index, title="Mapa de Calor de Actividad")
            fig_heatmap.update_layout(height=350, margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_heatmap, use_container_width=True)
        with col4:
            st.subheader("Distribución de Valores por Día")
            df_box = enriched_df.copy()
            df_box['day_name'] = df_box['day_of_week'].map(day_map)
            fig_box = px.box(df_box, x='day_name', y='value', title="Distribución Diaria (Mediana, Rangos, Atípicos)")
            fig_box.update_layout(height=350, xaxis_title="Día de la Semana", yaxis_title=f"Valor ({selected_param_units})", margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_box, use_container_width=True)

# ======================= PESTAÑA 3: EXPLORADOR SQL =======================
with tab_sql:
    st.header("Consola de Consultas SQL", divider="rainbow")
    st.info("Ejecuta consultas `SELECT` directamente sobre la base de datos. Las consultas que modifiquen datos (`UPDATE`, `DELETE`, etc.) serán bloqueadas.")

    query_text = st.text_area("Escribe tu consulta SQL aquí:", height=150, placeholder="SELECT * FROM fact_measurements LIMIT 10;")

    if st.button("🚀 Ejecutar Consulta", type="primary"):
        if query_text:
            # Medida de seguridad simple para evitar modificaciones
            if "update" in query_text.lower() or "delete" in query_text.lower() or "insert" in query_text.lower() or "drop" in query_text.lower() or "alter" in query_text.lower():
                st.error("❌ ERROR: Solo se permiten consultas de tipo `SELECT`.")
            else:
                try:
                    query_result_df = query_data(query_text)
                    st.success(f"✅ Consulta ejecutada con éxito. Se encontraron {len(query_result_df)} registros.")
                    st.markdown("---")
                    
                    # Lógica de visualización inteligente
                    st.subheader("Resultados de la Consulta")
                    
                    if not query_result_df.empty:
                        # Opción 1: Visualización automática
                        if len(query_result_df.columns) == 2:
                            col1, col2 = query_result_df.columns
                            if pd.api.types.is_numeric_dtype(query_result_df[col2]) and pd.api.types.is_datetime64_any_dtype(query_result_df[col1]):
                                st.write("Visualización sugerida: Gráfico de Líneas")
                                st.line_chart(query_result_df.set_index(col1))
                            elif pd.api.types.is_numeric_dtype(query_result_df[col1]) and pd.api.types.is_datetime64_any_dtype(query_result_df[col2]):
                                st.write("Visualización sugerida: Gráfico de Líneas")
                                st.line_chart(query_result_df.set_index(col2))
                            elif pd.api.types.is_numeric_dtype(query_result_df[col2]) and pd.api.types.is_string_dtype(query_result_df[col1]):
                                st.write("Visualización sugerida: Gráfico de Barras")
                                st.bar_chart(query_result_df.set_index(col1))
                            elif pd.api.types.is_numeric_dtype(query_result_df[col1]) and pd.api.types.is_string_dtype(query_result_df[col2]):
                                st.write("Visualización sugerida: Gráfico de Barras")
                                st.bar_chart(query_result_df.set_index(col2))

                        # Opción 2: Mostrar siempre la tabla de datos
                        st.write("Datos en Tabla:")
                        st.dataframe(query_result_df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error al ejecutar la consulta: {e}")
        else:
            st.warning("Por favor, escribe una consulta antes de ejecutar.")

# ======================= PESTAÑA 4: INFORMACIÓN =======================
with tab_info:
    st.header("Información del Proyecto", divider="rainbow")
    st.markdown("""
    **Arquitectura del Sistema:** ... (contenido igual que antes)
    """)
    st.markdown("---")
    st.markdown("Desarrollado con ❤️ para el Proyecto Final de IoT.")