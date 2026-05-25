import streamlit as st
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os

# Importar las nuevas funciones de conexión
from utils.db_connection import (
    get_available_states,
    get_stations,
    get_available_parameters,
    get_measurement_date_bounds,
    get_summary_stats,
    get_enriched_measurements,
    query_data, # Importamos la función genérica de consulta
    get_recent_etl_runs,
    get_latest_etl_run,
    get_etl_run_events,
    get_etl_summary,
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
available_params = get_available_parameters()
available_states_df = get_available_states()
date_bounds = get_measurement_date_bounds()

if date_bounds is not None and pd.notna(date_bounds.get("max_timestamp")):
    max_timestamp = pd.to_datetime(date_bounds["max_timestamp"]).to_pydatetime()
    min_timestamp = pd.to_datetime(date_bounds["min_timestamp"]).to_pydatetime() if pd.notna(date_bounds.get("min_timestamp")) else max_timestamp
    default_end_date = max_timestamp.date()
    default_start_candidate = (max_timestamp - timedelta(days=7)).date()
    default_start_date = max(min_timestamp.date(), default_start_candidate)
else:
    default_start_date = date.today() - timedelta(days=7)
    default_end_date = date.today()

# --- Barra Lateral de Filtros ---
with st.sidebar:
    st.header("⚙️ Filtros del Dashboard")
    st.markdown("---")

    filter_mode = st.radio("Filtro geográfico", ["Estado", "Estación"], horizontal=True)

    states = ["Todos"]
    if not available_states_df.empty:
        states += available_states_df["state_name"].tolist()

    selected_state = st.selectbox("Estado", options=states, index=0)
    state_filter = None if selected_state == "Todos" else selected_state

    stations_df = get_stations(state_filter)
    if stations_df.empty:
        st.warning("No hay estaciones para el filtro seleccionado.")
        st.stop()

    if filter_mode == "Estación":
        selected_station = st.selectbox(
            "Selecciona una estación",
            options=stations_df.to_dict("records"),
            format_func=lambda s: f"{s['name']} ({s['city']})",
        )
        selected_station_ids = [int(selected_station["id"])]
        selected_stations_map = stations_df[stations_df["id"] == selected_station["id"]]
    else:
        selected_station_ids = stations_df["id"].astype(int).tolist()
        selected_stations_map = stations_df.copy()

    st.caption(f"Estaciones seleccionadas: {len(selected_station_ids)}")

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
        start_date = st.date_input("Desde", default_start_date)
    with col2:
        end_date = st.date_input("Hasta", default_end_date)

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    st.markdown("---")
    if st.button("🔄 Aplicar Filtros y Refrescar", width="stretch", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("📍 Estación Monitoreada")
    if filter_mode == "Estación":
        st.info(f"**Nombre:** {selected_station['name']}\n\n**Ciudad/Estado:** {selected_station['city']}\n\n**País:** {selected_station['country_code']}")
    else:
        st.info(f"**Estado:** {selected_state}\n\n**Total Estaciones:** {len(selected_station_ids)}")

# --- Carga de Datos Principal ---
stats = get_summary_stats(selected_param_id, start_datetime, end_datetime, selected_station_ids)
enriched_df = get_enriched_measurements(selected_param_id, start_datetime, end_datetime, selected_station_ids)

# --- Pestañas Principales ---
tab_main, tab_advanced, tab_sql, tab_etl, tab_info = st.tabs(["📈 Vista General", "🔬 Análisis Avanzado", "🔍 Explorador SQL", "🛠️ ETL Monitor", "ℹ️ Info del Proyecto"])

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
        st.plotly_chart(fig_line, width="stretch")
        st.markdown("---")
        
        tab_map, tab_raw_data = st.tabs(["🗺️ Mapa de la Estación", "📋 Datos Crudos"])
        with tab_map:
            title_suffix = selected_station['name'] if filter_mode == "Estación" else selected_state
            st.subheader(f"Ubicación geográfica: {title_suffix}")
            map_source = selected_stations_map.dropna(subset=["latitude", "longitude"])
            if not map_source.empty:
                map_data = pd.DataFrame({"lat": map_source["latitude"], "lon": map_source["longitude"]})
                st.map(map_data, zoom=7 if filter_mode == "Estado" else 12)
            else:
                st.info("No hay coordenadas disponibles para la selección actual.")
        with tab_raw_data:
            st.subheader("Explorador de Datos Crudos")
            st.dataframe(enriched_df[['timestamp_utc', 'value']].sort_values(by='timestamp_utc', ascending=False), width="stretch")

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
            st.plotly_chart(fig_gauge, width="stretch")
        with col2:
            st.subheader("Promedio por Día de la Semana")
            day_map = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
            daily_avg = enriched_df.groupby('day_of_week')['value'].mean().reset_index()
            daily_avg['day_name'] = daily_avg['day_of_week'].map(day_map)
            daily_avg.sort_values('day_of_week', inplace=True)
            fig_bar = px.bar(daily_avg, x='day_name', y='value', text_auto='.2s', title="Promedio del Contaminante por Día")
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            fig_bar.update_layout(height=350, xaxis_title="Día de la Semana", yaxis_title=f"Valor Promedio ({selected_param_units})", margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_bar, width="stretch")
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Concentración por Hora y Día")
            heatmap_data = enriched_df.pivot_table(index='day_of_week', columns='hour_of_day', values='value', aggfunc='mean').sort_index()
            heatmap_data.index = heatmap_data.index.map(day_map)
            fig_heatmap = px.imshow(heatmap_data, labels=dict(x="Hora del Día", y="Día de la Semana", color=f"Promedio ({selected_param_units})"), x=heatmap_data.columns, y=heatmap_data.index, title="Mapa de Calor de Actividad")
            fig_heatmap.update_layout(height=350, margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_heatmap, width="stretch")
        with col4:
            st.subheader("Distribución de Valores por Día")
            df_box = enriched_df.copy()
            df_box['day_name'] = df_box['day_of_week'].map(day_map)
            fig_box = px.box(df_box, x='day_name', y='value', title="Distribución Diaria (Mediana, Rangos, Atípicos)")
            fig_box.update_layout(height=350, xaxis_title="Día de la Semana", yaxis_title=f"Valor ({selected_param_units})", margin=dict(l=30, r=30, t=50, b=30))
            st.plotly_chart(fig_box, width="stretch")

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
                        st.dataframe(query_result_df, width="stretch")
                    
                except Exception as e:
                    st.error(f"❌ Error al ejecutar la consulta: {e}")
        else:
            st.warning("Por favor, escribe una consulta antes de ejecutar.")

# ======================= PESTAÑA 4: MONITOR ETL =======================
with tab_etl:
    st.markdown(
        """
        <style>
        .etl-wrap { background: linear-gradient(180deg, #0f172a 0%, #111827 100%); color: #e5e7eb; padding: 24px; border-radius: 24px; border: 1px solid rgba(148, 163, 184, 0.18); }
        .etl-title { font-size: 2rem; font-weight: 800; margin-bottom: 4px; }
        .etl-sub { color: #94a3b8; margin-bottom: 18px; }
        .etl-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 18px; }
        .etl-card { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 18px; padding: 16px; box-shadow: 0 10px 30px rgba(2, 6, 23, 0.18); }
        .etl-label { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; }
        .etl-value { font-size: 1.6rem; font-weight: 800; margin-top: 6px; }
        .etl-pill { display:inline-block; padding: 5px 10px; border-radius: 999px; font-size: 0.8rem; margin-right: 8px; }
        .success { background:#064e3b; color:#d1fae5; }
        .running { background:#1e3a8a; color:#dbeafe; }
        .error { background:#7f1d1d; color:#fee2e2; }
        .etl-lane { display:grid; grid-template-columns: 1.1fr 1.9fr; gap: 16px; }
        .etl-box { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 18px; padding: 16px; }
        .etl-event { border-left: 3px solid #38bdf8; padding: 12px 14px; margin-bottom: 10px; background: rgba(30, 41, 59, 0.75); border-radius: 12px; }
        .etl-event.error { border-left-color: #ef4444; }
        .etl-event.success { border-left-color: #22c55e; }
        .etl-event h4 { margin: 0 0 4px 0; font-size: 1rem; }
        .etl-event p { margin: 0; color: #cbd5e1; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    summary = get_etl_summary()
    recent_runs = get_recent_etl_runs()
    latest_run = get_latest_etl_run()

    st.markdown('<div class="etl-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="etl-title">ETL Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="etl-sub">Seguimiento de ejecuciones, estados y eventos del pipeline sin depender de Airflow.</div>', unsafe_allow_html=True)

    if summary is not None:
        total_runs = int(summary.get("total_runs", 0) or 0)
        success_runs = int(summary.get("success_runs", 0) or 0)
        error_runs = int(summary.get("error_runs", 0) or 0)
        success_rate = (success_runs / total_runs * 100) if total_runs else 0
        total_inserted_rows = int(summary.get("total_inserted_rows", 0) or 0)
        total_discovered_locations = int(summary.get("total_discovered_locations", 0) or 0)

        st.markdown(
            f"""
            <div class="etl-grid">
                <div class="etl-card"><div class="etl-label">Ejecuciones totales</div><div class="etl-value">{total_runs}</div></div>
                <div class="etl-card"><div class="etl-label">Tasa de éxito</div><div class="etl-value">{success_rate:.1f}%</div></div>
                <div class="etl-card"><div class="etl-label">Filas insertadas</div><div class="etl-value">{total_inserted_rows}</div></div>
                <div class="etl-card"><div class="etl-label">Ubicaciones descubiertas</div><div class="etl-value">{total_discovered_locations}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="etl-lane">', unsafe_allow_html=True)
    st.markdown('<div class="etl-box">', unsafe_allow_html=True)
    st.subheader("Última ejecución")
    if latest_run is None:
        st.info("Todavía no hay ejecuciones registradas.")
    else:
        status = str(latest_run["status"]).lower()
        status_class = "success" if status == "success" else "error" if status == "error" else "running"
        st.markdown(
            f"""
            <span class="etl-pill {status_class}">{status.upper()}</span>
            <span class="etl-pill running">{latest_run['extraction_mode']}</span>
            <span class="etl-pill">Run #{int(latest_run['id'])}</span>
            """,
            unsafe_allow_html=True,
        )
        st.write(f"Inicio: {latest_run['started_at']}")
        if latest_run.get("finished_at") is not None:
            st.write(f"Fin: {latest_run['finished_at']}")
        st.write(f"Ubicaciones: {int(latest_run['discovered_locations'] or 0)}")
        st.write(f"Filas insertadas: {int(latest_run['inserted_rows'] or 0)}")
        if latest_run.get("error_message"):
            st.error(latest_run["error_message"])
        run_events = get_etl_run_events(int(latest_run["id"]))
        if not run_events.empty:
            st.markdown("**Eventos recientes**")
            for _, event in run_events.tail(12).iterrows():
                event_status = str(event["status"]).lower()
                event_class = "success" if event_status == "success" else "error" if event_status == "error" else "running"
                st.markdown(
                    f"""
                    <div class="etl-event {event_class}">
                        <h4>{event['event_type']} · {event['status']}</h4>
                        <p>{event['message']}</p>
                        <p style="font-size: 0.78rem; color: #94a3b8;">{event['created_at']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="etl-box">', unsafe_allow_html=True)
    st.subheader("Historial reciente")
    if recent_runs.empty:
        st.info("Sin historial todavía.")
    else:
        view_df = recent_runs.copy()
        view_df["status"] = view_df["status"].str.upper()
        st.dataframe(view_df, width="stretch", hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= PESTAÑA 4: INFORMACIÓN =======================
with tab_info:
    st.header("Información del Proyecto", divider="rainbow")
    st.markdown("""
    **Arquitectura del Sistema:** ... (contenido igual que antes)
    """)
    st.markdown("---")
    st.markdown("Desarrollado con ❤️ para el Proyecto Final de IoT.")