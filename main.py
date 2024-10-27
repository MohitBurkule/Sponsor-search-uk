import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io
import folium
from streamlit_folium import st_folium


# Step 1: Scrape the CSV URL from the gov.uk website
@st.cache_data(show_spinner=False)
def get_csv_url():
    url = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Look for the CSV download link
    for link in soup.find_all("a"):
        if "csv" in link.get("href", ""):
            csv_url = link.get("href")
            return csv_url, time.strftime('%Y-%m-%d %H:%M:%S')


# Step 2: Download CSV file separately with retries and cache it
@st.cache_data(show_spinner=True)
def download_csv_file(csv_url, retries=5, delay=2):
    attempt = 0
    while attempt < retries:
        try:
            # Try to download the CSV file
            response = requests.get(csv_url)
            response.raise_for_status()  # Check for HTTP errors
            return response.content
        except Exception as e:
            st.warning(f"Error downloading CSV: {e}. Retrying {retries - attempt - 1} more times...")
            attempt += 1
            time.sleep(delay)

    # If all attempts fail
    st.error("Failed to download the CSV after multiple attempts.")
    return None


# Step 3: Load the CSV file into a Pandas DataFrame
@st.cache_data(show_spinner=False)
def load_sponsor_data(csv_content):
    try:
        # Use io.StringIO to convert byte content into an in-memory text stream
        df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None


# Step 4: Plot UK map with sponsors
def plot_map(data):

    #write comming soon in syle, center and color center align
    text= """
    <div style=" padding: 10px; border-radius: 10px;">
    <h3 style="color: #ff6347; text-align: center;"
    >Coming Soon...</h3>
    <p style="color: #000000;">This feature is under development.</p>
    </div>
    """
    st.write(text, unsafe_allow_html=True)

    return
    uk_map = folium.Map(location=[54.0, -2.0], zoom_start=6)

    # Group by Town/City to aggregate sponsors
    grouped_data = data.groupby('Town/City').size().reset_index(name='Count')

    for i, row in grouped_data.iterrows():
        city = row['Town/City']
        count = row['Count']

        # Add clickable markers
        folium.Marker(
            location=[row['latitude'], row['longitude']],  # Placeholder for actual lat/long
            popup=f"{city}: {count} sponsors",
            tooltip=f"{city} ({count} sponsors)"
        ).add_to(uk_map)

    return uk_map


# Step 5: Set up Streamlit app
def main():
    st.title("UK Licensed Sponsors Search")

    # Scrape the CSV URL
    csv_info = get_csv_url()
    if csv_info:
        csv_url, cache_time = csv_info
        st.write(f"CSV URL: {csv_url} (Downloaded at: {cache_time})")

        # Download the CSV file content
        csv_content = download_csv_file(csv_url)

        if csv_content:
            # Load sponsor data from the downloaded content
            df = load_sponsor_data(csv_content)

            if df is not None:
                # Set table display size slightly bigger
                st.markdown("<style> .dataframe { font-size: 14px; } </style>", unsafe_allow_html=True)

                # Step 6: Search bar and filtering
                st.sidebar.header("Search Filters")

                # Search by Organization Name
                sponsor_name = st.sidebar.text_input("Organisation Name")

                # Search by location
                location = st.sidebar.text_input("Town/City")

                # Filter by Route column
                route = st.sidebar.selectbox("Select Route", ['All'] + df['Route'].unique().tolist())

                # Search by any column
                column_1 = st.sidebar.selectbox("Select first column", df.columns)
                search_value_1 = st.sidebar.text_input("Search first column")

                column_2 = st.sidebar.selectbox("Select second column", df.columns)
                search_value_2 = st.sidebar.text_input("Search second column")

                # Filter the dataframe based on user inputs
                filtered_df = df.copy()

                if sponsor_name:
                    filtered_df = filtered_df[
                        filtered_df['Organisation Name'].str.contains(sponsor_name, case=False, na=False)]

                if location:
                    filtered_df = filtered_df[filtered_df['Town/City'].str.contains(location, case=False, na=False)]

                if route != 'All':
                    filtered_df = filtered_df[filtered_df['Route'] == route]

                if search_value_1:
                    filtered_df = filtered_df[
                        filtered_df[column_1].astype(str).str.contains(search_value_1, case=False, na=False)]

                if search_value_2:
                    filtered_df = filtered_df[
                        filtered_df[column_2].astype(str).str.contains(search_value_2, case=False, na=False)]

                # Display the filtered dataframe
                st.dataframe(filtered_df)

                # Show map with sponsors per city
                st.header("Sponsor Locations on UK Map")
                sponsor_map = plot_map(filtered_df)
                # st_folium(sponsor_map, width=700, height=500)

        else:
            st.error("Could not download the CSV file.")
    else:
        st.error("Could not find the CSV file URL.")


if __name__ == "__main__":
    main()
