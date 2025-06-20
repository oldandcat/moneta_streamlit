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
    db_path = 'data/lots.db'
    if not os.path.exists(db_path):
        return None
    return sqlite3.connect(db_path)

# Function to get filtered data using SQL with pagination
def get_filtered_data(conn, year=None, metals=None, categories=None, search_query=None, currency='RUB', sort_by='lot_number', sort_order='ASC', limit=50, offset=0):
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
        # Use improved search with multiple patterns
        search_patterns = improve_search_query(search_query)
        if search_patterns:
            # Create OR conditions for multiple patterns
            pattern_conditions = []
            pattern_params = []
            
            for pattern in search_patterns:
                pattern_conditions.append("(description LIKE ? OR title LIKE ?)")
                pattern_params.extend([f'%{pattern}%', f'%{pattern}%'])
            
            query += f" AND ({' OR '.join(pattern_conditions)})"
            params.extend(pattern_params)
    
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
        query += " ORDER BY lot_number ASC"
    
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
        # Use improved search with multiple patterns
        search_patterns = improve_search_query(search_query)
        if search_patterns:
            # Create OR conditions for multiple patterns
            pattern_conditions = []
            pattern_params = []
            
            for pattern in search_patterns:
                pattern_conditions.append("(description LIKE ? OR title LIKE ?)")
                pattern_params.extend([f'%{pattern}%', f'%{pattern}%'])
            
            query += f" AND ({' OR '.join(pattern_conditions)})"
            params.extend(pattern_params)
    
    result = pd.read_sql_query(query, conn, params=params)
    return result['count'].iloc[0]

# Function to get search suggestions
def get_search_suggestions(conn, query, limit=10):
    if conn is None or not query:
        return []
    
    sql_query = """
    SELECT DISTINCT description 
    FROM lots 
    WHERE (description LIKE ? OR title LIKE ?)
    AND description IS NOT NULL 
    AND description != ''
    LIMIT ?
    """
    
    result = pd.read_sql_query(sql_query, conn, params=[f'%{query}%', f'%{query}%', limit])
    return result['description'].tolist()

# Function to improve search query
def improve_search_query(query):
    """Improve search query for better matching"""
    if not query:
        return query
    
    # Split query into words
    words = query.lower().split()
    
    # Create multiple search patterns
    patterns = []
    
    # Original query
    patterns.append(query)
    
    # Individual words
    for word in words:
        if len(word) >= 2:  # Only words with 2+ characters
            patterns.append(word)
    
    # Word combinations
    if len(words) >= 2:
        for i in range(len(words)):
            for j in range(i+1, len(words)+1):
                combination = ' '.join(words[i:j])
                if len(combination) >= 3:
                    patterns.append(combination)
    
    return patterns

