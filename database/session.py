import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL =", DATABASE_URL)


if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set in the .env file")


engine = create_engine(
    DATABASE_URL,
    echo=True
)


def get_session():
    with Session(engine) as session:
        yield session