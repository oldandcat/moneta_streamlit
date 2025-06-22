from auction_base import AuctionBase
import pandas as pd
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

class AdalexAuction(AuctionBase):
    """Adalex auction implementation"""
    
    def __init__(self):
        super().__init__("Adalex", "data/adalex/lots.db")
    
    def get_filtered_data(self, year: Optional[int] = None, 
                         metals: Optional[List[str]] = None,
                         categories: Optional[List[str]] = None,
                         search_title: Optional[str] = None,
                         search_description: Optional[str] = None,
                         currency: str = 'RUB',
                         sort_by: str = 'date_recent',
                         sort_order: str = 'ASC',
                         limit: Optional[int] = 50,
                         offset: int = 0) -> pd.DataFrame:
        """Get filtered data from Adalex database"""
        conn = self.get_connection()
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
        return df
    
    def get_total_count(self, year: Optional[int] = None,
                       metals: Optional[List[str]] = None,
                       categories: Optional[List[str]] = None,
                       search_title: Optional[str] = None,
                       search_description: Optional[str] = None) -> int:
        """Get total count for pagination"""
        conn = self.get_connection()
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
        """Get images for a specific lot from local files"""
        image_dir = lot_data.get('image_dir')
        if not image_dir:
            return []
        
        # Use image_dir from database directly (should be like data/adalex/images/lot_xxx)
        if os.path.isdir(image_dir):
            images = list(Path(image_dir).glob("*.jpg"))
            if images:
                return [str(img) for img in sorted(images)]  # Return all images sorted
        return [] 