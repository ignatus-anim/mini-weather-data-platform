import csv
import random
from datetime import datetime, timedelta
from io import StringIO
import boto3
from botocore.client import Config

STATIONS = [
    ("STN001", "Kotoka Airport", "Accra"),
    ("STN002", "Kumasi Met", "Kumasi"),
    ("STN003", "Tamale North", "Tamale"),
    ("STN004", "Takoradi Port", "Takoradi"),
    ("STN005", "Ho Central", "Ho"),
    ("STN006", "Cape Coast", "Cape Coast"),
    ("STN007", "Sunyani", "Sunyani"),
    ("STN008", "Bolgatanga", "Bolgatanga"),
]

CONDITIONS = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Thunderstorm", "Foggy", "Windy"]


def generate_records(days=30, readings_per_day=24):
    records = []
    start = datetime.now() - timedelta(days=days)

    for day in range(days):
        for hour in range(readings_per_day):
            for station_id, station_name, city in STATIONS:
                recorded_at = start + timedelta(days=day, hours=hour)
                records.append({
                    "station_id": station_id,
                    "station_name": station_name,
                    "city": city,
                    "temperature_c": round(random.uniform(18.0, 38.0), 1),
                    "humidity_pct": round(random.uniform(30.0, 95.0), 1),
                    "wind_speed_kmh": round(random.uniform(0.0, 60.0), 1),
                    "condition": random.choice(CONDITIONS),
                    "recorded_at": recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                })
    return records


def upload_to_minio(records):
    client = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin123",
        config=Config(signature_version="s3v4"),
    )

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

    filename = f"weather_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    client.put_object(
        Bucket="raw-data",
        Key=filename,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
    print(f"Uploaded {len(records)} records as {filename}")
    return filename


if __name__ == "__main__":
    records = generate_records()
    upload_to_minio(records)
