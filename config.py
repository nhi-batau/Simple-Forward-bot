# config.py
from os import environ

API_ID = int(environ.get("API_ID", "20114039"))
API_HASH = environ.get("API_HASH", "87297b8f3cc8fc9bbce591ad30da5896")
BOT_TOKEN = environ.get("BOT_TOKEN", "7996158914:AAEoO5TKXTROeg3WhpYd6dqT__3UUTFPXgY")
MONGO_URI = environ.get("MONGO_URI", "mongodb+srv://ssmemes163:mwWPwSoo73h8XRoo@cluster0.uc5ph6w.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
OWNER_ID = int(environ.get("OWNER_ID", "8172163893"))
