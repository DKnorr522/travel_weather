import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from time import sleep
from datetime import datetime, timedelta, time
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns


ss = st.session_state
if "journey" not in ss: ss["journey"] = {}
if "weather_plot" not in ss: ss["weather_plot"] = None
# if "show_plot" not in ss: ss["show_plot"] = False


def get_forecast_soup(
        day: str = datetime.today().strftime('%Y-%m-%d'),
        city: str = "buffalo",
        state: str = "ny"
        ) -> BeautifulSoup:
    url = f"https://www.wunderground.com/hourly/us/{state}/{city}/date/{day}"
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")  # idea from https://selenium.streamlit.app/ on Apr 26, 2024
    chrome_options.add_argument("--headless")
    # browser = webdriver.Chrome(options=chrome_options)
    browser = webdriver.Chrome(
        service=Service(
            ChromeDriverManager(
                chrome_type=ChromeType.CHROMIUM
            ).install()
        ),
        options=chrome_options
    )

    browser.get(url)

    sleep(1)

    content = browser.page_source
    soup = BeautifulSoup(content, "html.parser")
    return soup


def extract_col_headers(soup: BeautifulSoup) -> list:
    hours_table = soup.find(
        "table",
        attrs={"id": "hourly-forecast-table"}
    )

    hours_header = hours_table.find("thead").find("tr")

    col_headers = [
        header.text.strip()
            for header in hours_header.find_all("th", recursive=False)
    ]
    return col_headers


def time_to_num(time_val: str) -> int:
    num, am_pm = time_val.split()
    if num == "12:00": return 12 * (am_pm == "pm")
    return int(num.split(":")[0]) + 12*(am_pm == "pm")


def extract_forecast(soup: BeautifulSoup, col_headers: list) -> dict:
    hours_table = soup.find(
        "table",
        attrs={"id": "hourly-forecast-table"}
    )
    hours_body = hours_table.find("tbody")
    hours = hours_body.find_all("tr", recursive=False)

    forecast = {}

    for hour in hours:
        time_field = hour.find("td")
        time_val = time_to_num(time_field.text.strip())
        forecast[time_val] = {
            col_headers[col_num+1]:
            field.text.replace('\xa0', ' ').strip()
                for col_num, field in enumerate(hour.find_all("td", recursive=False)[1:])
        }

    return forecast


def clean_forecast(forecast: dict) -> dict:
    for hour, data in forecast.items():
        for col, datum in data.items():
            if col == "Conditions": continue

            details = datum.split()
            details[0] = float(details[0])
            forecast[hour][col] = details
    return forecast


def get_forecast(
        day: str = datetime.today().strftime('%Y-%m-%d'),
        city: str = "buffalo",
        state: str = "ny"
        ) -> dict:
    soup = get_forecast_soup(day, city, state)
    col_headers = extract_col_headers(soup)
    forecast_dict_raw = extract_forecast(soup, col_headers)
    forecast_dict = clean_forecast(forecast_dict_raw)
    return forecast_dict


def get_forecasts(day: str, cities: dict) -> dict:
    forecasts = {
        city:
            get_forecast(day, city, cities[city]["state"]) for city in cities
    }
    return forecasts


def get_journey(day: str, forecast: dict, start_time: int, cities: dict) -> dict:
    # journey = {
    #     start_time + cities[city]["travel_time"]:
    #         forecast[city][start_time+cities[city]["travel_time"]]
    #         for city in cities
    # }

    journey = {
        "day": day,
        "start_time": start_time,
        "cities": {}
    }
    for city in cities.keys():
        journey["cities"][city] = {
            "hour": start_time + cities[city]["travel_time"],
            "forecast": forecast[city][start_time+cities[city]["travel_time"]]
        }
    return journey


def get_new_journey(day: str, cities: dict, start_time: int) -> dict:
    forecasts = get_forecasts(day, cities)
    journey = get_journey(day, forecasts, start_time, cities)
    ss["journey"] = journey
    return journey


