import unittest
from pressure_notification import check_pressure_changes

class TestPressureRules(unittest.TestCase):
    def test_no_alert(self):
        # 気圧低下が閾値を下回る場合、アラートなし
        weather_data = {
            "current": {"pressure": 1013, "dt": 1749034217},
            "hourly": [
                {"dt": 1749034217, "pressure": 1013},
                {"dt": 1749034217 + 3600, "pressure": 1012},
                {"dt": 1749034217 + 7200, "pressure": 1011}
            ]
        }
        result = check_pressure_changes(weather_data)
        self.assertIsNone(result)

    def test_alert_3hours(self):
        # 3時間で3hPa以上の低下でアラート
        weather_data = {
            "current": {"pressure": 1013, "dt": 1749034217},
            "hourly": [
                {"dt": 1749034217, "pressure": 1013},
                {"dt": 1749034217 + 3600, "pressure": 1010},
                {"dt": 1749034217 + 7200, "pressure": 1009}
            ]
        }
        result = check_pressure_changes(weather_data)
        self.assertIsNotNone(result)
        self.assertIn("急速低下(3時間予測)", result["message"])

    def test_alert_12hours(self):
        # 12時間で10hPa以上の低下でアラート
        weather_data = {
            "current": {"pressure": 1013, "dt": 1749034217},
            "hourly": [
                {"dt": 1749034217, "pressure": 1013},
                {"dt": 1749034217 + 3600, "pressure": 1008},
                {"dt": 1749034217 + 7200, "pressure": 1003},
                {"dt": 1749034217 + 10800, "pressure": 1002},
                {"dt": 1749034217 + 14400, "pressure": 1001},
                {"dt": 1749034217 + 18000, "pressure": 1000},
                {"dt": 1749034217 + 21600, "pressure": 999},
                {"dt": 1749034217 + 25200, "pressure": 998},
                {"dt": 1749034217 + 28800, "pressure": 997},
                {"dt": 1749034217 + 32400, "pressure": 996},
                {"dt": 1749034217 + 36000, "pressure": 995},
                {"dt": 1749034217 + 39600, "pressure": 1013}
            ]
        }
        result = check_pressure_changes(weather_data)
        self.assertIsNotNone(result)
        self.assertIn("顕著な低下(12時間予測)", result["message"])

    def test_alert_24hours(self):
        # 24時間で5hPa以上の低下でアラート（12時間では6hPa未満の低下）
        weather_data = {
            "current": {"pressure": 1013, "dt": 1749034217},
            "hourly": [
                {"dt": 1749034217, "pressure": 1013},
                {"dt": 1749034217 + 3600 * 12, "pressure": 1008},  # 12時間後: 5hPa低下
                {"dt": 1749034217 + 3600 * 24, "pressure": 1007}   # 24時間後: 6hPa低下
            ]
        }
        result = check_pressure_changes(weather_data)
        self.assertIsNotNone(result)
        self.assertIn("日単位の変化に注意(24時間予測)", result["message"])

if __name__ == "__main__":
    unittest.main() 