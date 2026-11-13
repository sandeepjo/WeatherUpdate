from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import tool
import json
import requests

# 1. Define the tools the open-source agent can use
@tool
def get_coordinates(city_name):
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
        return {
            "latitude": match.get("latitude"),
            "longitude": match.get("longitude")
        }

    return None




@tool
def query_weather_api(latitude: str, longitude: str) -> str:
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
        data = response.json()
        return data;

@tool
def weather_report_analysis(data : dict) -> dict:
    """Analyze the weather report for a given city using the weather report passed"""
    #response.raise_for_status()  # Raise error for bad responses
    #data = response.json()

    print(data)

    # 3. Parse the hourly data
    hourly_data = data["hourly"]
    times = hourly_data["time"]
    precipitation = hourly_data["precipitation"]  # Total liquid equivalent (mm)
    rain = hourly_data["rain"]  # Rain amount (mm)
    snowfall = hourly_data["snowfall"]  # Snowfall amount (cm)
    temperature = hourly_data["temperature_2m"]  # Temperature (°C)
    weather_codes = hourly_data["weather_code"]  # WMO Weather interpretation codes

    print(f"--- Weather Prediction for Lat: {data['latitude']}, Lon: {data['longitude']} ---")

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
        if temperature[i] > 26:
            formatted_time = datetime.fromisoformat(times[i]).strftime("%Y-%m-%d %H:%M")
            event_type = f"🔥 Hot ({temperature[i]} °C)"
            weather_events.append((formatted_time, event_type, weather_codes[i]))

    # 5. Output results
    if weather_events:
        print(f"\nFound {len(weather_events)} hours with predicted rain, snow or high temperature")
        # Displaying the first 10 events for brevity
        for time, event, code in weather_events:
            print(f"[{time}] - {event} (WMO Code: {code})")
    else:
        print("\n☀️ No rain, snow, or high temperature predicted in the next 7 days!")

tools = [get_coordinates, query_weather_api, weather_report_analysis]


# 2. Initialize the local open-source model via Ollama
# Setting temperature=0 helps keep the agent deterministic and follow tool rules closely
llm = ChatOllama(
    model="qwen3",
    temperature=0
)

# 3. Define the agent's behavior with a clear system prompt
system_prompt = (
    """You are weather report analyzer for a given city. For a given city you need to gather weather report
     and analyze the report for key events like rain, snow, high temperature report
     it to the user
    
     When given a weahter report analysis task for a given city:
     1. Use get_coordinates to get latitude and longitude
     2. Use query_weather_api to get the weather report
     3. Use weather_report_analysis to analyze the weather report for key events
     4. Report key weather events"""
)

# 4. Create the agent using LangChain's built-in framework
agent = create_agent(
    model=llm,              # Passes the initialized Ollama chat object
    tools=tools,            # Exposes the list of tools to the agent
    system_prompt=system_prompt
)

# 5. Execute the agent using an AgentExecutor loop
# The agent will analyze the prompt, call the tool if needed, and synthesize the result
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "Report key weather events for the city 'Hyderabad' and save it to report.md"}
    ]
})

# 6. Print the assistant's final response
print(result["messages"][-1].content)