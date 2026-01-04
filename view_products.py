import streamlit as st
import pandas as pd
import json
from pathlib import Path

# 1. Настройки страницы
st.set_page_config(page_title="Сетка товаров", layout="wide")

# 2. Путь к файлу в репозитории GitHub (рядом с этим скриптом)
BASE_DIR = Path(__file__).parent
FILE_PATH = BASE_DIR / "szwego_products.csv"

# CSS для красивой плитки
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

# 3. Функции загрузки и сохранения
@st.cache_data
def load_data():
    if not FILE_PATH.exists():
        st.error(f"Файл не найден: {FILE_PATH}")
        st.info("Убедись, что szwego_products.csv лежит в той же папке, что и этот скрипт (app.py)")
        return pd.DataFrame()
    try:
        df = pd.read_csv(FILE_PATH, sep=';')
        st.success(f"Загружено {len(df)} товаров из {FILE_PATH}")
        return df
    except Exception as e:
        st.error(f"Ошибка чтения CSV: {e}")
        return pd.DataFrame()

def save_data(df):
    try:
        df.to_csv(FILE_PATH, sep=';', index=False, encoding='utf-8')
        st.success("✅ Файл обновлен!")
        st.rerun()  # Перезагружаем страницу для обновления данных
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")

# 4. Функция удаления
def delete_item(index_to_delete):
    st.session_state['df'] = st.session_state['df'].drop(index_to_delete).reset_index(drop=True)
    save_data(st.session_state['df'])

# 5. Парсинг первой картинки из JSON
def get_first_image(photos_str):
    if pd.isna(photos_str) or photos_str == '':
        return None
    try:
        clean_str = str(photos_str).replace('""', '"')
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]
        images = json.loads(clean_str)
        return images[0] if isinstance(images, list) and len(images) > 0 else None
    except:
        return None

# --- Основная логика ---

st.title("📦 Управление товарами Dior Bags")

# Загружаем данные в сессию
if 'df' not in st.session_state:
    st.session_state['df'] = load_data()

df = st.session_state['df']

if not df.empty:
    st.info(f"Файл: **szwego_products.csv** ({len(df)} товаров)")
    
    # Счетчик для кнопок (чтобы избежать дубликатов ключей)
    st.write("---")
    
    # Колонки
    COLS_COUNT = 6
    
    for i in range(0, len(df), COLS_COUNT):
        cols = st.columns(COLS_COUNT)
        batch = df.iloc[i:i + COLS_COUNT]
        
        for idx, (real_index, row) in enumerate(batch.iterrows()):
            with cols[idx]:
                # Картинка
                img_url = get_first_image(row.get('photos'))
                if img_url:
                    st.image(img_url, use_container_width=True)
                else:
                    st.markdown("🖼️<br>Нет фото", unsafe_allow_html=True)

                # Название
                desc = str(row.get('new_name', 'Без названия'))
                short_desc = (desc[:40] + '..') if len(desc) > 40 else desc
                st.caption(short_desc)

                # Цена
                price = row.get('price', 'Цена ?')
                st.markdown(f"**₽{price}**")

                # Кнопка удаления
                if st.button("❌ Удалить", key=f"del_{real_index}", 
                           on_click=delete_item, args=(real_index,), 
                           type="primary", use_container_width=True):
                    pass  # Callback сработает автоматически

else:
    st.warning("❌ Файл szwego_products.csv не найден или пустой.")
    st.info("""
    **Что нужно сделать:**
    1. Запушь `szwego_products.csv` в корень репозитория GitHub
    2. В Streamlit Cloud укажи этот файл как **Main file path**: `app.py`
    3. Нажми Deploy
    """)

# Инфо о файле внизу
with st.expander("ℹ️ Файловая структура"):
    st.code(f"""
📁 Репозиторий (корень)
├── app.py          ← этот скрипт
├── szwego_products.csv  ← данные (обязательно!)
└── requirements.txt     (опционально)
    """)
