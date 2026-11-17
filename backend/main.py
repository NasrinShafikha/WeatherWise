
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
import requests
import csv
import io
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from database import engine, Base, get_db
from models import WeatherRecord
from weather import (
    search_location,
    get_weather,
    get_date_range_weather,
    search_weather_videos
)


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WeatherWise API")


# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class RecordCreate(BaseModel):
    location: str
    country: str = ""
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    humidity: float | None = None
    wind_speed: float | None = None


class RecordUpdate(BaseModel):
    location: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    humidity: float | None = None
    wind_speed: float | None = None


# Convert database record into dictionary
def record_to_dict(record):
    return {
        "id": record.id,
        "location": record.location,
        "country": record.country,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "temperature": record.temperature,
        "weather_description": record.weather_description,
        "humidity": record.humidity,
        "wind_speed": record.wind_speed,
        "created_at": record.created_at
    }


# Calculate average temperature
def calculate_average_temperature(weather_data):
    daily = weather_data.get("daily", {})

    maximum = daily.get("temperature_2m_max", [])
    minimum = daily.get("temperature_2m_min", [])

    daily_averages = [
        (high + low) / 2
        for high, low in zip(maximum, minimum)
        if high is not None and low is not None
    ]

    if not daily_averages:
        return None

    return round(sum(daily_averages) / len(daily_averages), 2)


# Convert GPS coordinates into a readable location name
def reverse_geocode(latitude, longitude):
    try:
        response = requests.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "localityLanguage": "en"
            },
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        name = (
            data.get("city")
            or data.get("locality")
            or data.get("localityInfo", {})
                .get("administrative", [{}])[0]
                .get("name")
            or "Your Current Location"
        )

        if name.strip().lower() in ["palamcottah", "palayamkottai"]:
            name = "Palayamkottai"

        return {
            "name": name,
            "admin1": data.get("principalSubdivision", ""),
            "country": data.get("countryName", "")
        }

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        IndexError
    ):
        return {
            "name": "Your Current Location",
            "admin1": "",
            "country": ""
        }


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to WeatherWise API",
        "status": "Running"
    }


# Search for locations
@app.get("/api/location")
def find_location(location: str):
    try:
        if not location.strip():
            raise HTTPException(
                status_code=400,
                detail="Please enter a location."
            )

        locations = search_location(location)
        return {"locations": locations}

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Location service is unavailable."
        )


# Get weather by city name
@app.get("/api/weather")
def current_weather(location: str):
    try:
        locations = search_location(location)

        if not locations:
            raise HTTPException(
                status_code=404,
                detail="Location not found."
            )

        place = locations[0]
        latitude = place["latitude"]
        longitude = place["longitude"]

        weather_data = get_weather(latitude, longitude)

        return {
            "location": {
                "name": place.get("name", ""),
                "admin1": place.get("admin1", ""),
                "country": place.get("country", ""),
                "latitude": latitude,
                "longitude": longitude
            },
            "weather": weather_data,
            "map_url": (
                "https://www.google.com/maps/search/?api=1"
                f"&query={latitude},{longitude}"
            )
        }

    except HTTPException:
        raise

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Weather service is unavailable."
        )

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


# Get weather using GPS coordinates
@app.get("/api/weather/coordinates")
def weather_by_coordinates(latitude: float, longitude: float):
    try:
        if not -90 <= latitude <= 90:
            raise HTTPException(
                status_code=400,
                detail="Invalid latitude."
            )

        if not -180 <= longitude <= 180:
            raise HTTPException(
                status_code=400,
                detail="Invalid longitude."
            )

        weather_data = get_weather(latitude, longitude)
        location_data = reverse_geocode(latitude, longitude)

        return {
            "location": {
                **location_data,
                "latitude": latitude,
                "longitude": longitude
            },
            "weather": weather_data,
            "latitude": latitude,
            "longitude": longitude,
            "map_url": (
                "https://www.google.com/maps/search/?api=1"
                f"&query={latitude},{longitude}"
            )
        }

    except HTTPException:
        raise

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Weather service is unavailable."
        )


