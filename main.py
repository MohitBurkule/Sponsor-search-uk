import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io
import folium
from streamlit_folium import st_folium
from urllib.parse import quote  # For URL encoding
import re

st.set_page_config(layout="wide",
                   page_title="UK sponsor search",
                    page_icon=":uk:",
)

# Step 1: Scrape the CSV URL from the gov.uk website
@st.cache_data(show_spinner=False)
def get_csv_url():
    url = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
    response = requests.get(url, timeout=10)
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
            response = requests.get(csv_url, timeout=10)
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

        # Add a new column with URL for company search
        df['Company Info URL'] = df['Organisation Name'].apply(
            lambda name: f"https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?"
                         f"companyNameIncludes={quote(name)}"
        )

        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None


@st.cache_data(show_spinner=False)
def get_coordinates(city_name):
    """
    Geocodes a given city name to return latitude and longitude.
    Uses Open-Meteo API for faster and rate-limit friendly lookups.
    """
    if not city_name or pd.isna(city_name):
        return None, None

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city_name)}&count=1&format=json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            # Ensure it is somewhat within UK bounds or we could just take the first match
            # But just returning the first match is fine for now
            return result["latitude"], result["longitude"]
    except Exception as e:
        print(f"Error geocoding {city_name}: {e}")

    # Don't cache failed responses permanently if we had an easier way, but cache nulls to avoid spamming the API on bad cities
    return None, None

# Step 4: Plot UK map with sponsors
def plot_map(data):
    if data is None or data.empty:
        st.warning("No data available to plot on the map.")
        return None

    uk_map = folium.Map(location=[54.0, -2.0], zoom_start=6)

    # Group by Town/City to aggregate sponsors and also collect the organisation names
    grouped_data = data.groupby('Town/City').agg(
        Count=('Organisation Name', 'size'),
        Companies=('Organisation Name', lambda x: list(x))
    ).reset_index()

    # Sort by count descending
    grouped_data = grouped_data.sort_values(by='Count', ascending=False)

    # If there are many cities, limit to top 50 to avoid rate limits
    if len(grouped_data) > 50:
        st.info("Showing map for the top 50 cities. Use filters to narrow down the results.")
        grouped_data = grouped_data.head(50)

    # Fetch coordinates and plot markers
    for _, row in grouped_data.iterrows():
        city = row['Town/City']
        count = row['Count']
        companies = row['Companies']

        lat, lon = get_coordinates(city)
        if lat is not None and lon is not None:
            # Format the companies list into a string
            companies_display = "<br>".join(f"• {c}" for c in companies[:10])
            if count > 10:
                companies_display += f"<br><i>...and {count - 10} more</i>"

            popup_html = f"<b>{city} ({count} sponsors)</b><br>{companies_display}"

            tooltip_text = f"{city} ({count} sponsors)"
            if count <= 5:
                tooltip_text += f": {', '.join(companies[:5])}"

            # Add clickable markers
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip_text
            ).add_to(uk_map)

    return uk_map


