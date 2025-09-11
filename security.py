from fastapi import HTTPException, Header
from dotenv import load_dotenv
from fastapi import status

import os


load_dotenv('.env')

def check_api_key(
    x_api_key: str = Header(alias='X-API-KEY', default=None)
):
    if os.getenv('X_API_KEY') != x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