# Get weather for a selected date range
@app.get("/api/weather/date-range")
def weather_by_date_range(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date
):
    try:
        if not -90 <= latitude <= 90:
            raise HTTPException(
                status_code=400,
                detail="Invalid latitude."
            )

        if not -180 <= longitude <= 180:
            raise HTTPException(
                status_code=400,
                detail="Invalid longitude."
            )

        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date."
            )

        weather_data = get_date_range_weather(
            latitude,
            longitude,
            start_date,
            end_date
        )

        return {
            "message": "Date-range weather retrieved successfully.",
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": weather_data.get("daily", {})
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve date-range weather."
        )


# Search YouTube weather videos
@app.get("/api/videos")
def get_weather_videos(location: str):
    if not location.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a location."
        )

    try:
        videos = search_weather_videos(location)

        return {
            "location": location,
            "videos": videos
        }

    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error))

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve YouTube videos."
        )


# Create and save a weather record
@app.post("/api/records", status_code=201)
def create_record(
    record: RecordCreate,
    db: Session = Depends(get_db)
):
    try:
        if record.start_date > record.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date."
            )

        weather_data = get_date_range_weather(
            record.latitude,
            record.longitude,
            record.start_date,
            record.end_date
        )

        average_temperature = calculate_average_temperature(
            weather_data
        )

        new_record = WeatherRecord(
            location=record.location,
            country=record.country,
            latitude=record.latitude,
            longitude=record.longitude,
            start_date=record.start_date,
            end_date=record.end_date,
            temperature=average_temperature,
            weather_description="Weather data retrieved successfully",
            humidity=record.humidity,
            wind_speed=record.wind_speed
        )

        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        return {
            "message": "Weather record saved successfully.",
            "record": record_to_dict(new_record),
            "weather_data": weather_data
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve weather data."
        )


# Get all saved records
@app.get("/api/records")
def get_records(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).order_by(
        WeatherRecord.id.desc()
    ).all()

    return [record_to_dict(record) for record in records]


# Get a single record
@app.get("/api/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(WeatherRecord).filter(
        WeatherRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Weather record not found."
        )

    return record_to_dict(record)


# Update a record
@app.put("/api/records/{record_id}")
def update_record(
    record_id: int,
    updated_data: RecordUpdate,
    db: Session = Depends(get_db)
):
    record = db.query(WeatherRecord).filter(
        WeatherRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Weather record not found."
        )

    changes = updated_data.dict(exclude_unset=True)

    for key, value in changes.items():
        setattr(record, key, value)

    if record.start_date > record.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date."
        )

    weather_changed = any(
        key in changes
        for key in [
            "latitude",
            "longitude",
            "start_date",
            "end_date"
        ]
    )

    if weather_changed:
        try:
            weather_data = get_date_range_weather(
                record.latitude,
                record.longitude,
                record.start_date,
                record.end_date
            )

            record.temperature = calculate_average_temperature(
                weather_data
            )

            record.weather_description = (
                "Weather data retrieved successfully"
            )

        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

        except requests.RequestException:
            raise HTTPException(
                status_code=503,
                detail="Unable to update weather data."
            )

    db.commit()
    db.refresh(record)

    return {
        "message": "Weather record updated successfully.",
        "record": record_to_dict(record)
    }


# Delete a record
@app.delete("/api/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(WeatherRecord).filter(
        WeatherRecord.id == record_id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Weather record not found."
        )

    db.delete(record)
    db.commit()

    return {"message": "Weather record deleted successfully."}


