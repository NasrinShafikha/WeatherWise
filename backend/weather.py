
import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# API URLs
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# YouTube API key from .env
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


# Search for a location
def search_location(location):

    params = {
        "name": location,
        "count": 5,
        "language": "en",
        "format": "json"
    }

    response = requests.get(GEOCODING_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    if "results" not in data:
        raise ValueError("Location not found. Please try another city.")

    return data["results"]


# Get current weather and five-day forecast
def get_weather(latitude, longitude):

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "sunrise",
            "sunset"
        ],
        "forecast_days": 5,
        "timezone": "auto"
    }

    response = requests.get(WEATHER_URL, params=params, timeout=15)
    response.raise_for_status()

    return response.json()


# Get weather for a selected date range
def get_date_range_weather(latitude, longitude, start_date, end_date):

    today = date.today()

    if start_date > end_date:
        raise ValueError("Start date must be before end date.")

    if start_date > today:
        if end_date > today + timedelta(days=16):
            raise ValueError("Forecast is available only within the supported range.")
        api_url = WEATHER_URL

    elif end_date < today:
        api_url = ARCHIVE_URL

    else:
        raise ValueError(
            "Please select a date range entirely in the past or future."
        )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum"
        ],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto"
    }

    response = requests.get(api_url, params=params, timeout=20)
    response.raise_for_status()

    return response.json()


# Search YouTube for weather videos
def search_weather_videos(location):

    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API key is missing. Check your .env file.")

    params = {
        "part": "snippet",
        "q": f"weather forecast {location}",
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(
        YOUTUBE_SEARCH_URL,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):

        video_id = item["id"]["videoId"]
        details = item["snippet"]

        videos.append({
            "video_id": video_id,
            "title": details["title"],
            "channel": details["channelTitle"],
            "description": details["description"],
            "thumbnail": details["thumbnails"]["high"]["url"],
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })

    return videos
