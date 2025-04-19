import os

from dotenv import load_dotenv

load_dotenv()


MONGODB_DOMAIN = os.getenv("MONGODB_DOMAIN", "")
MONGODB_USER = os.getenv("MONGODB_USER", "")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")
MONGODB_DOMAIN = os.getenv("MONGODB_DOMAIN", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")
LOCATION = os.getenv("LOCATION", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
MODEL = os.getenv("MODEL", "")
GOOGLE_AUTH_CLIENT_IDS = [
    os.getenv("WEB_GOOGLE_AUTH_CLIENT_ID", ""),
    os.getenv("IOS_GOOGLE_AUTH_CLIENT_ID", ""),
    "pairfecto"
]