# Export records as CSV
@app.get("/api/export/csv")
def export_csv(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Location", "Country", "Latitude", "Longitude",
        "Start Date", "End Date", "Average Temperature",
        "Weather Description", "Humidity", "Wind Speed"
    ])

    for record in records:
        writer.writerow([
            record.id,
            record.location,
            record.country,
            record.latitude,
            record.longitude,
            record.start_date,
            record.end_date,
            record.temperature,
            record.weather_description,
            record.humidity,
            record.wind_speed
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=weather_records.csv"
        }
    )


# Export records as JSON
@app.get("/api/export/json")
def export_json(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).all()

    return [record_to_dict(record) for record in records]


# Export records as XML
@app.get("/api/export/xml")
def export_xml(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).all()

    root = ET.Element("weather_records")

    for record in records:
        record_element = ET.SubElement(root, "record")
        values = record_to_dict(record)

        for key, value in values.items():
            field = ET.SubElement(record_element, key)
            field.text = "" if value is None else str(value)

    xml_data = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True
    )

    return StreamingResponse(
        iter([xml_data]),
        media_type="application/xml",
        headers={
            "Content-Disposition":
                "attachment; filename=weather_records.xml"
        }
    )


# Export records as PDF
@app.get("/api/export/pdf")
def export_pdf(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).all()
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("WeatherWise - Weather Records Report", styles["Title"]),
        Spacer(1, 8 * mm),
        Paragraph(f"Total saved records: {len(records)}", styles["Normal"]),
        Spacer(1, 5 * mm)
    ]

    table_data = [[
        "ID", "Location", "Country", "Latitude", "Longitude",
        "Start Date", "End Date", "Avg Temp", "Humidity",
        "Wind Speed", "Description"
    ]]

    for record in records:
        table_data.append([
            str(record.id),
            Paragraph(xml_escape(str(record.location or "")), styles["BodyText"]),
            Paragraph(xml_escape(str(record.country or "")), styles["BodyText"]),
            str(record.latitude),
            str(record.longitude),
            str(record.start_date),
            str(record.end_date),
            str(record.temperature if record.temperature is not None else "N/A"),
            str(record.humidity if record.humidity is not None else "N/A"),
            str(record.wind_speed if record.wind_speed is not None else "N/A"),
            Paragraph(
                xml_escape(str(record.weather_description or "")),
                styles["BodyText"]
            )
        ])

    if not records:
        elements.append(
            Paragraph("No weather records have been saved yet.", styles["Normal"])
        )
    else:
        table = Table(table_data, repeatRows=1)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B53")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor("#F0F4F8")
            ]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ]))

        elements.append(table)

    document.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename=weather_records.pdf"
        }
    )


# Export records as Markdown
@app.get("/api/export/markdown")
def export_markdown(db: Session = Depends(get_db)):
    records = db.query(WeatherRecord).all()

    lines = [
        "# WeatherWise - Weather Records",
        "",
        f"Total saved records: {len(records)}",
        "",
        "| ID | Location | Country | Start Date | End Date | Average Temperature | Humidity | Wind Speed | Description |",
        "|---|---|---|---|---|---|---|---|---|"
    ]

    for record in records:
        location = str(record.location or "").replace("|", "\\|")
        country = str(record.country or "").replace("|", "\\|")
        description = str(
            record.weather_description or ""
        ).replace("|", "\\|")

        temperature = (
            str(record.temperature)
            if record.temperature is not None else "N/A"
        )

        humidity = (
            str(record.humidity)
            if record.humidity is not None else "N/A"
        )

        wind_speed = (
            str(record.wind_speed)
            if record.wind_speed is not None else "N/A"
        )

        lines.append(
            f"| {record.id} | {location} | {country} | "
            f"{record.start_date} | {record.end_date} | "
            f"{temperature} | {humidity} | {wind_speed} | "
            f"{description} |"
        )

    if not records:
        lines.extend(["", "No weather records have been saved yet."])

    markdown_data = "\n".join(lines)

    return StreamingResponse(
        iter([markdown_data]),
        media_type="text/markdown",
        headers={
            "Content-Disposition":
                "attachment; filename=weather_records.md"
        }
    )
