# Mini Weather Data Platform

A containerized end-to-end data platform that collects, processes, stores, and visualizes weather data using Docker Compose.

## Architecture

```
CSV Generation → MinIO (raw-data) → Airflow DAG → PostgreSQL → Metabase
```

| Service | Role | Port |
|---|---|---|
| MinIO | File storage (data lake) | 9000 / 9001 |
| Apache Airflow | Pipeline orchestration | 8081 |
| PostgreSQL | Data warehouse | 5433 |
| Metabase | BI dashboards | 3000 |

## Project Structure

```
module10/
├── dags/
│   └── weather_pipeline.py     # Airflow DAG
├── data/
│   └── generate_weather.py     # Standalone data generator
├── images/                     # Screenshots
├── docker-compose.yml
├── requirements.txt
├── .env
└── .gitignore
```

## Prerequisites

- Docker & Docker Compose installed
- Ports 3000, 5433, 8081, 9000, 9001 available

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd module10
```

### 2. Set directory permissions for Airflow

```bash
sudo chown -R 50000:0 logs/ plugins/ dags/ data/
```

### 3. Start all services

```bash
docker compose up -d
```

First run will take a few minutes to pull images. Wait until all containers are healthy:

```bash
docker compose ps
```

### 4. Verify services are running

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8081 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| Metabase | http://localhost:3000 | set on first visit |
| PostgreSQL | localhost:5433 | datauser / datapassword / salesdb |

---

## Running the Pipeline

### Trigger the DAG manually

1. Open Airflow at **http://localhost:8081**
2. Find the `weather_pipeline` DAG
3. Click the ▶ **Trigger** button

The DAG runs 3 tasks in sequence:

```
generate_and_upload → create_table → process_and_load
```

- `generate_and_upload` — generates 192 weather records (8 stations × 24 hours) and uploads a CSV to MinIO `raw-data` bucket
- `create_table` — creates the `weather_readings` table in PostgreSQL if it doesn't exist
- `process_and_load` — reads the CSV from MinIO, validates and cleans each row, inserts into PostgreSQL

### Verify data loaded

```bash
docker exec -it data-postgres psql -U datauser -d salesdb -c "SELECT COUNT(*) FROM weather_readings;"
```

---

## Screenshots

### Airflow DAG

![Airflow Dashboard](images/airflow%20dashboard.png)

### MinIO — Raw Data Bucket

![MinIO Dashboard](images/minio%20dashboard.png)

### Generated CSV in MinIO

![Generated CSV](images/generated%20data%20csv.png)

### Data in Metabase

![Data in Metabase](images/data%20in%20metabase.png)

### Metabase Analytics Overview

![Metabase Analytics](images/list%20of%20analytics_metabase.png)

### Average Temperature by City

![Avg Temp by City](images/avg%20temp%20by%20city.png)

### Average Temperature Over Time

![Avg Temp Over Time](images/avg%20temp%20by%20time.png)

### Weather Condition Distribution

![Count by Condition](images/count%20by%20condition.png)

---

## Data Schema

Table: `weather_readings`

| Column | Type | Description |
|---|---|---|
| id | SERIAL | Primary key |
| station_id | VARCHAR | Weather station ID |
| station_name | VARCHAR | Station name |
| city | VARCHAR | City name |
| temperature_c | NUMERIC | Temperature in Celsius |
| humidity_pct | NUMERIC | Humidity percentage |
| wind_speed_kmh | NUMERIC | Wind speed in km/h |
| condition | VARCHAR | Weather condition |
| recorded_at | TIMESTAMP | Reading timestamp |
| loaded_at | TIMESTAMP | Pipeline load timestamp |

## Stopping the Platform

```bash
docker compose down
```

To also remove all data volumes:

```bash
docker compose down -v
```
