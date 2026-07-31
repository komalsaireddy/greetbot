import unittest
import sys
from pathlib import Path

# Setup path so tests can run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from brain.prompt import PromptBuilder

class TestPrompts(unittest.TestCase):
    def setUp(self):
        self.builder = PromptBuilder()

    def test_build_system_prompt_stranger(self):
        prompt = self.builder.build_system_prompt(person_name=None, person_count=1)
        self.assertIn("unknown person", prompt)
        
    def test_build_system_prompt_known(self):
        prompt = self.builder.build_system_prompt(person_name="Alice", person_count=1)
        self.assertIn("You are speaking with: Alice", prompt)

    def test_build_system_prompt_multiple(self):
        prompt = self.builder.build_system_prompt(person_name="Bob", person_count=3)
        self.assertIn("There are 3 people visible", prompt)

if __name__ == '__main__':
    unittest.main()
