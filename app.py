import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import os
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="Moneta Auction Viewer",
    page_icon="🪙",
    layout="wide"
)

# Add custom CSS for smaller images
st.markdown("""
<style>
    .stImage > img {
        max-width: 120px !important;
        height: auto !important;
        border-radius: 8px !important;
    }
    .stMarkdown {
        line-height: 1.6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Function to get database connection
def get_db_connection():
    db_path = 'data/adalex/lots.db'
    if not os.path.exists(db_path):
        return None
    return sqlite3.connect(db_path)

# Function to get filtered data using SQL with pagination
def get_filtered_data(conn, year=None, metals=None, categories=None, search_query=None, currency='RUB', sort_by='date_recent', sort_order='ASC', limit=50, offset=0):
    if conn is None:
        return pd.DataFrame()
    
    # Base query
    query = "SELECT * FROM lots WHERE 1=1"
    params = []
    
    # Add filters
    if year is not None:
        query += " AND year = ?"
        params.append(year)
    
    if metals:
        placeholders = ','.join('?' * len(metals))
        query += f" AND metal IN ({placeholders})"
        params.extend(metals)
    
    if categories:
        placeholders = ','.join('?' * len(categories))
        query += f" AND category IN ({placeholders})"
        params.extend(categories)
    
    if search_query:
        # Use improved search with case-insensitive AND logic
        search_words = improve_search_query(search_query)
        if search_words:
            # Create AND conditions for each word in multiple fields
            word_conditions = []
            word_params = []
            
            for word in search_words:
                # Search in both description and title fields, case-insensitive
                word_conditions.append("(LOWER(COALESCE(description, '')) LIKE ? OR LOWER(COALESCE(title, '')) LIKE ?)")
                word_params.extend([f'%{word}%', f'%{word}%'])
            
            # Combine all word conditions with AND
            query += f" AND ({' AND '.join(word_conditions)})"
            params.extend(word_params)
    
    # Add sorting
    if sort_by == 'price_high':
        query += f" ORDER BY final_price_{currency.lower()} DESC"
    elif sort_by == 'price_low':
        query += f" ORDER BY final_price_{currency.lower()} ASC"
    elif sort_by == 'date_recent':
        query += " ORDER BY closed_date DESC"
    elif sort_by == 'date_old':
        query += " ORDER BY closed_date ASC"
    elif sort_by == 'year_desc':
        query += " ORDER BY year DESC"
    elif sort_by == 'year_asc':
        query += " ORDER BY year ASC"
    else:
        query += " ORDER BY year DESC"
    
    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=params)
    return df

# Function to get total count for pagination
def get_total_count(conn, year=None, metals=None, categories=None, search_query=None):
    if conn is None:
        return 0
    
    query = "SELECT COUNT(*) as count FROM lots WHERE 1=1"
    params = []
    
    if year is not None:
        query += " AND year = ?"
        params.append(year)
    
    if metals:
        placeholders = ','.join('?' * len(metals))
        query += f" AND metal IN ({placeholders})"
        params.extend(metals)
    
    if categories:
        placeholders = ','.join('?' * len(categories))
        query += f" AND category IN ({placeholders})"
        params.extend(categories)
    
    if search_query:
        # Use improved search with case-insensitive AND logic
        search_words = improve_search_query(search_query)
        if search_words:
            # Create AND conditions for each word in multiple fields
            word_conditions = []
            word_params = []
            
            for word in search_words:
                # Search in both description and title fields, case-insensitive
                word_conditions.append("(LOWER(COALESCE(description, '')) LIKE ? OR LOWER(COALESCE(title, '')) LIKE ?)")
                word_params.extend([f'%{word}%', f'%{word}%'])
            
            # Combine all word conditions with AND
            query += f" AND ({' AND '.join(word_conditions)})"
            params.extend(word_params)
    
    result = pd.read_sql_query(query, conn, params=params)
    return result['count'].iloc[0]

# Function to improve search query
def improve_search_query(query):
    """Improve search query for better matching"""
    if not query:
        return []
    
    # Split query into words and clean them
    words = [word.strip().lower() for word in query.split() if len(word.strip()) >= 2]
    
    if not words:
        return []
    
    # Return individual words for AND search
    return words

# Function to find images for a lot
def find_lot_images(image_dir=None):
    """Find all images for a lot based on image_dir from database (now full relative path)"""
    if not image_dir:
        return []
    # Use image_dir from database directly (should be like data/adalex/images/lot_xxx)
    if os.path.isdir(image_dir):
        images = list(Path(image_dir).glob("*.jpg"))
        if images:
            return [str(img) for img in sorted(images)]  # Return all images sorted
    return []

def main():
    st.title("🪙 Moneta Auction Viewer")
    
    # Get database connection
    conn = get_db_connection()
    if conn is None:
        st.error("Database not found. Please add your database to 'data/adalex/lots.db'")
        return
    
    try:
        # Get unique values for filters
        metals = pd.read_sql_query("SELECT DISTINCT metal FROM lots WHERE metal IS NOT NULL ORDER BY metal", conn)['metal'].tolist()
        years = pd.read_sql_query("SELECT DISTINCT year FROM lots WHERE year IS NOT NULL ORDER BY year", conn)['year'].tolist()
        categories = pd.read_sql_query("SELECT DISTINCT category FROM lots WHERE category IS NOT NULL ORDER BY category", conn)['category'].tolist()
        
        # Sidebar filters
        st.sidebar.header("Фильтры")
        
        # Year filter (single year selection)
        st.sidebar.subheader("Год")
        selected_year = st.sidebar.number_input("Введите год", min_value=min(years), max_value=max(years), value=None, placeholder="Например: 1700")
        year = selected_year if selected_year else None
        
        selected_metals = st.sidebar.multiselect("Металл", options=metals, default=[])
        selected_categories = st.sidebar.multiselect("Тип лота", options=categories, default=[])
        
        # Sorting options
        st.sidebar.subheader("Сортировка")
        sort_options = {
            'date_recent': 'По дате (новые сначала)',
            'date_old': 'По дате (старые сначала)',
            'price_high': 'По цене (дорогие сначала)',
            'price_low': 'По цене (дешевые сначала)',
            'year_desc': 'По году (новые сначала)',
            'year_asc': 'По году (старые сначала)'
        }
        sort_by = st.sidebar.selectbox("Сортировать по", options=list(sort_options.keys()), format_func=lambda x: sort_options[x], index=0)
        
        # Search with autocomplete
        st.sidebar.subheader("Поиск")
        search_query = st.sidebar.text_input("Поиск по описанию", key="search_input")
        st.sidebar.caption("💡 Подсказка: можно искать по нескольким словам (серебро талер). Поиск без учета регистра.")
        
        # Display settings (separated from filters)
        st.sidebar.markdown("---")
        st.sidebar.subheader("💰 Настройки отображения")
        currency = st.sidebar.selectbox("Валюта цен", ['RUB', 'USD', 'EUR'], index=0)
        
        # Check if any filters are applied
        filters_applied = (year is not None or selected_metals or selected_categories or search_query)
        
        if not filters_applied:
            st.info("Примените хотя бы один фильтр для просмотра результатов.")
            st.write("Доступные фильтры:")
            st.write(f"- Годы: {min(years)} - {max(years)}")
            st.write(f"- Металлы: {', '.join(metals[:10])}{'...' if len(metals) > 10 else ''}")
            st.write(f"- Типы: {', '.join(categories)}")
            return
        
        # Get total count for pagination
        total_count = get_total_count(conn, year, selected_metals, selected_categories, search_query)
        
        if total_count == 0:
            st.info("Лоты, соответствующие выбранным фильтрам, не найдены.")
            return
        
        # Pagination
        items_per_page = 50
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        # Get filtered data
        df = get_filtered_data(conn, year, selected_metals, selected_categories, search_query, currency, sort_by, limit=items_per_page, offset=0)
        
        # Show total count and current page info
        st.write(f"Найдено {total_count} лотов (показано {len(df)} из {total_count})")
        
        # Get price columns
        price_cols = {
            'start_price': f'start_price_{currency.lower()}',
            'final_price': f'final_price_{currency.lower()}'
        }
        
        # Show lots as cards in a single column layout
        for idx, row in df.iterrows():
            st.markdown("---")
            
            # Create two columns: images on left, info on right
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Show images if available
                images = find_lot_images(row.get('image_dir'))
                image_shown = False
                
                if images:
                    try:
                        # Show images side by side
                        img_cols = st.columns(len(images))
                        for i, image in enumerate(images):
                            with img_cols[i]:
                                st.image(image, use_column_width=True)
                        image_shown = True
                    except Exception as e:
                        st.error(f"Error loading images: {e}")
                if not image_shown:
                    st.write("Изображения отсутствуют")
            
            with col2:
                # Show lot info
                st.subheader(row['title'] if pd.notna(row['title']) else "Untitled Lot")
                
                # Create two columns for info and description
                info_col, desc_col = st.columns([1, 1])
                
                with info_col:
                    # Show basic info
                    info_text = ""
                    if pd.notna(row['category']):
                        info_text += f"**Тип:** {row['category']}  \n"
                    if pd.notna(row['year']):
                        info_text += f"**Год:** {row['year']}  \n"
                    if pd.notna(row['metal']):
                        info_text += f"**Металл:** {row['metal']}  \n"
                    if pd.notna(row['closed_date']):
                        info_text += f"**Дата закрытия:** {row['closed_date']}  \n"
                    if pd.notna(row['lot_url']):
                        info_text += f"**Аукцион:** [Adalex]({row['lot_url']})  \n"
                    
                    if info_text:
                        st.markdown(info_text)
                    
                    # Show prices (final price first, then start price)
                    start_price = row.get(price_cols['start_price'])
                    final_price = row.get(price_cols['final_price'])
                    
                    price_text = ""
                    if pd.notna(final_price):
                        if currency == 'RUB':
                            price_text += f"**Итог:** {int(final_price):,} ₽  \n"
                        elif currency == 'USD':
                            price_text += f"**Итог:** {int(final_price):,} $  \n"
                        elif currency == 'EUR':
                            price_text += f"**Итог:** {int(final_price):,} €  \n"
                    
                    if pd.notna(start_price):
                        if currency == 'RUB':
                            price_text += f"**Старт:** {int(start_price):,} ₽  \n"
                        elif currency == 'USD':
                            price_text += f"**Старт:** {int(start_price):,} $  \n"
                        elif currency == 'EUR':
                            price_text += f"**Старт:** {int(start_price):,} €  \n"
                    
                    if price_text:
                        st.markdown(price_text)
                
                with desc_col:
                    # Show description
                    if pd.notna(row['description']):
                        desc = row['description']
                        # If description is short (less than 200 characters), show it directly
                        if len(desc) < 200:
                            st.markdown(f"**Описание:** {desc}")
                        else:
                            # If description is long, show it in an expander
                            with st.expander("Подробное описание"):
                                st.write(desc)
        
        # Pagination at the bottom
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox(f"Страница (1-{total_pages})", range(1, total_pages + 1), index=0)
            
            # If page changed, reload data
            if page > 1:
                offset = (page - 1) * items_per_page
                df = get_filtered_data(conn, year, selected_metals, selected_categories, search_query, currency, sort_by, limit=items_per_page, offset=offset)
                
                # Show lots for current page
                for idx, row in df.iterrows():
                    st.markdown("---")
                    
                    # Create two columns: images on left, info on right
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Show images if available
                        images = find_lot_images(row.get('image_dir'))
                        image_shown = False
                        
                        if images:
                            try:
                                # Show images side by side
                                img_cols = st.columns(len(images))
                                for i, image in enumerate(images):
                                    with img_cols[i]:
                                        st.image(image, use_column_width=True)
                                image_shown = True
                            except Exception as e:
                                st.error(f"Error loading images: {e}")
                        if not image_shown:
                            st.write("Изображения отсутствуют")
                    
                    with col2:
                        # Show lot info
                        st.subheader(row['title'] if pd.notna(row['title']) else "Untitled Lot")
                        
                        # Create two columns for info and description
                        info_col, desc_col = st.columns([1, 1])
                        
                        with info_col:
                            # Show basic info
                            info_text = ""
                            if pd.notna(row['category']):
                                info_text += f"**Тип:** {row['category']}  \n"
                            if pd.notna(row['year']):
                                info_text += f"**Год:** {row['year']}  \n"
                            if pd.notna(row['metal']):
                                info_text += f"**Металл:** {row['metal']}  \n"
                            if pd.notna(row['closed_date']):
                                info_text += f"**Дата закрытия:** {row['closed_date']}  \n"
                            if pd.notna(row['lot_url']):
                                info_text += f"**Аукцион:** [Adalex]({row['lot_url']})  \n"
                            
                            if info_text:
                                st.markdown(info_text)
                            
                            # Show prices (final price first, then start price)
                            start_price = row.get(price_cols['start_price'])
                            final_price = row.get(price_cols['final_price'])
                            
                            price_text = ""
                            if pd.notna(final_price):
                                if currency == 'RUB':
                                    price_text += f"**Итог:** {int(final_price):,} ₽  \n"
                                elif currency == 'USD':
                                    price_text += f"**Итог:** {int(final_price):,} $  \n"
                                elif currency == 'EUR':
                                    price_text += f"**Итог:** {int(final_price):,} €  \n"
                            
                            if pd.notna(start_price):
                                if currency == 'RUB':
                                    price_text += f"**Старт:** {int(start_price):,} ₽  \n"
                                elif currency == 'USD':
                                    price_text += f"**Старт:** {int(start_price):,} $  \n"
                                elif currency == 'EUR':
                                    price_text += f"**Старт:** {int(start_price):,} €  \n"
                            
                            if price_text:
                                st.markdown(price_text)
                        
                        with desc_col:
                            # Show description
                            if pd.notna(row['description']):
                                desc = row['description']
                                # If description is short (less than 200 characters), show it directly
                                if len(desc) < 200:
                                    st.markdown(f"**Описание:** {desc}")
                                else:
                                    # If description is long, show it in an expander
                                    with st.expander("Подробное описание"):
                                        st.write(desc)
    finally:
        conn.close()

if __name__ == "__main__":
    main() 