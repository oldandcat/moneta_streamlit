from auction_base import AuctionBase
import pandas as pd
from typing import List, Optional, Dict, Any
import requests

class AuroraAuction(AuctionBase):
    """Aurora auction implementation"""
    
    def __init__(self):
        super().__init__("Aurora", "data/aurora/lots.db")
    
    def get_filtered_data(self, year: Optional[int] = None, 
                         metals: Optional[List[str]] = None,
                         categories: Optional[List[str]] = None,
                         search_title: Optional[str] = None,
                         search_description: Optional[str] = None,
                         catalogue_type: Optional[str] = None,
                         catalogue_number: Optional[str] = None,
                         currency: str = 'RUB',
                         sort_by: str = 'date_recent',
                         sort_order: str = 'ASC',
                         limit: Optional[int] = 50,
                         offset: int = 0) -> pd.DataFrame:
        """Get filtered data from Aurora database"""
        conn = self.get_connection()
        if conn is None:
            return pd.DataFrame()
        
        # Base query - use only 'url' field; if only 'lot_url' exists, rename it to 'url'
        query = "SELECT * FROM lots WHERE 1=1"
        params = []
        
        # Catalogue filter has priority - if catalogue is specified, ignore other filters
        if catalogue_type and catalogue_number:
            catalogue_column = f"catalogue_{catalogue_type.lower()}"
            query += f" AND {catalogue_column} = ?"
            params.append(catalogue_number)
        else:
            # Regular filters (only applied if no catalogue filter is active)
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
            
            # Add search filters
            if search_title:
                search_words = self.improve_search_query(search_title)
                if search_words:
                    word_conditions = []
                    word_params = []
                    for word in search_words:
                        word_conditions.append("LOWER(COALESCE(title, '')) LIKE ?")
                        word_params.extend([f'%{word}%'])
                    query += f" AND ({' AND '.join(word_conditions)})"
                    params.extend(word_params)
            
            if search_description:
                search_words = self.improve_search_query(search_description)
                if search_words:
                    word_conditions = []
                    word_params = []
                    for word in search_words:
                        word_conditions.append("LOWER(COALESCE(description, '')) LIKE ?")
                        word_params.extend([f'%{word}%'])
                    query += f" AND ({' AND '.join(word_conditions)})"
                    params.extend(word_params)
        
        # Add pagination only if limit is specified
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        # Execute query
        df = pd.read_sql_query(query, conn, params=params)
        # If 'lot_url' exists and 'url' does not, rename
        if 'lot_url' in df.columns and 'url' not in df.columns:
            df = df.rename(columns={'lot_url': 'url'})
        # If both exist, drop 'lot_url'
        if 'url' in df.columns and 'lot_url' in df.columns:
            df = df.drop(columns=['lot_url'])
        return df
    
    def get_total_count(self, year: Optional[int] = None,
                       metals: Optional[List[str]] = None,
                       categories: Optional[List[str]] = None,
                       search_title: Optional[str] = None,
                       search_description: Optional[str] = None,
                       catalogue_type: Optional[str] = None,
                       catalogue_number: Optional[str] = None) -> int:
        """Get total count for pagination"""
        conn = self.get_connection()
        if conn is None:
            return 0
        
        query = "SELECT COUNT(*) as count FROM lots WHERE 1=1"
        params = []
        
        # Catalogue filter has priority - if catalogue is specified, ignore other filters
        if catalogue_type and catalogue_number:
            catalogue_column = f"catalogue_{catalogue_type.lower()}"
            query += f" AND {catalogue_column} = ?"
            params.append(catalogue_number)
        else:
            # Regular filters (only applied if no catalogue filter is active)
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
            
            # Add search filters
            if search_title:
                search_words = self.improve_search_query(search_title)
                if search_words:
                    word_conditions = []
                    word_params = []
                    for word in search_words:
                        word_conditions.append("LOWER(COALESCE(title, '')) LIKE ?")
                        word_params.extend([f'%{word}%'])
                    query += f" AND ({' AND '.join(word_conditions)})"
                    params.extend(word_params)
            
            if search_description:
                search_words = self.improve_search_query(search_description)
                if search_words:
                    word_conditions = []
                    word_params = []
                    for word in search_words:
                        word_conditions.append("LOWER(COALESCE(description, '')) LIKE ?")
                        word_params.extend([f'%{word}%'])
                    query += f" AND ({' AND '.join(word_conditions)})"
                    params.extend(word_params)
        
        result = pd.read_sql_query(query, conn, params=params)
        return result['count'].iloc[0]
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options"""
        conn = self.get_connection()
        if conn is None:
            return {"metals": [], "years": [], "categories": []}
        
        metals = pd.read_sql_query("SELECT DISTINCT metal FROM lots WHERE metal IS NOT NULL ORDER BY metal", conn)['metal'].tolist()
        years = pd.read_sql_query("SELECT DISTINCT year FROM lots WHERE year IS NOT NULL ORDER BY year", conn)['year'].tolist()
        categories = pd.read_sql_query("SELECT DISTINCT category FROM lots WHERE category IS NOT NULL ORDER BY category", conn)['category'].tolist()
        
        return {
            "metals": metals,
            "years": years,
            "categories": categories
        }
    
    def get_lot_images(self, lot_data: Dict[str, Any]) -> List[str]:
        """Get images for a specific lot from URLs"""
        image_url = lot_data.get('image_url')
        if not image_url:
            return []
        
        # Return the image URL directly for Aurora
        return [image_url]
    
    def get_image_content(self, image_url: str):
        """Get image content from URL"""
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                return None
        except Exception:
            return None 