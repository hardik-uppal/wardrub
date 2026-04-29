"""Weather service for location-based recommendations."""

from typing import Optional, List, Dict
from datetime import datetime, timezone
import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.models.outfit import WeatherInfo, WeatherCondition

settings = get_settings()
logger = get_logger("weather")


class TimeOfDayForecast:
    """Weather forecast for a specific time of day."""
    def __init__(self, time_label: str, temp: float, condition: str, icon: str, wind_speed: float = 0):
        self.time_label = time_label
        self.temp = round(temp)
        self.condition = condition
        self.icon = icon
        self.wind_speed = wind_speed
        self.is_windy = wind_speed > 5.5  # m/s, about 20 km/h
    
    def to_dict(self):
        return {
            "time_label": self.time_label,
            "temp": self.temp,
            "condition": self.condition,
            "icon": self.icon,
            "wind_speed": self.wind_speed,
            "is_windy": self.is_windy
        }


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap."""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
    
    def __init__(self):
        """Initialize weather service."""
        self.api_key = settings.OPENWEATHER_API_KEY
    
    async def get_weather_by_coords(
        self, 
        lat: float, 
        lon: float
    ) -> Optional[WeatherInfo]:
        """
        Get current weather for coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            WeatherInfo or None if failed
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": self.api_key,
                        "units": "metric"  # Celsius
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            return self._parse_weather_response(data)
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")
            return None
    
    async def get_weather_by_city(self, city: str) -> Optional[WeatherInfo]:
        """
        Get current weather for a city.
        
        Args:
            city: City name
        
        Returns:
            WeatherInfo or None if failed
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": "metric"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            return self._parse_weather_response(data)
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")
            return None
    
    def _parse_weather_response(self, data: dict) -> WeatherInfo:
        """Parse OpenWeatherMap API response into WeatherInfo."""
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        
        temperature = main.get("temp", 20)
        feels_like = main.get("feels_like", temperature)
        humidity = main.get("humidity", 50)
        
        # Map OpenWeatherMap condition to our enum
        condition_id = weather.get("id", 800)
        condition = self._map_condition(condition_id, temperature)
        
        description = weather.get("description", "").capitalize()
        city = data.get("name", "")
        
        logger.info(f"Weather for {city}: {temperature}°C, {description}")
        
        return WeatherInfo(
            temperature=temperature,
            feels_like=feels_like,
            condition=condition,
            description=description,
            humidity=humidity,
            city=city
        )
    
    def _map_condition(self, condition_id: int, temperature: float) -> WeatherCondition:
        """
        Map OpenWeatherMap condition ID to WeatherCondition enum.
        
        OpenWeatherMap condition codes:
        - 2xx: Thunderstorm
        - 3xx: Drizzle
        - 5xx: Rain
        - 6xx: Snow
        - 7xx: Atmosphere (fog, etc)
        - 800: Clear
        - 80x: Clouds
        """
        # Temperature-based override
        if temperature >= 30:
            return WeatherCondition.HOT
        if temperature <= 5:
            return WeatherCondition.COLD
        
        # Condition-based
        if condition_id < 300:  # Thunderstorm
            return WeatherCondition.RAINY
        if condition_id < 600:  # Drizzle or Rain
            return WeatherCondition.RAINY
        if condition_id < 700:  # Snow
            return WeatherCondition.SNOWY
        if condition_id == 800:  # Clear
            return WeatherCondition.CLEAR
        if condition_id > 800:  # Clouds
            return WeatherCondition.CLOUDY
        
        # Default
        return WeatherCondition.CLEAR
    
    def get_clothing_recommendation(self, weather: WeatherInfo) -> dict:
        """
        Get basic clothing recommendations based on weather.
        
        Args:
            weather: Current weather info
        
        Returns:
            Dictionary with recommendations by category
        """
        temp = weather.feels_like
        condition = weather.condition
        
        recommendations = {
            "layers": [],
            "avoid": [],
            "suggested_categories": []
        }
        
        # Temperature-based recommendations
        if temp < 10:
            recommendations["layers"] = ["Heavy outerwear", "Sweater/Hoodie", "Long sleeves"]
            recommendations["suggested_categories"] = ["outerwear", "top"]
            recommendations["avoid"] = ["Shorts", "Tank tops", "Light dresses"]
        elif temp < 18:
            recommendations["layers"] = ["Light jacket", "Long sleeves"]
            recommendations["suggested_categories"] = ["outerwear", "top", "bottom"]
            recommendations["avoid"] = ["Heavy coats", "Shorts"]
        elif temp < 25:
            recommendations["layers"] = ["Light layers", "Short or long sleeves"]
            recommendations["suggested_categories"] = ["top", "bottom", "dress"]
            recommendations["avoid"] = ["Heavy outerwear"]
        else:  # Hot
            recommendations["layers"] = ["Light, breathable fabrics"]
            recommendations["suggested_categories"] = ["top", "bottom", "dress"]
            recommendations["avoid"] = ["Heavy fabrics", "Dark colors", "Layers"]
        
        # Weather condition modifiers
        if condition == WeatherCondition.RAINY:
            recommendations["layers"].append("Water-resistant layer")
            if "outerwear" not in recommendations["suggested_categories"]:
                recommendations["suggested_categories"].append("outerwear")
        
        return recommendations

    async def get_day_forecast(self, lat: float, lon: float) -> Optional[List[Dict]]:
        """
        Get weather forecast for different times of day (morning, noon, evening, night).
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            List of forecast dicts for morning, noon, evening, night or None if failed
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.FORECAST_URL,
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": self.api_key,
                        "units": "metric",
                        "cnt": 16  # Get next 48 hours (16 x 3-hour intervals)
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            return self._parse_day_forecast(data)
        except httpx.HTTPStatusError as e:
            logger.error(f"Forecast API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch forecast: {e}")
            return None

    def _parse_day_forecast(self, data: dict) -> List[Dict]:
        """
        Parse OpenWeatherMap forecast response to extract morning, noon, evening, night weather.
        
        Args:
            data: API response
        
        Returns:
            List of forecasts for [morning, noon, evening, night]
        """
        forecasts = data.get("list", [])
        
        # Target hours for each time period
        time_periods = {
            "Morn": (6, 9),      # 6am - 9am
            "Noon": (11, 14),    # 11am - 2pm  
            "Eve": (17, 20),     # 5pm - 8pm
            "Night": (21, 24),   # 9pm - midnight
        }
        
        results = {}
        
        for forecast in forecasts:
            dt = datetime.fromtimestamp(forecast["dt"], tz=timezone.utc)
            local_hour = dt.hour  # This is UTC, but close enough for now
            
            main = forecast.get("main", {})
            weather = forecast.get("weather", [{}])[0]
            wind = forecast.get("wind", {})
            
            temp = main.get("temp", 20)
            condition_id = weather.get("id", 800)
            description = weather.get("description", "")
            wind_speed = wind.get("speed", 0)
            
            # Map to our condition and icon
            condition = self._get_condition_name(condition_id, temp, wind_speed)
            icon = self._get_weather_icon(condition_id, temp, wind_speed)
            
            # Find which time period this belongs to
            for period_name, (start_hour, end_hour) in time_periods.items():
                if period_name not in results and start_hour <= local_hour < end_hour:
                    results[period_name] = TimeOfDayForecast(
                        time_label=period_name,
                        temp=temp,
                        condition=condition,
                        icon=icon,
                        wind_speed=wind_speed
                    )
                    break
        
        # Fill in missing periods with current/nearby data
        if forecasts:
            first_forecast = forecasts[0]
            main = first_forecast.get("main", {})
            weather = first_forecast.get("weather", [{}])[0]
            wind = first_forecast.get("wind", {})
            default_temp = main.get("temp", 20)
            condition_id = weather.get("id", 800)
            wind_speed = wind.get("speed", 0)
            default_condition = self._get_condition_name(condition_id, default_temp, wind_speed)
            default_icon = self._get_weather_icon(condition_id, default_temp, wind_speed)
            
            for period_name in ["Morn", "Noon", "Eve", "Night"]:
                if period_name not in results:
                    results[period_name] = TimeOfDayForecast(
                        time_label=period_name,
                        temp=default_temp,
                        condition=default_condition,
                        icon=default_icon,
                        wind_speed=wind_speed
                    )
        
        # Return in order
        return [results.get(p).to_dict() for p in ["Morn", "Noon", "Eve", "Night"] if results.get(p)]

    def _get_condition_name(self, condition_id: int, temp: float, wind_speed: float) -> str:
        """Get human-readable condition name with wind info."""
        conditions = []
        
        # Main condition
        if condition_id < 300:  # Thunderstorm
            conditions.append("Stormy")
        elif condition_id < 400:  # Drizzle
            conditions.append("Drizzle")
        elif condition_id < 600:  # Rain
            conditions.append("Rainy")
        elif condition_id < 700:  # Snow
            conditions.append("Snowy")
        elif condition_id < 800:  # Atmosphere (fog, mist)
            conditions.append("Foggy")
        elif condition_id == 800:  # Clear
            if temp >= 30:
                conditions.append("Hot")
            elif temp <= 5:
                conditions.append("Cold")
            else:
                conditions.append("Clear")
        else:  # Clouds
            conditions.append("Cloudy")
        
        # Add windy if applicable
        if wind_speed > 5.5:  # > 20 km/h
            conditions.append("Windy")
        
        return " & ".join(conditions)

    def _get_weather_icon(self, condition_id: int, temp: float, wind_speed: float) -> str:
        """Get icon name for the weather condition."""
        # Primary icon based on condition
        if condition_id < 300:  # Thunderstorm
            return "cloud-lightning"
        elif condition_id < 600:  # Drizzle or Rain
            return "cloud-rain"
        elif condition_id < 700:  # Snow
            return "snowflake"
        elif condition_id < 800:  # Atmosphere
            return "cloud-fog"
        elif condition_id == 800:  # Clear
            if temp >= 30:
                return "thermometer"
            elif temp <= 5:
                return "snowflake"
            return "sun"
        else:  # Clouds
            if wind_speed > 5.5:
                return "wind"
            return "cloud"