@st.cache_data(show_spinner=False)
def get_company_info(company_actual_url):
    """
    Scrapes the provided company actual URL for key company information.

    :param company_actual_url: The URL to scrape for company information.
    :return: A dictionary containing the company information if found; otherwise, None.
    """
    info = {}
    try:
        response = requests.get(company_actual_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        def get_text_or_na(element):
            return element.text.strip() if element else 'N/A'

        number_element = soup.find('p', id='company-number')
        if number_element:
            number_strong = number_element.find('strong')
            if number_strong:
                info['Company number'] = number_strong.text.strip()
            else:
                info['Company number'] = number_element.text.replace('Company number', '').strip()

        # Address
        address_element = soup.find('dd', class_='text data')
        if address_element:
            info['Registered office address'] = get_text_or_na(address_element)

        # Company status
        status_element = soup.find('dd', class_='text data', id='company-status')
        if not status_element:
            dts = soup.find_all('dt')
            for dt in dts:
                if 'Company status' in dt.text:
                    status_element = dt.find_next_sibling('dd')
        if status_element:
            info['Company status'] = get_text_or_na(status_element)

        # Company type
        type_element = soup.find('dd', class_='text data', id='company-type')
        if not type_element:
            dts = soup.find_all('dt')
            for dt in dts:
                if 'Company type' in dt.text:
                    type_element = dt.find_next_sibling('dd')
        if type_element:
            info['Company type'] = get_text_or_na(type_element)

        # Incorporated on
        inc_element = soup.find('dd', class_='text data', id='company-creation-date')
        if not inc_element:
            dts = soup.find_all('dt')
            for dt in dts:
                if 'Incorporated on' in dt.text:
                    inc_element = dt.find_next_sibling('dd')
        if inc_element:
            info['Incorporated on'] = get_text_or_na(inc_element)

        return info
    except Exception as e:
        print(f"Error extracting company info: {e}")
        return None

@st.cache_data(show_spinner=False)
def get_sic_codes(company_info_url):
    """
    Scrapes the provided company information URL for SIC codes
    (spans with IDs sic0 to sic10).

    :param company_info_url: The URL to scrape for company SIC codes.
    :return: A dictionary containing the SIC codes if found; otherwise, an empty dictionary.
    """
    sic_codes = {}

    try:
        # Send a request to the company info URL
        response = requests.get(company_info_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.content, "html.parser")

        # Loop through sic0 to sic10
        for i in range(11):
            sic_id = f'sic{i}'
            span = soup.find('span', id=sic_id)
            if span:
                sic_codes[sic_id] = span.text.strip()  # Add to dictionary with the ID as the key

    except Exception as e:
        print(f"Error scraping SIC codes: {e}")

    return sic_codes  # Return the dictionary of SIC codes


def get_company_link(company_name):
    """
    Scrapes the provided company information URL for the exact company name
    and returns the corresponding link if found.

    :param company_name: The name of the company to search for.
    :return: The link to the company's information if found; otherwise, None.
    """
    base_url = "https://find-and-update.company-information.service.gov.uk"
    # We use the search endpoint instead of the advanced search to get better results
    search_url = f"https://find-and-update.company-information.service.gov.uk/search/companies?q={quote(company_name)}"

    def normalize_name(name):
        name = name.lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '', name)
        return name

    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.content, "html.parser")

        text_to_search = normalize_name(company_name)
        text_to_search_ltd = text_to_search.replace("limited", "ltd")
        text_to_search_limited = text_to_search.replace("ltd", "limited")

        # 1. Try exact match
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if href.startswith("/company/"):
                link_text = link.text.strip()
                link_text_norm = normalize_name(link_text)

                link_text_norm_ltd = link_text_norm.replace("limited", "ltd")
                link_text_norm_limited = link_text_norm.replace("ltd", "limited")

                if text_to_search_ltd == link_text_norm_ltd or text_to_search_limited == link_text_norm_limited:
                    return base_url + href

        # 2. Try prefix match
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if href.startswith("/company/"):
                link_text = link.text.strip()
                link_text_norm = normalize_name(link_text)

                link_text_norm_ltd = link_text_norm.replace("limited", "ltd")

                if link_text_norm_ltd.startswith(text_to_search_ltd) or text_to_search_ltd.startswith(link_text_norm_ltd):
                    return base_url + href

        # 3. Just return the first company result
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if href.startswith("/company/"):
                return base_url + href

    except Exception as e:
        print(f"Error scraping company link: {e}")

    return None  # Return None if the company name is not found

# Step 5: Set up Streamlit app
def main():
    st.title("UK Licensed Sponsors Search")

    # Scrape the CSV URL
    csv_info = get_csv_url()
    if csv_info:
        csv_url, cache_time = csv_info
        st.write(f"CSV URL: {csv_url} (Downloaded at: {cache_time})")
        st.write("Select companies below to view their company information.")
        # Download the CSV file content
        csv_content = download_csv_file(csv_url)

        if csv_content:
            # Load sponsor data from the downloaded content
            df = load_sponsor_data(csv_content)

            if df is not None:
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
                # Show the total number of companies
                st.write(f"Total number of companies: {len(filtered_df)}")
                # Use the st.dataframe with on_select set to "rerun"
                selected_row_data = st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    on_select="rerun",
                    column_config={
                        "Company Info URL": st.column_config.LinkColumn("Company Info URL")
                    }
                )

                if selected_row_data['selection']['rows']:  # Check if a row is selected
                    if len(selected_row_data['selection']['rows']) >20:
                        st.warning("Company search is limited to 20 companies at a time. Please select fewer companies.")
                        #limit the number of selected companies to 20
                        selected_row_data['selection']['rows'] = selected_row_data['selection']['rows'][:20]
                    st.write("Selected Companies: (red color indicates the link is not found)")
                    for i in selected_row_data['selection']['rows']:
                        # Get the selected row's Organisation Name from the returned dictionary
                        selected_organisation=filtered_df.iloc[i]['Organisation Name']
                        #url encode the selected organisation name
                        url_selected_organisation = quote(selected_organisation)
                        company_info_url = f"https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?companyNameIncludes={url_selected_organisation}&status=active"
                        company_actual_url=get_company_link(selected_organisation)
                        #make a button with the link , button text should be the company name
                        if company_actual_url:
                            st.write(f" [{selected_organisation}]({company_actual_url})")

                            company_info = get_company_info(company_actual_url)
                            if company_info:
                                st.write(f"**Company Info for {selected_organisation}**")
                                for key, value in company_info.items():
                                    st.write(f"**{key}:** {value}")

                            sic_codes = get_sic_codes(company_actual_url)
                            if sic_codes:
                                st.write(f"Activities for {selected_organisation}")
                                for sic_id, code in sic_codes.items():
                                    st.write(f" {code}")
                        else:
                            #make it different color if the link is not found
                            #use html
                            st.write(f"<a href='{company_info_url}' style='color:red;'>{selected_organisation}</a>", unsafe_allow_html=True)
                # Show map with sponsors per city
                st.header("Sponsor Locations on UK Map")
                sponsor_map = plot_map(filtered_df)
                if sponsor_map:
                    st_folium(sponsor_map, width=700, height=500)

        else:
            st.error("Could not download the CSV file.")
    else:
        st.error("Could not find the CSV file URL.")


if __name__ == "__main__":
    main()
