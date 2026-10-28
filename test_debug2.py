import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from tests.test_shift_integration import TestVoiceShiftStart

class DebugVoice(TestVoiceShiftStart):
    def test_yes_debug(self):
        prompt = self.assistant.ask(self.WAKE)
        print("PROMPT:", prompt)
        answer = self.assistant.ask("Yes")
        print("ANSWER:", answer)
        rows = self._shift_rows()
        print("ROWS:", rows)

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(DebugVoice("test_yes_debug"))
    unittest.TextTestRunner().run(suite)
