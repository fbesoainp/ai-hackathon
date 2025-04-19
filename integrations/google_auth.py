from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, initialize_app
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from models.google_user import GoogleUser
from utils.constants import GOOGLE_AUTH_CLIENT_IDS
from utils.logging import logger

app = FastAPI()
initialize_app()


security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> GoogleUser:
    """
    Verify the Google ID token and return the user info if the token is valid
    """
    token = credentials.credentials
    try:
        idinfo: dict = id_token.verify_firebase_token(token, google_requests.Request())
        audience = idinfo.get("aud")

        if audience not in GOOGLE_AUTH_CLIENT_IDS:
            logger.error(f"Invalid client ID: {audience}")
            raise HTTPException(status_code=401, detail="Invalid client ID")

        uid = idinfo["sub"]
        user = auth.get_user(uid)

        return GoogleUser(
            id=uid,
            email=user.email,
            name=user.display_name,
            picture=user.photo_url,
        )
    except Exception as e:
        logger.error(f"Invalid or expired token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token") from e
