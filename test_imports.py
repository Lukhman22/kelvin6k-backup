import time
print("start", time.time())
import fastapi
print("fastapi", time.time())
import sqlite3
print("sqlite3", time.time())
from agent import config
print("config", time.time())
from agent import db
print("db", time.time())
from agent.assistant import Assistant
print("assistant", time.time())
from api.camera_service import CameraService
print("camera", time.time())
print("done", time.time())
