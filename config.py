import os

class Config:
    APP_NAME = "MUIV VKR PROJECT"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("SQLALCHEMY_DATABASE_URI") or "sqlite:///site.db"
    )
    SECRET_KEY = 'your-very-secret-and-random-key'
