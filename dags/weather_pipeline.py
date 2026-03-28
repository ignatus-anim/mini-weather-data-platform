from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import csv
import boto3
import psycopg2
from io import StringIO
from botocore.client import Config

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

MINIO_CONFIG = {
    "endpoint_url": "http://minio:9000",
    "aws_access_key_id": "minioadmin",
    "aws_secret_access_key": "minioadmin123",
    "config": Config(signature_version="s3v4"),
}

PG_CONFIG = {
    "host": "data-postgres",
    "port": 5432,
    "dbname": "salesdb",
    "user": "datauser",
    "password": "datapassword",
}


def generate_and_upload():
    import random
    from io import StringIO

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

    records = []
    base = datetime.now() - timedelta(days=1)
    for hour in range(24):
        for station_id, station_name, city in STATIONS:
            records.append({
                "station_id": station_id,
                "station_name": station_name,
                "city": city,
                "temperature_c": round(random.uniform(18.0, 38.0), 1),
                "humidity_pct": round(random.uniform(30.0, 95.0), 1),
                "wind_speed_kmh": round(random.uniform(0.0, 60.0), 1),
                "condition": random.choice(CONDITIONS),
                "recorded_at": (base + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
            })

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

    client = boto3.client("s3", **MINIO_CONFIG)
    filename = f"weather_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    client.put_object(
        Bucket="raw-data",
        Key=filename,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
    print(f"Uploaded {len(records)} records → raw-data/{filename}")
    return filename


def create_table():
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_readings (
            id              SERIAL PRIMARY KEY,
            station_id      VARCHAR(10),
            station_name    VARCHAR(100),
            city            VARCHAR(100),
            temperature_c   NUMERIC(5,1),
            humidity_pct    NUMERIC(5,1),
            wind_speed_kmh  NUMERIC(5,1),
            condition       VARCHAR(50),
            recorded_at     TIMESTAMP,
            loaded_at       TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Table weather_readings ready")


def process_and_load(**context):
    filename = context["ti"].xcom_pull(task_ids="generate_and_upload")

    client = boto3.client("s3", **MINIO_CONFIG)
    obj = client.get_object(Bucket="raw-data", Key=filename)
    content = obj["Body"].read().decode("utf-8")

    reader = csv.DictReader(StringIO(content))
    rows = []
    for row in reader:
        temp = float(row["temperature_c"])
        humidity = float(row["humidity_pct"])
        wind = float(row["wind_speed_kmh"])

        # basic validation / cleaning
        if not (-10 <= temp <= 60):
            continue
        if not (0 <= humidity <= 100):
            continue
        if wind < 0:
            continue

        rows.append((
            row["station_id"],
            row["station_name"],
            row["city"],
            round(temp, 1),
            round(humidity, 1),
            round(wind, 1),
            row["condition"].strip(),
            row["recorded_at"],
        ))

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO weather_readings
            (station_id, station_name, city, temperature_c, humidity_pct, wind_speed_kmh, condition, recorded_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, rows)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {len(rows)} records into weather_readings")


with DAG(
    dag_id="weather_pipeline",
    default_args=default_args,
    description="Weather data: MinIO → PostgreSQL",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["weather"],
) as dag:

    t1 = PythonOperator(task_id="generate_and_upload", python_callable=generate_and_upload)
    t2 = PythonOperator(task_id="create_table", python_callable=create_table)
    t3 = PythonOperator(task_id="process_and_load", python_callable=process_and_load, provide_context=True)

    t1 >> t2 >> t3
