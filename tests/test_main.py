import sys
from unittest.mock import MagicMock
import pytest

# Mocking modules before importing main.py
mock_st = MagicMock()
# Mock st.cache_data to be a transparent decorator
mock_st.cache_data.return_value = lambda f: f
sys.modules["streamlit"] = mock_st

mock_pd = MagicMock()
sys.modules["pandas"] = mock_pd

mock_requests = MagicMock()
sys.modules["requests"] = mock_requests

mock_bs4 = MagicMock()
sys.modules["bs4"] = mock_bs4

mock_folium = MagicMock()
sys.modules["folium"] = mock_folium

mock_st_folium = MagicMock()
sys.modules["streamlit_folium"] = mock_st_folium

# Now import the function to test
from main import get_coordinates

def test_get_coordinates_none():
    """Test get_coordinates with None input."""
    lat, lon = get_coordinates(None)
    assert lat is None
    assert lon is None

def test_get_coordinates_empty_string():
    """Test get_coordinates with empty string input."""
    lat, lon = get_coordinates("")
    assert lat is None
    assert lon is None

def test_get_coordinates_isna():
    """Test get_coordinates with pd.NA input."""
    # Mock pd.isna to return True for a specific sentinel value
    sentinel_na = "pd.NA_SENTINEL"
    mock_pd.isna.side_effect = lambda x: x == sentinel_na

    lat, lon = get_coordinates(sentinel_na)
    assert lat is None
    assert lon is None
    mock_pd.isna.assert_called_with(sentinel_na)
