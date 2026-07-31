import unittest
import sys
import os
from pathlib import Path

# Setup path so tests can run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import config

class TestConfig(unittest.TestCase):
    def test_environment_variables_loaded(self):
        # We know we just saved GROQ_API_KEY and TELEGRAM keys into .env
        self.assertIsNotNone(config.GROQ_API_KEY)
        self.assertIsNotNone(config.TELEGRAM_BOT_TOKEN)
        self.assertIsNotNone(config.TELEGRAM_CHAT_ID)
        
        # Test default values
        self.assertEqual(config.ROBOT_NAME, "GreetBot")
        self.assertIsInstance(config.LLM_MAX_TOKENS, int)
        self.assertIsInstance(config.LLM_TEMPERATURE, float)

if __name__ == '__main__':
    unittest.main()
