import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io
import folium
from streamlit_folium import st_folium
from urllib.parse import quote  # For URL encoding
st.set_page_config(layout="wide")
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

        # Add a new column with URL for company search
        df['Company Info URL'] = df['Organisation Name'].apply(
            lambda name: f"https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?"
                         f"companyNameIncludes={quote(name)}"
        )

        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None


# Step 4: Plot UK map with sponsors
def plot_map(data):
    # Placeholder content: Feature in development
    text = """
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
        response = requests.get(company_info_url)
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


def get_company_link(company_info_url, company_name):
    """
    Scrapes the provided company information URL for the exact company name
    and returns the corresponding link if found.

    :param company_info_url: The URL to scrape for company information.
    :param company_name: The name of the company to search for.
    :return: The link to the company's information if found; otherwise, None.
    """
    base_url="https://find-and-update.company-information.service.gov.uk/"
    try:
        # Send a request to the company info URL
        response = requests.get(company_info_url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.content, "html.parser")
        text_to_search = company_name.lower()
        #strip all white spaces
        text_to_search = text_to_search.replace(" ", "")
        # st.write(f"Searching for: {text_to_search}")
        # Search for company name in the results
        for link in soup.find_all("a"):
            #st.write(link.text.lower().replace(" ", "").replace("(linkopensanewwindow)","").replace("(opensinnewtab)",""))

            if text_to_search==link.text.lower().replace(" ", "").replace("(linkopensanewwindow)","").replace("(opensinnewtab)",""):
                return base_url+link.get("href")
                # Return the URL of the found company

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
                # Set table display size slightly bigger
                # st.markdown(
                #     """
                #     <style>
                #     .dataframe { font-size: 16px !important; }
                #     </style>
                #     """, unsafe_allow_html=True)

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
                # st.dataframe(filtered_df,width=2600, height=500,use_container_width=False)
                # filtered_df['Company Info URL'] = filtered_df['Company Info URL'].apply(
                #     lambda url: f'<a href="{url}" target="_blank">Company Info</a>')
                # st.write(filtered_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                 # Use the st.dataframe with on_select set to "rerun"
                selected_row_data = st.dataframe(filtered_df, use_container_width=True, on_select="rerun")#,selection_mode="single-row")

                if selected_row_data['selection']['rows']:  # Check if a row is selected
                    if len(selected_row_data['selection']['rows']) >20:
                        st.warning("Company search is limited to 20 companies at a time. Please select fewer companies.")
                        #limit the number of selected companies to 20
                        selected_row_data['selection']['rows'] = selected_row_data['selection']['rows'][:20]
                    st.write("Selected Companies: (red color indicates the link is not found)")
                    # st.write(selected_row_data['selection']['rows'])
                    for i in selected_row_data['selection']['rows']:
                        # Get the selected row's Organisation Name from the returned dictionary
                        selected_organisation=filtered_df.iloc[i]['Organisation Name']
                        #url encode the selected organisation name
                        url_selected_organisation = quote(selected_organisation)
                        company_info_url = f"https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?companyNameIncludes={url_selected_organisation}&status=active"
                        company_actual_url=get_company_link(company_info_url, selected_organisation)
                        # Use Streamlit's markdown to open the URL in a new tab
                        # js = f"window.open('{company_info_url}');alert('Opening Company Info in a new tab...');"
                        # st.markdown(f'<script>{js}</script>', unsafe_allow_html=True)
                        #make a button with the link , button text should be the company name
                        if company_actual_url:
                            st.write(f" [{selected_organisation}]({company_actual_url})")
                            sic_codes = get_sic_codes(company_actual_url)
                            if sic_codes:
                                st.write(f"Activities for {selected_organisation}")
                                for sic_id, code in sic_codes.items():
                                    st.write(f" {code}")
                        else:
                            #make it different color if the link is not found
                            #st.write(f" [{selected_organisation}]({company_info_url})")
                            #use html
                            st.write(f"<a href='{company_info_url}' style='color:red;'>{selected_organisation}</a>", unsafe_allow_html=True)
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
