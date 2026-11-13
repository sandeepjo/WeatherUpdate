import json
import os
import requests
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
from strands.vended_tools import make_write, write

from datetime import datetime

os.environ["BYPASS_TOOL_CONSENT"] = "true"


@tool
def get_coordinates(city_name: str) -> dict:
    """This function queries the Open-Meteo Geocoding API URL to get latitude and longitude for a given city name"""
    # Open-Meteo Geocoding API URL
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # Define query parameters
    params = {
        "name": city_name,
        "count": 1,  # Limit to the best matching result
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()  # Raise an error for bad responses

    data = response.json()

    # Check if any results were returned
    if "results" in data and len(data["results"]) > 0:
        match = data["results"][0]
        print("latitude", match.get("latitude"))
        print("longitude", match.get("longitude"))
        return {
            "latitude": match.get("latitude"),
            "longitude": match.get("longitude")
        }

    return None


@tool
def query_weather_api(latitude: float   , longitude: float  ) -> dict:
    """Query the open meteo API for the weather report of a given city"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
        "hourly": ["temperature_2m", "precipitation", "rain", "snowfall", "weather_code"],
        "timezone": "auto",  # Automatically detects local timezone
        "forecast_days": 7  # Look ahead up to 7 days (can go up to 16)
    }

    try:
        # 2. Make the API request
        response = requests.get(url, params=params)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Open-Meteo: {e}")
    weather_report = response.json()
    #print(data)
    return weather_report;


@tool
def weather_report_analysis(weather_report: dict) -> list:
    """Analyze the weather report for a given city using the weather report passed"""
    # response.raise_for_status()  # Raise error for bad responses
    # data = response.json()

    #print(data)

    # 3. Parse the hourly data
    hourly_data = weather_report["hourly"]
    times = hourly_data["time"]
    precipitation = hourly_data["precipitation"]  # Total liquid equivalent (mm)
    rain = hourly_data["rain"]  # Rain amount (mm)
    snowfall = hourly_data["snowfall"]  # Snowfall amount (cm)
    temperature = hourly_data["temperature_2m"]  # Temperature (°C)
    weather_codes = hourly_data["weather_code"]  # WMO Weather interpretation codes

    print(f"--- Weather Prediction for Lat: {weather_report['latitude']}, Lon: {weather_report['longitude']} ---")

    # 4. Analyze data for upcoming rain/snow events
    weather_events = []

    for i in range(len(times)):
        # Check if any precipitation is predicted for this hour
        if precipitation[i] > 0:
            formatted_time = datetime.fromisoformat(times[i]).strftime("%Y-%m-%d %H:%M")

            # Categorize the event type
            if snowfall[i] > 0 and rain[i] == 0:
                event_type = f"❄️ Snowfall ({snowfall[i]} cm)"
            elif rain[i] > 0 and snowfall[i] == 0:
                event_type = f"🌧️ Rain ({rain[i]} mm)"
            else:
                event_type = f"🌨️ Mixed Rain/Snow ({precipitation[i]} mm total)"
            weather_events.append((formatted_time, event_type, weather_codes[i]))
        if temperature[i] > 30:
            formatted_time = datetime.fromisoformat(times[i]).strftime("%Y-%m-%d %H:%M")
            event_type = f"🔥 Hot ({temperature[i]} °C)"
            weather_events.append((formatted_time, event_type, weather_codes[i]))

    # 5. Output results
    if weather_events:
        print(f"\nFound {len(weather_events)} hours with predicted rain, snow or high temperature")
        # Displaying the first 10 events for brevity
        for time, event, code in weather_events:
            print(f"[{time}] - {event} (WMO Code: {code})")
        return weather_events
    else:
        print("\n☀️ No rain, snow, or high temperature predicted in the next 7 days!")
        return None

model = AnthropicModel(
    client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
    model_id="claude-sonnet-5-5",
    max_tokens=8192,
)
SYSTEM_PROMPT = """You are weather report analyzer for a given city. For a given city you need to gather weather report
 and analyze the report for key events like rain, snow, high temperature report
 it to the user

 When given a weahter report analysis task for a given city:
 1. Use get_coordinates to get latitude and longitude
 2. Use query_weather_api to get the weather report
 3. Use weather_report_analysis to analyze the weather report for key events
 4. Write key weather events with timelines from the report generated by weather_report_analysis in file report.md in 'C Users sande PycharmProjects WeatherUpdate .venv Scripts' directory using tool write"""

agent = Agent(
    model=model,
    tools=[get_coordinates, query_weather_api, weather_report_analysis, write],
    system_prompt=SYSTEM_PROMPT,
)
result = agent("Report key weather events for the city 'Hyderabad'")
print(str(result))