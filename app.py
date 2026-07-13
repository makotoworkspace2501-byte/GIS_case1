import streamlit as st
import geopandas as gpd
import rasterio
from rasterio.features import shapes
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
import os
import json
from shapely.geometry import shape
import backend.climate_module as climate
import backend.segmentation_module as segment
import backend.land_module as land

# Настройка страницы
st.set_page_config(page_title="Мониторинг орошения Марксовский район", layout="wide")
st.title("🌾 Автоматизированная система мониторинга орошения (Марксовский район)")
st.markdown("---")

# Пути к данным
NDVI_DIR = "data/rasters/NDVI"
ERA5_DIR = "data/rasters/ERA5"
VECTOR_PATH = "data/vector/Marksovsky_Rayon.geojson"

# --- КЭШИРОВАНИЕ ДЛЯ УСКОРЕНИЯ (Ваш питомец оптимизировал нагрузку) ---
@st.cache_resource
def load_boundaries():
    """Загрузка границ района (Модуль землеустройства)"""
    if os.path.exists(VECTOR_PATH):
        return gpd.read_file(VECTOR_PATH).to_crs(epsg=4326)
    return gpd.GeoDataFrame()

@st.cache_data
def process_ndvi_year(year):
    """Модуль сегментации орошения: Пороговая классификация и векторизация"""
    file_path = os.path.join(NDVI_DIR, f"NDVI_Summer_{year}.tif")
    if not os.path.exists(file_path): return None
    
    with rasterio.open(file_path) as src:
        ndvi = src.read(1)
        transform = src.transform
        # Пороговая классификация (Орошение vs Богара)
        irrigation_mask = (ndvi > 0.6).astype('uint8')
        
        # Векторизация (преобразование растра в полигоны)
        polygons = []
        for geom, val in shapes(irrigation_mask, transform=transform):
            if val == 1:
                polygons.append(shape(geom))
                
    gdf = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
    return gdf

# --- ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ (Фронтенд) ---

# Боковая панель с настройками
st.sidebar.header("Панель управления")
years = list(range(2000, 2025))
selected_year = st.sidebar.slider("Выберите год для анализа", min_value=2000, max_value=2024, value=2023)

# Загрузка данных
boundaries = load_boundaries()
irrigation_polygons = process_ndvi_year(selected_year)

# 1. Интерактивная карта
st.subheader(f"🗺️ Карта динамики орошения ({selected_year} год)")
m = folium.Map(location=[51.5, 46.7], zoom_start=10, tiles="OpenStreetMap") # Координаты Марксовского района

# Добавление границ района
if not boundaries.empty:
    folium.GeoJson(
        boundaries,
        name="Границы района",
        style_function=lambda x: {"fillColor": "transparent", "color": "black", "weight": 2}
    ).add_to(m)

# Добавление зон орошения
if irrigation_polygons is not None and not irrigation_polygons.empty:
    folium.GeoJson(
        irrigation_polygons,
        name=f"Зоны орошения ({selected_year})",
        style_function=lambda x: {"fillColor": "blue", "color": "blue", "weight": 1, "fillOpacity": 0.5},
        tooltip="Зона орошения"
    ).add_to(m)

st_folium(m, width=1000, height=600)

st.markdown("---")

# 2. Аналитическая панель (Графики)
st.subheader("📊 Аналитическая панель")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Динамика ГТК (Климатический анализ)")
    # Здесь вызывается функция из backend/climate_module.py
    # gtk_data = climate.calculate_gtk_dynamics(ERA5_DIR)
    # Для примера создадим заглушку данных:
    df_gtk = pd.DataFrame({
        'Год': years,
        'ГТК': [0.8, 0.9, 0.7, 1.1, 1.2, 0.6, 0.8, 0.9, 1.0, 0.7, 
                0.8, 0.9, 0.7, 1.1, 1.2, 0.6, 0.8, 0.9, 1.0, 0.7,
                0.8, 0.9, 0.7, 1.1, 1.2] # Заглушка
    })
    fig_gtk = px.line(df_gtk, x='Год', y='ГТК', title="Динамика гидротермического коэффициента")
    st.plotly_chart(fig_gtk, use_container_width=True)

with col2:
    st.markdown("#### Площадь орошения по годам")
    # Расчет площадей (Модуль землеустройства)
    # area_data = land.calculate_irrigation_area_by_year(NDVI_DIR, boundaries)
    df_area = pd.DataFrame({
        'Год': years,
        'Площадь орошения (га)': [1500, 1550, 1400, 1600, 1800, 1300, 1500, 1550, 1700, 1400,
                                  1500, 1550, 1400, 1600, 1800, 1300, 1500, 1550, 1700, 1400,
                                  1500, 1550, 1400, 1600, 1800] # Заглушка
    })
    fig_area = px.bar(df_area, x='Год', y='Площадь орошения (га)', title="Динамика площади орошения")
    st.plotly_chart(fig_area, use_container_width=True)

# 3. Инструмент идентификации и Экспорт
st.markdown("---")
st.subheader("📥 Экспорт данных")
st.write("Данные для выгрузки. Нажмите кнопку, чтобы скачать отчет.")

# Кнопка экспорта (имитация)
csv = df_area.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Скачать таблицу площадей (CSV)",
    data=csv,
    file_name='irrigation_area_dynamics.csv',
    mime='text/csv',
)

st.success("Система мониторинга успешно")
