import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.weather import WeatherService


def observation(hour, temp):
    return {'dt': int(datetime(2026, 9, 13, hour, tzinfo=timezone.utc).timestamp()),
            'main': {'temp': temp}, 'weather': [{'id': 800, 'description': 'clear'}], 'wind': {'speed': 1}}


class ForecastRegressionTests(unittest.TestCase):
    def test_all_periods_are_parsed(self):
        result = WeatherService()._parse_day_forecast({'list': [observation(h, t) for h, t in [(6, 10), (12, 20), (18, 15), (21, 8)]]})
        self.assertEqual([r['time_label'] for r in result], ['Morn', 'Noon', 'Eve', 'Night'])
        self.assertEqual([r['temp'] for r in result], [10, 20, 15, 8])

    def test_missing_periods_use_existing_forecast_fallback(self):
        result = WeatherService()._parse_day_forecast({'list': [observation(12, 20)]})
        self.assertEqual(len(result), 4)
        self.assertTrue(all(r['temp'] == 20 for r in result))

    def test_empty_forecast_does_not_reference_undefined_condition(self):
        self.assertEqual(WeatherService()._parse_day_forecast({'list': []}), [])

    def test_invalid_condition_is_rejected(self):
        item = observation(12, 20)
        item['weather'] = [{}]
        with self.assertRaises(ValueError):
            WeatherService()._parse_day_forecast({'list': [item]})
