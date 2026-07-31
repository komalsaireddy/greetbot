import unittest
import sys
from pathlib import Path

# Setup path so tests can run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from skills.wikipedia_skill import is_wikipedia_query, extract_wikipedia_query
from skills.search import is_search_query, extract_search_query
from skills.weather import is_weather_query, extract_city
from skills.telegram_bot import is_file_send_query, extract_file_query

class TestSkills(unittest.TestCase):
    def test_wikipedia_detection(self):
        self.assertTrue(is_wikipedia_query("who is albert einstein"))
        self.assertTrue(is_wikipedia_query("what is a black hole"))
        self.assertFalse(is_wikipedia_query("send me a photo"))
        self.assertEqual(extract_wikipedia_query("who is albert einstein"), "albert einstein")

    def test_search_detection(self):
        self.assertTrue(is_search_query("search for python tutorials"))
        self.assertTrue(is_search_query("look up the latest news"))
        self.assertFalse(is_search_query("play some music"))
        self.assertEqual(extract_search_query("search for python tutorials"), "python tutorials")

    def test_weather_detection(self):
        self.assertTrue(is_weather_query("what is the weather like today"))
        self.assertTrue(is_weather_query("weather in london"))
        self.assertFalse(is_weather_query("what is a cloud"))
        self.assertEqual(extract_city("weather in london"), "London")

    def test_telegram_file_send_detection(self):
        self.assertTrue(is_file_send_query("send me the report to telegram"))
        self.assertTrue(is_file_send_query("forward the timetable to telegram"))
        self.assertFalse(is_file_send_query("what is the weather"))
        self.assertEqual(extract_file_query("send me the timetable to telegram"), "the timetable")

if __name__ == '__main__':
    unittest.main()
