import sys
from unittest.mock import MagicMock
sys.modules['cv2'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['faster_whisper'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['pyttsx3'] = MagicMock()
sys.modules['elevenlabs'] = MagicMock()
sys.modules['av'] = MagicMock()

from fastapi.testclient import TestClient
import api.server

client = TestClient(api.server.app)

client.post("/api/operators", json={"operator_id": "op_test_2", "name": "API Worker"})
res1 = client.post("/api/v1/attendance/check-in", json={"employee_id": "op_test_2"})
print("CHECK-IN:", res1.json())

res2 = client.get("/api/v1/attendance")
print("LIST AFTER CHECK-IN:", res2.json())

res3 = client.post("/api/v1/attendance/check-out", json={"employee_id": "op_test_2"})
print("CHECK-OUT:", res3.json())

res4 = client.get("/api/v1/attendance")
print("LIST AFTER CHECK-OUT:", res4.json())
