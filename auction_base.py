from abc import ABC, abstractmethod
import sqlite3
import pandas as pd
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import requests
from PIL import Image
import io

class AuctionBase(ABC):
    """Abstract base class for auction data handling"""
    
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path
        self.conn = None
    
    def get_connection(self) -> Optional[sqlite3.Connection]:
        """Get database connection"""
        if not os.path.exists(self.db_path):
            return None
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    @abstractmethod
    def get_filtered_data(self, year: Optional[int] = None, 
                         metals: Optional[List[str]] = None,
                         categories: Optional[List[str]] = None,
                         search_title: Optional[str] = None,
                         search_description: Optional[str] = None,
                         currency: str = 'RUB',
                         sort_by: str = 'date_recent',
                         sort_order: str = 'ASC',
                         limit: int = 50,
                         offset: int = 0) -> pd.DataFrame:
        """Get filtered data from auction database"""
        pass
    
    @abstractmethod
    def get_total_count(self, year: Optional[int] = None,
                       metals: Optional[List[str]] = None,
                       categories: Optional[List[str]] = None,
                       search_title: Optional[str] = None,
                       search_description: Optional[str] = None) -> int:
        """Get total count for pagination"""
        pass
    
    @abstractmethod
    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options (metals, years, categories)"""
        pass
    
    @abstractmethod
    def get_lot_images(self, lot_data: Dict[str, Any]) -> List[str]:
        """Get images for a specific lot"""
        pass
    
    def close_connection(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def improve_search_query(self, query: str) -> List[str]:
        """Improve search query for better matching"""
        if not query:
            return []
        
        # Split query into words and clean them
        words = [word.strip().lower() for word in query.split() if len(word.strip()) >= 2]
        
        if not words:
            return []
        
        # Return individual words for AND search
        return words 