# Moneta Streamlit

A web application for displaying and analyzing antique coin auction results.

## Features

- View all auction lots (coins)
- Filter by year, metal, and price
- Search by description with autocomplete
- View coin images
- Display detailed information about each lot

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Project Structure

- `app.py` - Main Streamlit application
- `data/` - Directory for SQLite database and images
- `requirements.txt` - Project dependencies 