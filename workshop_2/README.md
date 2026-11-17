# Workshop 2 — Technical Architecture and Bronze/Silver Pipeline

| Deliverable | Location |
| --- | --- |
| Technical Architecture and Pipeline Report (PDF) | `workshop_2/report/` (added after the runs) |
| `docker-compose.yml` | repository root |
| Custom Airflow image | `airflow/Dockerfile`, `airflow/requirements-airflow.txt` |
| Bronze ingestion DAG | `airflow/dags/bronze_ingestion_dag.py` |
| Silver processing DAG | `airflow/dags/silver_processing_dag.py` |
| Supporting modules | `src/tcmon/pipeline/` (bronze, silver, schema, paths), `src/tcmon/sources/`, `src/tcmon/normalization/` |
| Preprocessing specification | [`preprocessing_spec.md`](preprocessing_spec.md) |
| Bronze samples (≥ 3 runs) | `datalake_bronze/*.json` |
| Silver samples (≥ 3 files) | `datalake_silver/*.parquet` |
| Silver exploration notebook | `notebooks/02_silver_exploration.ipynb` |
| Evidence (screenshots) | `workshop_2/evidence/` |

## How to run the stack (Windows, `cmd`, from the repository folder)

Requirements: Docker Desktop with WSL 2, about 3.5 GB of memory for Docker, port 8080 free.
Close memory-heavy applications (browser tabs, chat apps) while the stack runs.

```bat
copy .env.example .env
docker compose build
docker compose up airflow-init
docker compose up -d
docker compose ps
```

1. `docker compose build` builds the custom image (first time: 5–15 min).
2. `docker compose up airflow-init` migrates the metadata database and creates the admin user; it ends with `exited with code 0`.
3. `docker compose up -d` starts PostgreSQL, the webserver, the scheduler and the triggerer.
4. `docker compose ps` must show the services as `healthy` (1–2 min after start).
5. Open <http://localhost:8080> — user `airflow`, password `airflow`.

## How to run the DAGs

1. In the DAG list, switch **on** (unpause) `bronze_ingestion` and `silver_processing`.
2. Trigger `bronze_ingestion` with ▶ (*Trigger DAG*). It runs every hour on its own afterwards.
3. When it finishes (all tasks green), trigger `silver_processing` with ▶, or wait for its next 15-minute run.
   The FileSensor finds the new run manifest and the Parquet file appears in `datalake_silver/`.
4. Repeat until there are at least three Bronze runs and three Silver files. Spreading the Bronze runs
   over a few hours gives Silver files with new records; runs a few minutes apart produce Silver files
   with 0 rows, because identical records are removed by the cross-batch deduplication (expected behaviour).

## Verification

```bat
docker compose exec airflow-scheduler python -m pytest -q /opt/airflow/tests/test_pipeline.py
docker compose exec airflow-scheduler jupyter nbconvert --to notebook --execute --inplace /opt/airflow/notebooks/02_silver_exploration.ipynb
```

Stop the stack with `docker compose down` (data stays in the `datalake_*` folders; the metadata database
stays in the `postgres-db-volume` volume).

## Screenshots to collect (`workshop_2/evidence/`)

| # | Screenshot | Where |
| --- | --- | --- |
| 01 | `docker compose ps` with all services healthy | `cmd` |
| 02 | Docker Desktop, Containers view with the stack running | Docker Desktop |
| 03 | Airflow DAG list with both DAGs active | Airflow UI, *DAGs* |
| 04 | `bronze_ingestion` Graph view | DAG → *Graph* |
| 05 | `bronze_ingestion` Grid view with ≥ 3 successful runs | DAG → *Grid* |
| 06 | Log of `extract_api_gdacs` (HTTP 200 and feature count) | task → *Logs* |
| 07 | Log of `validate_ibtracs` (validation report) | task → *Logs* |
| 08 | `silver_processing` Graph view | DAG → *Graph* |
| 09 | `silver_processing` Grid view with ≥ 3 successful runs | DAG → *Grid* |
| 10 | Log of `wait_for_bronze_files` showing the file found | task → *Logs* |
| 11 | Log of `verify_parquet` with the first rows | task → *Logs* |
| 12 | `datalake_bronze/` and `datalake_silver/` folders in the file explorer | Windows Explorer |
| 13 | Output of the pytest command | `cmd` |
