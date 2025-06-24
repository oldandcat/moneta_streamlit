from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st
from adalex_auction import AdalexAuction
from aurora_auction import AuroraAuction
from redkie_monety_auction import RedkieMonetyAuction

class AuctionFactory:
    """Factory for managing multiple auctions"""
    
    def __init__(self):
        self.auctions = {
            "Adalex": AdalexAuction(),
            "Aurora": AuroraAuction(),
            "Redkie Monety": RedkieMonetyAuction()
        }
        self.available_auctions = self._get_available_auctions()
    
    def _get_available_auctions(self) -> List[str]:
        """Get list of available auctions (those with existing databases)"""
        available = []
        for name, auction in self.auctions.items():
            if auction.get_connection() is not None:
                available.append(name)
        return available
    
    def get_auction(self, name: str):
        """Get specific auction by name"""
        return self.auctions.get(name)
    
    def get_combined_filter_options(self, selected_auctions: List[str]) -> Dict[str, List[str]]:
        """Get combined filter options from selected auctions"""
        all_metals = set()
        all_years = set()
        all_categories = set()
        
        for auction_name in selected_auctions:
            auction = self.auctions.get(auction_name)
            if auction and auction.get_connection():
                options = auction.get_filter_options()
                all_metals.update(options.get("metals", []))
                all_years.update(options.get("years", []))
                all_categories.update(options.get("categories", []))
        
        return {
            "metals": sorted(list(all_metals)),
            "years": sorted(list(all_years)),
            "categories": sorted(list(all_categories))
        }
    
    def get_combined_data(self, selected_auctions: List[str], 
                         year: Optional[int] = None,
                         metals: Optional[List[str]] = None,
                         categories: Optional[List[str]] = None,
                         search_title: Optional[str] = None,
                         search_description: Optional[str] = None,
                         catalogue_type: Optional[str] = None,
                         catalogue_number: Optional[str] = None,
                         currency: str = 'RUB',
                         sort_by: str = 'date_recent',
                         sort_order: str = 'ASC',
                         limit: int = 50,
                         offset: int = 0) -> pd.DataFrame:
        """Get combined data from selected auctions"""
        all_data = []
        
        for auction_name in selected_auctions:
            auction = self.auctions.get(auction_name)
            if auction and auction.get_connection():
                # Get ALL data from this auction (no pagination, no sorting)
                df = auction.get_filtered_data(
                    year=year,
                    metals=metals,
                    categories=categories,
                    search_title=search_title,
                    search_description=search_description,
                    catalogue_type=catalogue_type,
                    catalogue_number=catalogue_number,
                    currency=currency,
                    limit=None,  # No limit - get all data
                    offset=0     # No offset - start from beginning
                )
                
                if not df.empty:
                    # Reset index to avoid duplicate indices
                    df = df.reset_index(drop=True)
                    # Add auction name column
                    df['auction_name'] = auction_name
                    all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        # Combine all dataframes with ignore_index=True to avoid index conflicts
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Sort combined data
        if sort_by == 'price_high':
            combined_df = combined_df.sort_values(f'final_price_{currency.lower()}', ascending=False)
        elif sort_by == 'price_low':
            combined_df = combined_df.sort_values(f'final_price_{currency.lower()}', ascending=True)
        elif sort_by == 'date_recent':
            combined_df = combined_df.sort_values('close_date', ascending=False)
        elif sort_by == 'date_old':
            combined_df = combined_df.sort_values('close_date', ascending=True)
        elif sort_by == 'year_desc':
            combined_df = combined_df.sort_values('year', ascending=False)
        elif sort_by == 'year_asc':
            combined_df = combined_df.sort_values('year', ascending=True)
        
        # Apply pagination to combined results
        return combined_df.iloc[offset:offset + limit]
    
    def get_combined_total_count(self, selected_auctions: List[str],
                               year: Optional[int] = None,
                               metals: Optional[List[str]] = None,
                               categories: Optional[List[str]] = None,
                               search_title: Optional[str] = None,
                               search_description: Optional[str] = None,
                               catalogue_type: Optional[str] = None,
                               catalogue_number: Optional[str] = None) -> int:
        """Get total count from all selected auctions"""
        total_count = 0
        
        for auction_name in selected_auctions:
            auction = self.auctions.get(auction_name)
            if auction and auction.get_connection():
                count = auction.get_total_count(
                    year=year,
                    metals=metals,
                    categories=categories,
                    search_title=search_title,
                    search_description=search_description,
                    catalogue_type=catalogue_type,
                    catalogue_number=catalogue_number
                )
                total_count += count
        
        return total_count
    
    def get_lot_images(self, lot_data: Dict[str, Any]) -> List[str]:
        """Get images for a specific lot based on auction type"""
        auction_name = lot_data.get('auction_name')
        if not auction_name:
            return []
        
        auction = self.auctions.get(auction_name)
        if auction:
            return auction.get_lot_images(lot_data)
        
        return []
    
    def display_lot_images(self, lot_data: Dict[str, Any]):
        """Display images for a lot based on auction type"""
        auction_name = lot_data.get('auction_name')
        if not auction_name:
            return
        
        auction = self.auctions.get(auction_name)
        if not auction:
            return
        
        if auction_name == "Aurora":
            # For Aurora, use image_url field
            image_url = lot_data.get('image_url')
            if image_url:
                try:
                    st.image(image_url, width=450)
                except Exception as e:
                    st.error(f"Не удалось загрузить изображение: {image_url}")
        elif auction_name == "Redkie Monety":
            # For Redkie Monety, use image_url field
            image_url = lot_data.get('image_url')
            if image_url:
                try:
                    st.image(image_url, width=450)
                except Exception as e:
                    st.error(f"Не удалось загрузить изображение: {image_url}")
        elif auction_name == "Adalex":
            # For Adalex, use local file display with horizontal layout
            images = auction.get_lot_images(lot_data)
            if images:
                # Create columns for horizontal layout
                num_images = min(len(images), 2)  # Show max 2 images
                if num_images == 1:
                    # Single image
                    try:
                        st.image(images[0], width=450)
                    except Exception as e:
                        st.error(f"Ошибка при загрузке изображения: {str(e)}")
                elif num_images == 2:
                    # Two images side by side
                    col1, col2 = st.columns(2)
                    with col1:
                        try:
                            st.image(images[0], width=225)
                        except Exception as e:
                            st.error(f"Ошибка при загрузке изображения: {str(e)}")
                    with col2:
                        try:
                            st.image(images[1], width=225)
                        except Exception as e:
                            st.error(f"Ошибка при загрузке изображения: {str(e)}")
    
    def close_all_connections(self):
        """Close all database connections"""
        for auction in self.auctions.values():
            auction.close_connection()
    
    def get_available_catalogue_numbers(self, selected_auctions: List[str], catalogue_type: str) -> List[str]:
        """Get available catalogue numbers for a specific catalogue type"""
        all_numbers = set()
        
        for auction_name in selected_auctions:
            auction = self.auctions.get(auction_name)
            if auction and auction.get_connection():
                numbers = auction.get_catalogue_numbers(catalogue_type)
                all_numbers.update(numbers)
        
        return sorted(list(all_numbers)) 