import os
import json
import tempfile

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Сетка товаров", layout="wide")

DATA_DIR = "data"
DEFAULT_FILE = "szwego_products.csv"

# ---------- Картинки ----------
BASE_OPTIM_PARAMS = "imageMogr2/auto-orient/thumbnail/!320x320r/quality/80/format/jpg"

def to_thumb(url: str) -> str:
    if not url or pd.isna(url):
        return ""
    if "imageMogr2" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{BASE_OPTIM_PARAMS}"

def get_first_image(photos_str):
    if pd.isna(photos_str) or photos_str == '':
        return ""
    try:
        clean_str = str(photos_str).replace('""', '"')
        if clean_str.startswith('"') and clean_str.endswith('"'):
            clean_str = clean_str[1:-1]
        images = json.loads(clean_str)
        return images[0] if isinstance(images, list) and len(images) > 0 else ""
    except:
        return ""

# ---------- Стили ----------
st.markdown("""
<style>
div[data-testid="column"] {
    background-color: #1e1f23;
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
.one-line-desc {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 0.85rem;
    color: rgba(250, 250, 250, 0.8);
    margin-top: 4px;
}
.card-selected {
    border: 2px solid #ff4b4b;
    box-shadow: 0 0 6px rgba(255, 75, 75, 0.6);
}
.fixed-delete-bar {
    position: fixed;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    background-color: rgba(32, 33, 36, 0.98);
    padding: 8px 16px;
    border-radius: 999px;
    border: 1px solid #444;
    z-index: 9999;
}
.fixed-delete-bar-inner {
    display: flex;
    align-items: center;
    gap: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Файлы ----------
def get_file_path():
    st.sidebar.title("📁 Настройки файла")
    upload_method = st.sidebar.radio("Способ загрузки:", ["Выбрать из репозитория", "Загрузить из компьютера"])

    if upload_method == "Выбрать из репозитория":
        if not os.path.isdir(DATA_DIR):
            st.sidebar.error(f"Папка {DATA_DIR} не найдена.")
            return None
        csv_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]
        if not csv_files:
            st.sidebar.error("В папке data нет CSV файлов.")
            return None
        default_index = csv_files.index(DEFAULT_FILE) if DEFAULT_FILE in csv_files else 0
        selected = st.sidebar.selectbox("Файл из GitHub:", csv_files, index=default_index)
        return os.path.join(DATA_DIR, selected)
    else:
        uploaded_file = st.sidebar.file_uploader("Загрузите CSV:", type=["csv"])
        if uploaded_file is None:
            return None
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"Загружен: {uploaded_file.name}")
        return temp_path

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()
    df = pd.read_csv(file_path, sep=';')

    df['thumb_url'] = df['photos'].apply(get_first_image).apply(to_thumb)
    df['display_desc'] = df['description'].fillna('Без описания').astype(str).str.strip()
    mask_nan = df['display_desc'].str.lower().isin(['nan', 'nan.', 'none', ''])
    df.loc[mask_nan, 'display_desc'] = 'Без описания'
    if 'is_deleted' not in df.columns:
        df['is_deleted'] = False
    return df

def save_to_csv(df_full, file_path):
    df_save = df_full[df_full['is_deleted'] == False].drop(
        columns=['thumb_url', 'display_desc', 'is_deleted'],
        errors='ignore'
    )
    df_save.to_csv(file_path, sep=';', index=False, encoding='utf-8')
    st.toast("✅ CSV обновлен на диске!", icon="✅")

def download_data(df_full, filename):
    df_save = df_full[df_full['is_deleted'] == False].drop(
        columns=['thumb_url', 'display_desc', 'is_deleted'],
        errors='ignore'
    )
    csv = df_save.to_csv(sep=';', index=False, encoding='utf-8')
    st.download_button(
        "💾 Скачать updated CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )

# ---------- Основная логика ----------
file_path = get_file_path()

if file_path:
    st.title("📦 Управление товарами")
    st.info(f"Файл: `{os.path.basename(file_path)}`")

    if 'df' not in st.session_state or st.session_state.get('current_file') != file_path:
        st.session_state['df'] = load_data(file_path)
        st.session_state['current_file'] = file_path
        st.session_state['selected_rows'] = set()
        st.session_state['page'] = 1

    df = st.session_state['df']
    df_filtered = df[~df['is_deleted']]

    if df_filtered.empty:
        st.warning("Файл пуст или все товары помечены как удалённые.")
        filename = os.path.basename(file_path)
        download_data(df, f"updated_{filename}")
    else:
        st.write(f"Отображается товаров: **{len(df_filtered)}** из **{len(df)}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Обновить CSV на диске", use_container_width=True):
                save_to_csv(df, file_path)
                st.session_state['df'] = load_data(file_path)
                st.session_state['selected_rows'] = set()
                st.session_state['page'] = 1
                st.rerun()
        with col2:
            filename = os.path.basename(file_path)
            download_data(df, f"updated_{filename}")

        # --------- пагинация счётчиком ----------
        PAGE_SIZE = 60
        total_pages = (len(df_filtered) + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = st.session_state.get('page', 1)
        current_page = max(1, min(current_page, total_pages))

        page = st.number_input(
            "Страница",
            min_value=1,
            max_value=max(1, total_pages),
            value=current_page,
            step=1
        )
        if page != current_page:
            st.session_state['page'] = int(page)
            st.rerun()
        current_page = st.session_state['page']

        start_idx = (current_page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, len(df_filtered))
        page_batch = df_filtered.iloc[start_idx:end_idx]
        st.caption(f"Страница {current_page} из {total_pages} • товары {start_idx + 1}–{end_idx}")

        COLS_COUNT = 6
        page_batch = page_batch.copy()

        for i in range(0, len(page_batch), COLS_COUNT):
            cols = st.columns(COLS_COUNT)
            sub_batch = page_batch.iloc[i: i + COLS_COUNT]

            for idx, (row_idx, row) in enumerate(sub_batch.iterrows()):
                real_idx = row_idx
                selected = real_idx in st.session_state['selected_rows']

                with cols[idx]:
                    card_class = "card-selected" if selected else ""
                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                    if row.get('thumb_url'):
                        st.image(row['thumb_url'], use_container_width=True)
                    else:
                        st.text("Нет фото")

                    desc = row.get('display_desc', 'Без описания')
                    st.markdown(
                        f'<span class="one-line-desc">{desc}</span>',
                        unsafe_allow_html=True
                    )

                    price = row.get('price', '')
                    st.write(f"**{price}**")

                    new_checked = st.checkbox(
                        "Выбрать",
                        key=f"select_{real_idx}",
                        value=selected
                    )
                    if new_checked and not selected:
                        st.session_state['selected_rows'].add(real_idx)
                    if not new_checked and selected:
                        st.session_state['selected_rows'].discard(real_idx)

                    st.markdown("</div>", unsafe_allow_html=True)

        # --------- фиксированная нижняя панель ----------
        selected_count = len(st.session_state['selected_rows'])

        st.markdown(
            f"""
<div class="fixed-delete-bar">
  <div class="fixed-delete-bar-inner">
    <span>Выбрано: {selected_count}</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # сама кнопка (обычный st.button, но логика удаления)
        if selected_count > 0:
            if st.button("🗑️ Удалить выбранные", key="delete_selected"):
                for real_idx in list(st.session_state['selected_rows']):
                    if real_idx in df.index:
                        df.loc[real_idx, 'is_deleted'] = True
                st.session_state['df'] = df
                st.session_state['selected_rows'] = set()
                st.toast("Удалены выбранные товары", icon="🗑️")
                st.rerun()
else:
    st.title("📦 Управление товарами")
    st.warning("Выберите файл для начала работы.")
