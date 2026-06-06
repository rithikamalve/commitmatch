-- CommitMatch RDS PostgreSQL Schema
-- Run once on a fresh db.t3.micro instance

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── DONORS ──────────────────────────────────────────────────────────────────
CREATE TABLE donors (
    user_id                  TEXT PRIMARY KEY,
    blood_group              TEXT,
    gender                   TEXT,
    latitude                 DOUBLE PRECISION,
    longitude                DOUBLE PRECISION,
    role                     TEXT,
    donor_type               TEXT,
    eligibility_status       TEXT,
    is_eligible              BOOLEAN GENERATED ALWAYS AS (
                                 LOWER(eligibility_status) LIKE '%eligible%'
                                 AND LOWER(eligibility_status) NOT LIKE '%ineligible%'
                             ) STORED,
    next_eligible_date       DATE,
    last_donation_date       DATE,
    last_contacted_date      DATE,
    donations_till_date      INTEGER,
    total_calls              INTEGER,
    calls_to_donations_ratio DOUBLE PRECISION,
    cycle_of_donations       INTEGER,
    frequency_in_days        INTEGER,
    user_donation_active_status TEXT,
    commitment_score         INTEGER,
    registration_date        DATE,
    phone_number             TEXT,
    preferred_language       TEXT DEFAULT 'Hindi',
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

-- ─── PATIENTS ────────────────────────────────────────────────────────────────
CREATE TABLE patients (
    bridge_id                    TEXT PRIMARY KEY,
    bridge_blood_group           TEXT,
    bridge_gender                TEXT,
    quantity_required            INTEGER,
    last_transfusion_date        DATE,
    expected_next_transfusion_date DATE,
    last_bridge_donation_date    DATE,
    latitude                     DOUBLE PRECISION,
    longitude                    DOUBLE PRECISION,
    status_of_bridge             BOOLEAN DEFAULT TRUE,
    created_at                   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── BLOOD REQUESTS ──────────────────────────────────────────────────────────
CREATE TABLE blood_requests (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_bridge_id    TEXT REFERENCES patients(bridge_id),
    required_date        DATE,
    status               TEXT DEFAULT 'open'
                             CHECK (status IN ('open','confirmed','cancelled','failed')),
    notes                TEXT,
    matched_donor_id     TEXT REFERENCES donors(user_id),
    standby_donor_id     TEXT REFERENCES donors(user_id),
    match_time_seconds   INTEGER,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ─── REQUEST DONOR RANKINGS ──────────────────────────────────────────────────
CREATE TABLE request_donor_rankings (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id           UUID REFERENCES blood_requests(id) ON DELETE CASCADE,
    donor_id             TEXT REFERENCES donors(user_id),
    rank                 INTEGER NOT NULL,
    commitment_score     INTEGER,
    signal_breakdown     JSONB,
    is_primary           BOOLEAN DEFAULT FALSE,
    is_standby           BOOLEAN DEFAULT FALSE,
    outreach_status      TEXT DEFAULT 'pending'
                             CHECK (outreach_status IN (
                                 'pending','sent','confirmed','declined',
                                 'amber','no_response','ready_to_send'
                             )),
    outreach_sent_at     TIMESTAMPTZ,
    response_received_at TIMESTAMPTZ,
    donor_reply_raw      TEXT,
    hesitation_detected  BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ─── INTERACTION LOG ─────────────────────────────────────────────────────────
CREATE TABLE interaction_log (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    donor_id     TEXT REFERENCES donors(user_id),
    request_id   UUID REFERENCES blood_requests(id),
    direction    TEXT CHECK (direction IN ('outbound','inbound')),
    message_body TEXT,
    sentiment    TEXT CHECK (sentiment IN ('confirmed','declined','hesitation','unclear')),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── FAILURE LOG ─────────────────────────────────────────────────────────────
CREATE TABLE failure_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID REFERENCES blood_requests(id),
    donor_id        TEXT REFERENCES donors(user_id),
    failure_reason  TEXT CHECK (failure_reason IN (
                        'no_response','declined','no_show','hesitation_undetected'
                    )),
    predicted_score INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── SHORTAGE ALERTS ─────────────────────────────────────────────────────────
CREATE TABLE shortage_alerts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_group          TEXT NOT NULL,
    city_cluster         TEXT DEFAULT 'Hyderabad',
    eligible_donor_count INTEGER,
    active_patient_count INTEGER,
    severity             TEXT CHECK (severity IN ('low','medium','critical')),
    resolved             BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ─── WEBSOCKET CONNECTIONS ───────────────────────────────────────────────────
CREATE TABLE ws_connections (
    connection_id  TEXT PRIMARY KEY,
    coordinator_id TEXT,
    connected_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── INDEXES ─────────────────────────────────────────────────────────────────
CREATE INDEX idx_donors_blood_group        ON donors(blood_group);
CREATE INDEX idx_donors_eligibility        ON donors(eligibility_status);
CREATE INDEX idx_blood_requests_status     ON blood_requests(status);
CREATE INDEX idx_rankings_request_id       ON request_donor_rankings(request_id);
CREATE INDEX idx_rankings_outreach_status  ON request_donor_rankings(outreach_status);
CREATE INDEX idx_interaction_log_donor     ON interaction_log(donor_id);
CREATE INDEX idx_interaction_log_request   ON interaction_log(request_id);
CREATE INDEX idx_shortage_alerts_resolved  ON shortage_alerts(resolved);
