# Architecture Overview (draft)

Adapted from the common technical contract (Docker Compose: database, ingestion application, orchestrator, dashboard). **Check against the reference architecture in the Course Project document.** Rendered image: [`architecture.png`](architecture.png).

```mermaid
flowchart LR
    subgraph Sources
        S1[S1 IBTrACS since1980<br/>CSV, historical]
        S2[S2 GDACS TC archive<br/>REST GeoJSON, historical]
        S3[S3 IBTrACS ACTIVE<br/>CSV + ETag, incremental]
        S4[S4 GDACS TC current<br/>REST GeoJSON, incremental]
        S5[S5 NHC CurrentStorms.json<br/>optional, AL/EP only]
    end
    subgraph Ingestion["Ingestion app: python ingest.py"]
        H[--mode historical<br/>partitioned bulk load]
        I[--mode incremental<br/>watermark polling]
        R[(data/raw<br/>landing zone)]
        N[Normalization + validation<br/>UTC, WGS84, kt]
        Q[Quarantine<br/>rejected_record]
    end
    O[Orchestrator<br/>scheduler]
    DB[(PostgreSQL<br/>event + domain tables<br/>ingestion_run / state)]
    A[Analysis<br/>cross-source matching<br/>SAS analog indicator]
    D[Plotly Dash<br/>localhost:8050]
    S1 --> H
    S2 --> H
    S3 --> I
    S4 --> I
    S5 -.-> I
    O --> H
    O --> I
    H --> R
    I --> R
    R --> N
    N --> DB
    N --> Q
    Q --> DB
    DB --> A
    A --> DB
    DB --> D
```

| Component | Responsibility | Workshop |
| --- | --- | --- |
| Source adapters (`src/tcmon/sources`) | Download raw responses, parse CSV / GeoJSON / JSON | 1 (done), 2 |
| Raw landing zone (`data/raw`) | Unmodified responses + `.meta.json` | 1 (done) |
| Normalization (`src/tcmon/normalization`) | Canonical event, units, UTC, WGS84 | 1 (draft), 2 |
| Storage (`src/tcmon/storage`, `sql/`) | Upserts, ingestion_run/state, quarantine | 2 |
| Orchestrator | Schedules from `config/sources.yaml` | 3 |
| Analysis | Matching, event groups, SAS indicator | 3, 4 |
| Dashboard (`dashboard/`) | Plotly Dash at localhost:8050 | 4 |