# Function to find images for a lot
def find_lot_images(lot_number, image_dir=None):
    """Find all images for a lot based on image_dir from database"""
    if not image_dir:
        return []
    
    # Use image_dir from database directly
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
        st.error("Database not found. Please add your database to 'data/lots.db'")
        return
    
    try:
        # Get unique values for filters
        metals = pd.read_sql_query("SELECT DISTINCT metal FROM lots WHERE metal IS NOT NULL ORDER BY metal", conn)['metal'].tolist()
        years = pd.read_sql_query("SELECT DISTINCT year FROM lots WHERE year IS NOT NULL ORDER BY year", conn)['year'].tolist()
        categories = pd.read_sql_query("SELECT DISTINCT category FROM lots WHERE category IS NOT NULL ORDER BY category", conn)['category'].tolist()
        
        # Sidebar filters
        st.sidebar.header("Фильтры")
        currency = st.sidebar.selectbox("Валюта", ['RUB', 'USD', 'EUR'], index=0)
        
        # Year filter (single year selection)
        st.sidebar.subheader("Год")
        selected_year = st.sidebar.selectbox("Выберите год", options=['Все'] + years, index=0)
        year = None if selected_year == 'Все' else selected_year
        
        selected_metals = st.sidebar.multiselect("Металл", options=metals, default=[])
        selected_categories = st.sidebar.multiselect("Тип лота", options=categories, default=[])
        
        # Sorting options
        st.sidebar.subheader("Сортировка")
        sort_options = {
            'lot_number': 'По номеру лота',
            'price_high': 'По цене (дорогие сначала)',
            'price_low': 'По цене (дешевые сначала)',
            'date_recent': 'По дате (новые сначала)',
            'date_old': 'По дате (старые сначала)',
            'year_desc': 'По году (новые сначала)',
            'year_asc': 'По году (старые сначала)'
        }
        sort_by = st.sidebar.selectbox("Сортировать по", options=list(sort_options.keys()), format_func=lambda x: sort_options[x], index=0)
        
        # Search with autocomplete
        st.sidebar.subheader("Поиск")
        search_query = st.sidebar.text_input("Поиск по описанию", key="search_input")
        st.sidebar.caption("💡 Подсказка: можно искать по отдельным словам (руб, спб) или по фразам")
        
        # Show search suggestions
        if search_query and len(search_query) >= 2:
            suggestions = get_search_suggestions(conn, search_query, 5)
            if suggestions:
                st.sidebar.write("**Подсказки:**")
                for suggestion in suggestions:
                    if st.sidebar.button(f"📝 {suggestion[:50]}...", key=f"sugg_{suggestion[:20]}"):
                        st.session_state.search_input = suggestion
                        st.rerun()
        
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
                images = find_lot_images(row.get('lot_number'), row.get('image_dir'))
                image_shown = False
                
                if images:
                    try:
                        # Show images side by side
                        img_cols = st.columns(len(images))
                        for i, image in enumerate(images):
                            with img_cols[i]:
                                st.image(image, use_container_width=True)
                        image_shown = True
                    except Exception as e:
                        st.error(f"Error loading images: {e}")
                if not image_shown:
                    st.write("Изображения отсутствуют")
            
            with col2:
                # Show lot info
                st.subheader(row['title'] if pd.notna(row['title']) else "Untitled Lot")
                
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
                
                if info_text:
                    st.markdown(info_text)
                
                # Show prices
                start_price = row.get(price_cols['start_price'])
                final_price = row.get(price_cols['final_price'])
                
                price_text = ""
                if pd.notna(start_price):
                    # Format price without decimals and add currency symbol
                    if currency == 'RUB':
                        price_text += f"**Старт:** {int(start_price):,} ₽  \n"
                    elif currency == 'USD':
                        price_text += f"**Старт:** {int(start_price):,} $  \n"
                    elif currency == 'EUR':
                        price_text += f"**Старт:** {int(start_price):,} €  \n"
                
                if pd.notna(final_price):
                    if currency == 'RUB':
                        price_text += f"**Итог:** {int(final_price):,} ₽  \n"
                    elif currency == 'USD':
                        price_text += f"**Итог:** {int(final_price):,} $  \n"
                    elif currency == 'EUR':
                        price_text += f"**Итог:** {int(final_price):,} €  \n"
                
                if price_text:
                    st.markdown(price_text)
                
                # Show description
                if pd.notna(row['description']):
                    with st.expander("Подробное описание"):
                        st.write(row['description'])
        
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
                        images = find_lot_images(row.get('lot_number'), row.get('image_dir'))
                        image_shown = False
                        
                        if images:
                            try:
                                # Show images side by side
                                img_cols = st.columns(len(images))
                                for i, image in enumerate(images):
                                    with img_cols[i]:
                                        st.image(image, use_container_width=True)
                                image_shown = True
                            except Exception as e:
                                st.error(f"Error loading images: {e}")
                        if not image_shown:
                            st.write("Изображения отсутствуют")
                    
                    with col2:
                        # Show lot info
                        st.subheader(row['title'] if pd.notna(row['title']) else "Untitled Lot")
                        
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
                        
                        if info_text:
                            st.markdown(info_text)
                        
                        # Show prices
                        start_price = row.get(price_cols['start_price'])
                        final_price = row.get(price_cols['final_price'])
                        
                        price_text = ""
                        if pd.notna(start_price):
                            # Format price without decimals and add currency symbol
                            if currency == 'RUB':
                                price_text += f"**Старт:** {int(start_price):,} ₽  \n"
                            elif currency == 'USD':
                                price_text += f"**Старт:** {int(start_price):,} $  \n"
                            elif currency == 'EUR':
                                price_text += f"**Старт:** {int(start_price):,} €  \n"
                        
                        if pd.notna(final_price):
                            if currency == 'RUB':
                                price_text += f"**Итог:** {int(final_price):,} ₽  \n"
                            elif currency == 'USD':
                                price_text += f"**Итог:** {int(final_price):,} $  \n"
                            elif currency == 'EUR':
                                price_text += f"**Итог:** {int(final_price):,} €  \n"
                        
                        if price_text:
                            st.markdown(price_text)
                        
                        # Show description
                        if pd.notna(row['description']):
                            with st.expander("Подробное описание"):
                                st.write(row['description'])
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 