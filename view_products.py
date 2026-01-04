import streamlit as st
import pandas as pd
import json
import os

# 1. Настройки страницы
st.set_page_config(page_title="Сетка товаров", layout="wide")

# Путь к файлу
FILE_PATH = r"C:\Users\redmi\Desktop\Parsing\Dior_bags\szwego_products.csv"

# CSS для красивой плитки (выравнивание кнопок и карточек)
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        text-align: center;
    }
    img {
        max-height: 150px;
        object-fit: cover;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Функции загрузки и сохранения
def load_data():
    if not os.path.exists(FILE_PATH):
        st.error("Файл не найден!")
        return pd.DataFrame()
    try:
        # Читаем CSV
        df = pd.read_csv(FILE_PATH, sep=';')
        return df
    except Exception as e:
        st.error(f"Ошибка чтения: {e}")
        return pd.DataFrame()

def save_data(df):
    try:
        # Сохраняем обратно в CSV с теми же параметрами
        df.to_csv(FILE_PATH, sep=';', index=False, encoding='utf-8')
        # st.toast("Файл обновлен!", icon="✅") # Можно включить уведомление
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")

# 3. Функция удаления (Callback)
def delete_item(index_to_delete):
    # Удаляем строку из session_state
    st.session_state['df'] = st.session_state['df'].drop(index_to_delete).reset_index(drop=True)
    # Сохраняем изменения на диск
    save_data(st.session_state['df'])

# 4. Обработка картинок (парсинг JSON)
def get_first_image(photos_str):
    if pd.isna(photos_str) or photos_str == '':
        return None
    try:
        # Очистка специфичных кавычек CSV, если они есть
        clean_str = str(photos_str).replace('""', '"')
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]
        
        images = json.loads(clean_str)
        if isinstance(images, list) and len(images) > 0:
            return images[0]
    except:
        return None
    return None

# --- Основная логика ---

st.title(f"📦 Управление товарами ({FILE_PATH})")

# Инициализация данных в сессии (загружаем один раз при старте)
if 'df' not in st.session_state:
    st.session_state['df'] = load_data()

df = st.session_state['df']

if not df.empty:
    st.write(f"Всего товаров: **{len(df)}**")
    
    # Расчет колонок
    COLS_COUNT = 6
    rows = len(df) // COLS_COUNT + 1

    # Проходим по строкам с шагом 6
    for i in range(0, len(df), COLS_COUNT):
        # Создаем ряд колонок
        cols = st.columns(COLS_COUNT)
        
        # Берем "кусочек" датафрейма (батч из 6 штук)
        batch = df.iloc[i : i + COLS_COUNT]
        
        for idx, (real_index, row) in enumerate(batch.iterrows()):
            with cols[idx]:
                # 1. Картинка
                img_url = get_first_image(row.get('photos'))
                if img_url:
                    st.image(img_url, use_container_width=True)
                else:
                    st.text("Нет фото")

                # 2. Описание (обрезаем, чтобы плитка не была гигантской)
                desc = str(row.get('new_name', ''))
                short_desc = (desc[:40] + '..') if len(desc) > 40 else desc
                st.caption(short_desc if short_desc != 'nan' else "Без описания")

                # 3. Цена
                price = row.get('price', '')
                st.write(f"**{price}**")

                # 4. Кнопка удаления
                # Важно: используем real_index (индекс в df), чтобы удалить правильную строку
                st.button(
                    "❌ Удалить", 
                    key=f"btn_{real_index}", 
                    on_click=delete_item, 
                    args=(real_index,),
                    type="primary" # Красная кнопка (в некоторых темах)
                )

else:
    st.warning("Файл пуст или не загружен.")
