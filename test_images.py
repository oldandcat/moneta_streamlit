#!/usr/bin/env python3
"""
Test script to check image handling for both auctions
"""

from auction_factory import AuctionFactory
import pandas as pd

def test_image_handling():
    factory = AuctionFactory()
    
    print("Available auctions:", factory.available_auctions)
    
    # Test Adalex images
    print("\n=== Testing Adalex Images ===")
    adalex_auction = factory.get_auction("Adalex")
    if adalex_auction:
        # Get first lot from Adalex
        df = adalex_auction.get_filtered_data(limit=1)
        if not df.empty:
            lot_data = df.iloc[0].to_dict()
            lot_data['auction_name'] = 'Adalex'
            print(f"Lot title: {lot_data.get('title')}")
            print(f"Image directory: {lot_data.get('image_dir')}")
            
            images = adalex_auction.get_lot_images(lot_data)
            print(f"Found images: {images}")
    
    # Test Aurora images
    print("\n=== Testing Aurora Images ===")
    aurora_auction = factory.get_auction("Aurora")
    if aurora_auction:
        # Get first lot from Aurora
        df = aurora_auction.get_filtered_data(limit=1)
        if not df.empty:
            lot_data = df.iloc[0].to_dict()
            lot_data['auction_name'] = 'Aurora'
            print(f"Lot title: {lot_data.get('title')}")
            print(f"Image URL: {lot_data.get('image_url')}")
            
            images = aurora_auction.get_lot_images(lot_data)
            print(f"Found images: {images}")

if __name__ == "__main__":
    test_image_handling() 