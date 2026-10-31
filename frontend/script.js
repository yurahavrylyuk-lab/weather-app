const weatherDescriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    97: "Heavy thunderstorm",
    99: "Thunderstorm with heavy hail"
};

const weatherIcons = {
    0: "☀︎",
    1: "🌤",
    2: "⛅",
    3: "☁︎",

    45: "≋",
    48: "≋",

    51: "🌦",
    53: "🌦",
    55: "🌧",

    56: "🌧",
    57: "🌧",

    61: "🌦",
    63: "🌧",
    65: "🌧",

    66: "🌧",
    67: "🌧",

    71: "🌨",
    73: "🌨",
    75: "❄︎",
    77: "❄︎",

    80: "🌦",
    81: "🌧",
    82: "⛈",

    85: "🌨",
    86: "❄︎",

    95: "⛈",
    96: "⛈",
    97: "⛈",
    99: "⛈"
};

const weatherBackgroundClasses = [
    "weather-clear",
    "weather-few",
    "weather-sct",
    "weather-bkn",
    "weather-ovc"
];

function applyWeatherBackground(backgroundClass) {
    document.body.classList.remove(...weatherBackgroundClasses);
    document.body.classList.add(backgroundClass);
}

function getCloudBackgroundFromMetar(metar) {
    if (!metar || !metar.clouds || metar.clouds.length === 0) {
        return null;
    }

    const covers = metar.clouds.map((cloud) => cloud.cover);

    if (covers.includes("OVC")) {
        return "weather-ovc";
    }

    if (covers.includes("BKN")) {
        return "weather-bkn";
    }

    if (covers.includes("SCT")) {
        return "weather-sct";
    }

    if (covers.includes("FEW")) {
        return "weather-few";
    }

    return null;
}

const flightCategoryClasses = [
    "flight-vfr",
    "flight-mvfr",
    "flight-ifr",
    "flight-lifr"
];

function applyFlightCategoryColor(category) {
    const element = document.getElementById("flight-category");

    element.classList.remove(...flightCategoryClasses);

    if (!category) {
        return;
    }

    if (category === "VFR") {
        element.classList.add("flight-vfr");
    } else if (category === "MVFR") {
        element.classList.add("flight-mvfr");
    } else if (category === "IFR") {
        element.classList.add("flight-ifr");
    } else if (category === "LIFR") {
        element.classList.add("flight-lifr");
    }
}

function getCloudBackgroundFromWeatherCode(weatherCode) {
    if (weatherCode === 0) {
        return "weather-clear";
    }

    if (weatherCode === 1) {
        return "weather-few";
    }

    if (weatherCode === 2) {
        return "weather-sct";
    }

    if (weatherCode === 3) {
        return "weather-ovc";
    }

    // Fallback for rain/snow/fog/thunder etc.
    return "weather-bkn";
}

function getBackgroundClass(data) {
    const metarClass = getCloudBackgroundFromMetar(data.metar);

    if (metarClass) {
        return metarClass;
    }

    return getCloudBackgroundFromWeatherCode(data.weather_code);
}

const searchForm = document.getElementById("search-form");
const cityInput = document.getElementById("city-input");
const searchButton = document.getElementById("search-button");
const statusMessage = document.getElementById("status-message");


searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const city = cityInput.value.trim();

    if (!city) {
        return;
    }


    // Show loading state
    statusMessage.textContent = "Loading weather...";
    searchButton.disabled = true;


    try {
      const response = await fetch(
          `/api/weather?city=${encodeURIComponent(city)}`
      );


        // Handle HTTP errors
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error("City not found.");
            }

            throw new Error("Weather service is unavailable.");
        }


        const data = await response.json();

        const backgroundClass = getBackgroundClass(data);
        applyWeatherBackground(backgroundClass);

        // GENERAL WEATHER

        document.getElementById("weather-description").textContent =
            weatherDescriptions[data.weather_code] || "Unknown weather";
        document.getElementById("weather-icon").textContent =
            weatherIcons[data.weather_code] || "☁︎";

        document.getElementById("city-name").textContent =
            data.city;

        document.getElementById("country-name").textContent =
            data.country || "";

        document.getElementById("temperature").textContent =
            `${Math.round(data.temperature)}°C`;

        document.getElementById("apparent-temperature").textContent =
            `${Math.round(data.apparent_temperature)}°C`;

        document.getElementById("humidity").textContent =
            `${data.humidity}%`;

        document.getElementById("wind-speed").textContent =
            `${data.wind_speed} km/h`;


        // METAR / AVIATION SUMMARY

        const metar = data.metar;


        if (metar) {
            // Aviation summary
            document.getElementById("flight-category").textContent =
                metar.flight_category || "N/A";
            applyFlightCategoryColor(
                metar.flight_category
            );

            document.getElementById("visibility").textContent =
                metar.visibility?.display || "N/A";

            document.getElementById("ceiling").textContent =
                metar.ceiling_ft_agl !== null
                    ? `${metar.ceiling_ft_agl} ft AGL`
                    : "No ceiling";


            // METAR STATION

            document.getElementById("metar-station").textContent =
                metar.station || "N/A";

            document.getElementById("metar-station-name").textContent =
                metar.station_name || "Unknown station";

            document.getElementById("metar-distance").textContent =
                metar.distance_km !== null
                    ? `${metar.distance_km} km`
                    : "N/A";

            document.getElementById("metar-time").textContent =
                metar.observed_at
                    ? new Date(metar.observed_at).toLocaleString()
                    : "N/A";


            // METAR WIND

            if (metar.wind) {
                const direction =
                    metar.wind.direction_deg !== null
                        ? `${metar.wind.direction_deg}°`
                        : "VRB";

                const speed =
                    metar.wind.speed_kt !== null
                        ? `${metar.wind.speed_kt} kt`
                        : "N/A";

                let windText = `${direction} / ${speed}`;

                if (metar.wind.gust_kt !== null) {
                    windText += ` gusting ${metar.wind.gust_kt} kt`;
                }

                document.getElementById("metar-wind").textContent =
                    windText;

            } else {
                document.getElementById("metar-wind").textContent =
                    "N/A";
            }


            // METAR VISIBILITY

            document.getElementById("metar-visibility").textContent =
                metar.visibility?.display || "N/A";


            // METAR CLOUDS

            if (
                metar.clouds &&
                metar.clouds.length > 0
            ) {
                const cloudText = metar.clouds
                    .map((cloud) => {
                        if (cloud.base_ft_agl !== null) {
                            return `${cloud.cover} ${cloud.base_ft_agl} ft AGL`;
                        }

                        return cloud.cover;
                    })
                    .join(", ");

                document.getElementById("metar-clouds").textContent =
                    cloudText;

            } else {
                document.getElementById("metar-clouds").textContent =
                    "No cloud layers reported";
            }


            // METAR CEILING

            document.getElementById("metar-ceiling").textContent =
                metar.ceiling_ft_agl !== null
                    ? `${metar.ceiling_ft_agl} ft AGL`
                    : "No ceiling";


            // TEMPERATURE / DEW POINT

            document.getElementById("metar-temperature").textContent =
                metar.temperature_c !== null
                    ? `${metar.temperature_c}°C`
                    : "N/A";

            document.getElementById("metar-dewpoint").textContent =
                metar.dewpoint_c !== null
                    ? `${metar.dewpoint_c}°C`
                    : "N/A";


            // QNH

            document.getElementById("metar-qnh").textContent =
                metar.qnh_hpa !== null
                    ? `${metar.qnh_hpa} hPa`
                    : "N/A";


            // WEATHER PHENOMENA

            if (
                metar.phenomena &&
                metar.phenomena.length > 0
            ) {
                const phenomenaText = metar.phenomena
                    .map(
                        (phenomenon) =>
                            `${phenomenon.code} — ${phenomenon.description}`
                    )
                    .join(", ");

                document.getElementById("metar-phenomena").textContent =
                    phenomenaText;

            } else {
                document.getElementById("metar-phenomena").textContent =
                    "None";
            }


            // RAW METAR

            document.getElementById("raw-metar").textContent =
                metar.raw || "N/A";


        } else {
            // NO METAR AVAILABLE

            document.getElementById("flight-category").textContent =
                "N/A";
            applyFlightCategoryColor(null);

            document.getElementById("visibility").textContent =
                "N/A";

            document.getElementById("ceiling").textContent =
                "N/A";


            document.getElementById("metar-station").textContent =
                "No recent METAR";

            document.getElementById("metar-station-name").textContent =
                "No reporting station found within the last hour";

            document.getElementById("metar-distance").textContent =
                "N/A";

            document.getElementById("metar-time").textContent =
                "N/A";

            document.getElementById("metar-wind").textContent =
                "N/A";

            document.getElementById("metar-visibility").textContent =
                "N/A";

            document.getElementById("metar-clouds").textContent =
                "N/A";

            document.getElementById("metar-ceiling").textContent =
                "N/A";

            document.getElementById("metar-temperature").textContent =
                "N/A";

            document.getElementById("metar-dewpoint").textContent =
                "N/A";

            document.getElementById("metar-qnh").textContent =
                "N/A";

            document.getElementById("metar-phenomena").textContent =
                "N/A";

            document.getElementById("raw-metar").textContent =
                "No recent METAR available";
        }


        // WINDS ALOFT

        const winds = data.winds_aloft;


        if (winds) {
            document.getElementById("wind-1000").textContent =
                `${winds["1000_ft_agl"].direction_deg}° / ${winds["1000_ft_agl"].speed_kt} kt`;

            document.getElementById("wind-2000").textContent =
                `${winds["2000_ft_agl"].direction_deg}° / ${winds["2000_ft_agl"].speed_kt} kt`;

            document.getElementById("wind-3000").textContent =
                `${winds["3000_ft_agl"].direction_deg}° / ${winds["3000_ft_agl"].speed_kt} kt`;

            document.getElementById("wind-5000").textContent =
                `${winds["5000_ft_agl"].direction_deg}° / ${winds["5000_ft_agl"].speed_kt} kt`;

        } else {
            document.getElementById("wind-1000").textContent =
                "N/A";

            document.getElementById("wind-2000").textContent =
                "N/A";

            document.getElementById("wind-3000").textContent =
                "N/A";

            document.getElementById("wind-5000").textContent =
                "N/A";
        }

        // FREEZING LEVEL

        if (data.freezing_level) {
            document.getElementById("freezing-level").textContent =
                `${data.freezing_level.height_ft_amsl} ft AMSL`;

        } else {
            document.getElementById("freezing-level").textContent =
                "N/A";
        }


        statusMessage.textContent = "";


    } catch (error) {
        console.error(error);


        if (error instanceof TypeError) {
            statusMessage.textContent =
                "Weather service is unavailable.";

        } else {
            statusMessage.textContent =
                error.message || "Something went wrong.";
        }


    } finally {
        searchButton.disabled = false;
    }
});

applyWeatherBackground("weather-ovc");