def get_journey_plot(journey: dict):
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # keys = journey.keys()
    keys = journey["cities"].keys()

    ax1.plot(
        keys,
        # [journey[key]["Temp."][0] for key in keys],
        [journey["cities"][key]["forecast"]["Temp."][0] for key in keys],
        'r',
        label="Temperature"
    )

    ax2.bar(
        keys,
        # [journey[key]["Cloud Cover"][0] for key in keys],
        [journey["cities"][key]["forecast"]["Cloud Cover"][0] for key in keys],
        alpha=.5,
        label="Cloud Cover"
    )

    ax2.scatter(
        keys,
        # [journey[key]["Precip"][0] for key in keys],
        [journey["cities"][key]["forecast"]["Precip"][0] for key in keys],
        label="Chance of Precipitation"
    )

    # plt.xlabel("Time (Hour)")
    plt.xlabel("City")
    plt.xticks(rotation=45)
    # plt.xticks(
    #     ticks=[
    #         journey['cities'][city]['hour'] for city in journey['cities'].keys()
    #     ],
    #     labels=[
    #         f"{journey['cities'][city]}\n{journey['cities'][city]['hour']}" for city in journey['cities'].keys()
    #     ]
    # )
    ax1.set_ylabel("Temperature (F)")
    ax2.set_ylabel("Percent")
    ax2.set_ylim((0, 100))
    ax1.grid()
    ax2.grid(which="minor")
    plt.title(f"Temperature Along Drive from Buffalo to Round Lake")  # on {date}")
    plt.legend(
        loc="best",
        bbox_to_anchor=(.75, -0.1)
    )
    ss["weather_plot"] = fig
    return fig


cities_travel_east = {
    "buffalo": {"travel_time": 0, "state": "ny"},
    "rochester": {"travel_time": 1, "state": "ny"},
    "syracuse": {"travel_time": 2, "state": "ny"},
    "utica": {"travel_time": 3, "state": "ny"},
    "amsterdam": {"travel_time": 4, "state": "ny"},
    "round_lake": {"travel_time": 5, "state": "ny"}
}

cities_travel_west = {
    "round_lake": {"travel_time": 0, "state": "ny"},
    "amsterdam": {"travel_time": 1, "state": "ny"},
    "utica": {"travel_time": 2, "state": "ny"},
    "syracuse": {"travel_time": 3, "state": "ny"},
    "rochester": {"travel_time": 4, "state": "ny"},
    "buffalo": {"travel_time": 5, "state": "ny"}
}

travel_dir_dict = {
    "To Round Lake": cities_travel_east,
    "To Buffalo": cities_travel_west
}

today = datetime.today()
tomorrow = datetime.today() + timedelta(days=1)
fortnight = today + timedelta(days=14)

st.header(
    "Forecast Viewer for Drive Between Buffalo and Round Lake"
)

date_col, time_col, direction_col = st.columns(3)

with date_col:
    travel_date = st.date_input(
        label="Choose travel date",
        value=tomorrow,
        min_value=today if today.hour < 16 else tomorrow,
        max_value=fortnight
    )

with time_col:
    leave_time = st.time_input(
        label="What time are you leaving?",
        value=time(hour=10),
        step=timedelta(hours=1)
    ).hour

with direction_col:
    travel_dir = st.radio(
        label="Choose direction of travel",
        options=travel_dir_dict.keys()
    )

if st.button(
    label="Get drive forecast"
):
    ss["journey"] = {}
    ss["weather_plot"] = None
    get_new_journey(
        travel_date,
        travel_dir_dict[travel_dir],
        leave_time
    )
    get_journey_plot(ss["journey"])

if ss["weather_plot"]:
    st.pyplot(ss["weather_plot"])

colors = [
    "red",
    "orange",
    "yellow",
    "green",
    "blue"
]

