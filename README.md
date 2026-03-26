# UK Licensed Sponsors Search

A Streamlit application designed to search, filter, and map UK companies that are licensed to sponsor workers. The app scrapes the latest register of licensed sponsors CSV from the official UK government website, loads it into an interactive dataframe, and provides geographical visualization using Open-Meteo API and Folium.

## Features

- **Automatic Data Retrieval**: Fetches the latest licensed sponsor CSV directly from the gov.uk website.
- **Interactive Search & Filtering**: Filter sponsors by organization name, city, route, or any other specific column.
- **Company Insights**: Integrates with the UK Companies House advanced search to provide company information links and Standard Industrial Classification (SIC) codes for selected companies.
- **Geographical Mapping**: Maps sponsor locations across the UK, grouping them by city using Folium and Geocoding via the Open-Meteo API.

## Prerequisites

- Python 3.7 or higher.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the Streamlit application:
   ```bash
   streamlit run main.py
   ```

2. Open your web browser and navigate to the local URL provided by Streamlit (typically `http://localhost:8501`).

## Technologies Used

- **Streamlit**: For the interactive web interface.
- **Pandas**: For data manipulation and processing.
- **Requests & BeautifulSoup**: For web scraping and downloading the CSV file.
- **Folium & Streamlit-Folium**: For rendering interactive maps.
- **Open-Meteo API**: For geocoding city names to latitude and longitude coordinates.
