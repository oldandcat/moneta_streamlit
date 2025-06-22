import streamlit as st
import pandas as pd
from PIL import Image
import os
from pathlib import Path
from auction_factory import AuctionFactory

# Currency symbols for display
currency_symbols = {
    'RUB': '₽',
    'USD': '$',
    'EUR': '€'
}

# Set page configuration
st.set_page_config(
    page_title="Moneta Search",
    page_icon="🪙",
    layout="wide"
)

# Add custom CSS for styling
st.markdown("""
<style>
    .stMarkdown {
        line-height: 1.6 !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🪙 Moneta Search")
    st.markdown("<p style='color: #666; font-size: 0.9em; margin-top: -10px;'>by Gaba-Dubov brothers</p>", unsafe_allow_html=True)
    
    # Initialize auction factory
    factory = AuctionFactory()
    
    if not factory.available_auctions:
        st.error("Базы данных аукционов не найдены. Пожалуйста, добавьте базы данных в соответствующие папки.")
        return
    
    try:
        # --- Выбор аукционов в самом верху ---
        st.sidebar.header("Выбор аукционов")
        selected_auctions = st.sidebar.multiselect(
            "Выберите аукционы для поиска",
            options=factory.available_auctions,
            default=factory.available_auctions
        )
        
        if not selected_auctions:
            st.warning("Пожалуйста, выберите хотя бы один аукцион.")
            return
        
        # Update filter options based on selected auctions
        filter_options = factory.get_combined_filter_options(selected_auctions)
        st.session_state.filter_options = filter_options
        
        # Sidebar filters
        st.sidebar.header("Фильтры")
        
        # Year filter (single year selection)
        st.sidebar.subheader("Год")
        # Update year filter with actual min/max values
        if filter_options["years"]:
            selected_year = st.sidebar.number_input(
                "Введите год", 
                min_value=min(filter_options["years"]), 
                max_value=max(filter_options["years"]), 
                value=st.session_state.get('selected_year', None), 
                placeholder="Например: 1700",
                key='selected_year'
            )
            year = selected_year if selected_year else None
        else:
            year = None
        
        # Update metal and category filters with actual options
        selected_metals = st.sidebar.multiselect("Металл", options=filter_options["metals"], default=st.session_state.get('selected_metals', []), key='selected_metals')
        selected_categories = st.sidebar.multiselect("Тип лота", options=filter_options["categories"], default=st.session_state.get('selected_categories', []), key='selected_categories')
        
        # --- Поиск с выбором области ---
        st.sidebar.subheader("Поиск")
        search_scope = st.sidebar.selectbox(
            "Область поиска",
            options=['title', 'description', 'both'],
            format_func=lambda x: {'title': 'По названию', 'description': 'По описанию', 'both': 'По названию и описанию'}[x],
            key='search_scope'
        )
        search_query = st.sidebar.text_input("Поисковый запрос", placeholder="Введите ключевые слова...", key='search_query')
        
        # Currency selection
        st.sidebar.subheader("Валюта")
        currency = st.sidebar.selectbox("Выберите валюту", options=['RUB', 'USD', 'EUR'], key='currency')
        
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
        sort_by = st.sidebar.selectbox("Сортировать по", options=list(sort_options.keys()), format_func=lambda x: sort_options[x], key='sort_by')
        
        # Pagination
        st.sidebar.subheader("Навигация")
        items_per_page = st.sidebar.selectbox("Лотов на странице", options=[25, 50, 100], index=1, key='items_per_page')
        
        # Get total count for pagination
        total_count = factory.get_combined_total_count(
            selected_auctions=selected_auctions,
            year=year,
            metals=selected_metals,
            categories=selected_categories,
            search_title=search_query if search_scope in ['title', 'both'] else None,
            search_description=search_query if search_scope in ['description', 'both'] else None
        )
        
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        # Page navigation
        col1, col2, col3 = st.sidebar.columns(3)
        with col1:
            if st.button("◀️"):
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 0
                st.session_state.current_page = max(0, st.session_state.current_page - 1)
                st.rerun()
        
        with col2:
            st.write(f"Стр. {st.session_state.get('current_page', 0) + 1}/{total_pages}")
        
        with col3:
            if st.button("▶️"):
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 0
                st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
                st.rerun()
        
        current_page = st.session_state.get('current_page', 0)
        offset = current_page * items_per_page
        
        # Get filtered data
        df = factory.get_combined_data(
            selected_auctions=selected_auctions,
            year=year,
            metals=selected_metals,
            categories=selected_categories,
            search_title=search_query if search_scope in ['title', 'both'] else None,
            search_description=search_query if search_scope in ['description', 'both'] else None,
            currency=currency,
            sort_by=sort_by,
            limit=items_per_page,
            offset=offset
        )
        
        # Display results
        st.subheader(f"Результаты поиска ({total_count} лотов)")
        
        if df.empty:
            st.info("По вашему запросу ничего не найдено. Попробуйте изменить параметры поиска.")
        else:
            # Display lots
            for index, row in df.iterrows():
                with st.container():
                    col1, col2 = st.columns([1.5, 2.5])
                    
                    with col1:
                        # Display images
                        factory.display_lot_images(row.to_dict())
                    
                    with col2:
                        # --- Компактный блок title и цен ---
                        st.markdown(f"<div style='margin-bottom: 0.05em;'><span style='font-size:1.1em; font-weight:bold'>{row['title']}</span></div>", unsafe_allow_html=True)
                        price_block = ""
                        if pd.notna(row.get(f'start_price_{currency.lower()}')) and row.get(f'start_price_{currency.lower()}') > 0:
                            price_block += f"<span style='font-weight:600;'>Стартовая цена:</span> {int(row.get(f'start_price_{currency.lower()}'))} {currency_symbols.get(currency, currency)}"
                        if pd.notna(row.get(f'final_price_{currency.lower()}')) and row.get(f'final_price_{currency.lower()}') > 0:
                            if price_block:
                                price_block += " &nbsp;|&nbsp; "
                            price_block += f"<span style='font-weight:600;'>Финальная цена:</span> {int(row.get(f'final_price_{currency.lower()}'))} {currency_symbols.get(currency, currency)}"
                        st.markdown(f"<div style='margin-bottom: 0.1em;'>{price_block}</div>", unsafe_allow_html=True)
                        
                        # --- Дата закрытия сразу после цен ---
                        if pd.notna(row['close_date']):
                            # Extract only date part (remove time if present)
                            close_date = str(row['close_date']).split()[0]  # Take only the date part
                            st.markdown(f"<div style='margin-bottom:0.05em;'><span style='font-size:0.95em;'><b>Дата закрытия:</b> {close_date}</span></div>", unsafe_allow_html=True)
                        
                        # --- Описание и год ---
                        if pd.notna(row['description']):
                            st.markdown(f"<div style='margin-bottom:0.05em;'><span style='font-size:0.95em;'><b>Описание:</b> {row['description']}</span></div>", unsafe_allow_html=True)
                        if pd.notna(row['year']):
                            st.markdown(f"<span style='margin-right:1em; font-size:0.95em;'><b>Год:</b> {int(row['year'])}</span>", unsafe_allow_html=True)
                        
                        # --- Название аукциона в самом низу ---
                        if pd.notna(row['lot_url']):
                            st.markdown(f"<div style='margin-top:0.15em;'><a href='{row['lot_url']}' style='color:#1a73e8; font-weight:600; text-decoration:none;'>{row['auction_name']}</a></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='margin-top:0.15em;'><span style='color:#1a73e8; font-weight:600;'>{row['auction_name']}</span></div>", unsafe_allow_html=True)
                    
                    st.divider()
        
        # Bottom pagination controls
        if total_pages > 1:
            st.subheader("Навигация по страницам")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("◀️ Первая"):
                    st.session_state.current_page = 0
                    st.rerun()
            
            with col2:
                if st.button("◀️ Назад"):
                    st.session_state.current_page = max(0, st.session_state.current_page - 1)
                    st.rerun()
            
            with col3:
                st.write(f"Страница {current_page + 1} из {total_pages}")
            
            with col4:
                if st.button("Вперед ▶️"):
                    st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
                    st.rerun()
            
            with col5:
                if st.button("Последняя ▶️"):
                    st.session_state.current_page = total_pages - 1
                    st.rerun()
    
    except Exception as e:
        st.error(f"Произошла ошибка: {str(e)}")
    
    finally:
        # Close all database connections
        factory.close_all_connections()

if __name__ == "__main__":
    main() 