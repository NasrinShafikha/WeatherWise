from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from database import Base


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)

    location = Column(String, nullable=False)
    country = Column(String, nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    temperature = Column(Float, nullable=True)
    weather_description = Column(String, nullable=True)

    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
