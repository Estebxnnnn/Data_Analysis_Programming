-- TC-Analog Monitor - schema DRAFT (Workshop 1, updated with the 14 Nov 2026 profiling). PostgreSQL dialect.
-- Common tables follow the course data model; domain tables are TC-specific.
-- To be finalized in Workshop 2.

-- ------------------------------------------------------------ common tables
CREATE TABLE IF NOT EXISTS source (
    source_id      TEXT PRIMARY KEY,               -- e.g. 'ibtracs_since1980'
    name           TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('historical','incremental','optional_incremental')),
    url            TEXT NOT NULL,
    format         TEXT NOT NULL,
    license        TEXT,
    attribution    TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id         BIGSERIAL PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES source(source_id),
    mode           TEXT NOT NULL CHECK (mode IN ('historical','incremental')),
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    status         TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','success','failed')),
    partition_key  TEXT,                           -- e.g. '2005/WP' or '2024-09'
    raw_path       TEXT,
    rows_read      INTEGER DEFAULT 0,
    rows_inserted  INTEGER DEFAULT 0,
    rows_updated   INTEGER DEFAULT 0,
    rows_rejected  INTEGER DEFAULT 0,
    error_message  TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_state (
    source_id       TEXT PRIMARY KEY REFERENCES source(source_id),
    watermark_value TEXT,                          -- max datemodified / lastUpdate, ISO-8601 UTC
    etag            TEXT,
    last_modified   TEXT,
    content_hash    TEXT,
    last_run_id     BIGINT REFERENCES ingestion_run(run_id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS storm (
    sid            TEXT PRIMARY KEY,               -- IBTrACS storm identifier
    season         INTEGER NOT NULL,
    number         INTEGER,
    basin          TEXT NOT NULL,
    subbasin       TEXT,
    name           TEXT,
    atcf_ids       TEXT,                           -- may hold several ids joined by ':'
    first_fix_utc  TIMESTAMPTZ,
    last_fix_utc   TIMESTAMPTZ,
    max_wind_kt    REAL,
    min_pres_hpa   REAL,
    is_provisional BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS event_group (
    group_id       BIGSERIAL PRIMARY KEY,
    sid            TEXT REFERENCES storm(sid),     -- NULL until matched to a storm
    label          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event (
    event_id       TEXT PRIMARY KEY,               -- sha1(source|native id|time)
    source         TEXT NOT NULL REFERENCES source(source_id),
    event_type     TEXT NOT NULL CHECK (event_type IN ('tc_track_fix','tc_alert_episode','tc_advisory')),
    "timestamp"    TIMESTAMPTZ NOT NULL,
    latitude       DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude      DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude < 180),
    severity       REAL,                           -- max sustained wind, kt
    raw_reference  TEXT NOT NULL,
    group_id       BIGINT REFERENCES event_group(group_id),
    run_id         BIGINT REFERENCES ingestion_run(run_id),
    record_hash    TEXT NOT NULL,
    is_withdrawn   BOOLEAN NOT NULL DEFAULT FALSE,
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_event_time ON event ("timestamp");
CREATE INDEX IF NOT EXISTS ix_event_group ON event (group_id);

CREATE TABLE IF NOT EXISTS rejected_record (
    rejected_id    BIGSERIAL PRIMARY KEY,
    run_id         BIGINT REFERENCES ingestion_run(run_id),
    source_id      TEXT NOT NULL,
    reason         TEXT NOT NULL,
    payload        JSONB NOT NULL,
    rejected_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------ domain tables
CREATE TABLE IF NOT EXISTS tc_track_fix (
    event_id        TEXT PRIMARY KEY REFERENCES event(event_id),
    sid             TEXT NOT NULL REFERENCES storm(sid),
    nature          TEXT,                          -- DS, TS, ET, SS, NR, MX
    track_type      TEXT,                          -- main, PROVISIONAL, US-PROVISIONAL, spur-merge, spur-split, spur-other, US-PROVISIONAL_spur
    wmo_agency      TEXT,
    usa_agency      TEXT,
    wind_avg_period TEXT,                          -- '1-min' or agency-specific
    pressure_hpa    REAL,
    sshs_category   SMALLINT,                      -- -1..5, 1-min winds only
    storm_speed_kt  REAL,
    storm_dir_deg   REAL,
    dist2land_km    REAL,
    landfall_km     REAL,
    usa_record      TEXT,
    usa_status      TEXT,
    iflag           TEXT
);

CREATE TABLE IF NOT EXISTS tc_alert (
    event_id           TEXT PRIMARY KEY REFERENCES event(event_id),
    gdacs_eventid      BIGINT NOT NULL,
    episodeid          BIGINT NOT NULL,
    name               TEXT,
    alertlevel         TEXT CHECK (alertlevel IN ('Green','Orange','Red')),
    alertscore         REAL,
    episode_alertlevel TEXT,
    peak_wind_kt       REAL,                       -- GDACS severity: peak wind so far (km/h / 1.852)
    reporting_source   TEXT,                       -- JTWC, NOAA, RSMC (observed values)
    from_utc           TIMESTAMPTZ,
    to_utc             TIMESTAMPTZ,
    datemodified_utc   TIMESTAMPTZ,
    is_current         BOOLEAN,
    countries          TEXT,
    severity_text      TEXT,
    UNIQUE (gdacs_eventid, episodeid)
);

CREATE TABLE IF NOT EXISTS tc_advisory (               -- optional, NHC
    event_id          TEXT PRIMARY KEY REFERENCES event(event_id),
    nhc_id            TEXT NOT NULL,
    classification    TEXT,
    pressure_hpa      REAL,
    movement_dir_deg  REAL,
    movement_speed_kt REAL,
    public_adv_num    TEXT,
    forecast_track_url TEXT,
    cone_url          TEXT
);

CREATE TABLE IF NOT EXISTS storm_xref (
    xref_id        BIGSERIAL PRIMARY KEY,
    sid            TEXT NOT NULL REFERENCES storm(sid),
    atcf_id        TEXT,
    gdacs_eventid  BIGINT,
    nhc_id         TEXT,
    match_method   TEXT NOT NULL,                  -- 'atcf_id', 'spatiotemporal', 'manual'
    match_score    REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_storm_xref
    ON storm_xref (sid, match_method, COALESCE(gdacs_eventid, -1), COALESCE(nhc_id, ''));

CREATE TABLE IF NOT EXISTS analog_match (              -- Workshop 4
    current_sid        TEXT NOT NULL REFERENCES storm(sid),
    analog_sid         TEXT NOT NULL REFERENCES storm(sid),
    computed_at        TIMESTAMPTZ NOT NULL,
    similarity         REAL NOT NULL CHECK (similarity BETWEEN 0 AND 100),
    track_distance_km  REAL,
    intensity_diff_kt  REAL,
    rank               SMALLINT NOT NULL,
    PRIMARY KEY (current_sid, computed_at, rank)
);
