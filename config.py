import os
from dotenv import load_dotenv

load_dotenv()

class Flask_Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chtwzebgdsthwfxgxyjnvwhxhdwecnvbsx")
    JWT_ACCESS_TOKEN_EXPIRES = 3600