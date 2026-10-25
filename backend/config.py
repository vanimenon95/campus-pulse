import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    explicit = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if explicit:
        # hosts often give mysql://...; SQLAlchemy needs the PyMySQL driver name
        if explicit.startswith("mysql://"):
            explicit = "mysql+pymysql://" + explicit[len("mysql://"):]
        return explicit
    env = os.getenv
    user = quote_plus(env("DB_USER") or env("MYSQLUSER") or "campus_user")
    pw = quote_plus(env("DB_PASSWORD") or env("MYSQLPASSWORD") or "campus_password")
    host = env("DB_HOST") or env("MYSQLHOST") or "localhost"
    port = env("DB_PORT") or env("MYSQLPORT") or "3306"
    name = env("DB_NAME") or env("MYSQLDATABASE") or "campus_pulse"
    return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "12"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
