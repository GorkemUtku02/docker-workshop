# docker-workshop

A containerized ingestion pipeline that loads the NYC Yellow Taxi trip dataset into PostgreSQL.

## What it does

Downloads a monthly NYC Yellow Taxi CSV (gzipped, ~1.4M rows for 2021-01), streams it in chunks, and writes it into a PostgreSQL table with an explicit schema — no full-file load into memory.

The script is parameterized and packaged as a Docker image, so the same artifact can ingest any month into any table without a code change.

## Stack

| Component | Purpose |
|---|---|
| PostgreSQL 18 | Target database (containerized, named volume for persistence) |
| pgAdmin 4 | Web UI for browsing schemas and running queries |
| pandas | CSV parsing with explicit dtypes and chunked iteration |
| SQLAlchemy + psycopg 3 | Connection handling and `to_sql` writes |
| uv | Dependency resolution and locked environments |
| Docker Compose | Multi-container setup with a shared network |

## Project structure

```
docker-workshop/
├── pipeline/
│   ├── ingest_data.py        # the ingestion script
│   ├── notebook.ipynb        # exploration the script was derived from
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── pyproject.toml
│   └── uv.lock
├── test/
└── .gitignore
```

## Running it

### 1. Start the services

```bash
cd pipeline
docker compose up -d
```

This brings up PostgreSQL on `5432` and pgAdmin on `8085`. Compose creates its own network, so the containers resolve each other by service name.

### 2. Build the ingestion image

```bash
docker build -t taxi_ingest:v001 .
```

### 3. Run the ingestion

```bash
docker run -it --rm \
  --network=pipeline_default \
  taxi_ingest:v001 \
    --pg-user=root \
    --pg-pass=root \
    --pg-host=pgdatabase \
    --pg-port=5432 \
    --pg-db=ny_taxi \
    --target-table=yellow_taxi_trips_2021_1 \
    --year=2021 \
    --month=1 \
    --chunksize=100000
```

`--pg-host` is the **container name**, not `localhost`. Inside a container, `localhost` refers to that container itself — the database lives in a different one.

Running the script directly on the host instead? Then `localhost` is correct:

```bash
uv run python ingest_data.py --pg-host=localhost ...
```

### 4. Query the data

Via pgAdmin at `http://localhost:8085` (login `admin@admin.com` / `root`, then add a server with host `pgdatabase`), or from the terminal:

```bash
uv run pgcli -h localhost -p 5432 -u root -d ny_taxi
```

```sql
SELECT count(*) FROM yellow_taxi_trips_2021_1;
```

## Implementation notes

**Chunked ingestion.** `pd.read_csv(..., iterator=True, chunksize=100_000)` returns a lazy reader instead of a DataFrame. Only one chunk is held in memory at a time, so the pipeline's memory footprint stays flat regardless of file size.

**Explicit dtypes.** Column types are declared up front rather than inferred. Without this, timestamps land in Postgres as `TEXT` (breaking any date filtering or `DATE_TRUNC`) and integer IDs land as floats. Nullable `Int64` is used for columns containing NaN.

**Schema creation.** The first chunk writes `head(0)` with `if_exists='replace'` to create an empty table with the right schema, then every chunk appends. Leaving `replace` inside the loop would wipe the table on each iteration.

**Container networking.** The database and the ingestion job run in separate containers with separate network namespaces. They communicate over a shared Docker network using container names as hostnames.

## Data source

Yellow Taxi trip records:

```
https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_{year}-{month:02d}.csv.gz
```