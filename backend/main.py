import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
import db as _db
from data_loader import DataLoader
from routers import analytics, copilot, donors, match, patients, requests, webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _auto_seed(data_loader):
    """Seed demo data into the in-memory store at startup."""
    import json
    from datetime import datetime, timezone
    from matching.prioritizer import rank_donors_for_patient

    donors_df   = data_loader.get_donors()
    patients_df = data_loader.get_patients()

    if donors_df.empty or patients_df.empty:
        logger.warning("Auto-seed skipped — CSV not loaded")
        return

    # Pick up to 5 patients with valid data
    valid_patients = patients_df[
        patients_df["bridge_blood_group"].notna() &
        patients_df["latitude"].notna()
    ].head(5)

    seeded_requests = 0
    for i, (_, prow) in enumerate(valid_patients.iterrows()):
        patient = data_loader._row_to_dict(prow)
        ranked  = rank_donors_for_patient(donors_df, patient, top_n=5)
        if not ranked:
            continue

        statuses   = ["confirmed", "open", "open", "open", "open"]
        status     = statuses[i]
        req_id     = _db.put_item("requests", {
            "patient_bridge_id": str(patient.get("bridge_id", "")),
            "required_date":     "2026-06-15",
            "status":            status,
            "match_time_seconds": 280,
            "created_at":        datetime.now(timezone.utc).isoformat(),
        })

        for r in ranked:
            out_status = "pending"
            hesitation = False
            if i == 2 and r["rank"] == 1:     # third request gets amber alert
                out_status = "amber"
                hesitation = True
            elif i == 0 and r["rank"] == 1:   # first request confirmed
                out_status = "confirmed"

            _db.put_item("rankings", {
                "request_id":        req_id,
                "donor_id":          r["donor_id"],
                "rank":              r["rank"],
                "commitment_score":  r["score"],
                "confidence":        r.get("confidence", "low"),
                "signal_breakdown":  json.dumps(r.get("signals", {})),
                "reasons":           r.get("reasons", []),
                "flags":             r.get("flags", []),
                "is_primary":        r["is_primary"],
                "is_standby":        r["is_standby"],
                "outreach_status":   out_status,
                "hesitation_detected": hesitation,
                "donor_reply_raw":   "dekhunga traffic hai" if hesitation else None,
            })
        seeded_requests += 1

    # Shortage alerts
    for bg, donors_n, patients_n, severity in [
        ("O Negative", 2, 4, "critical"),
        ("AB Negative", 1, 2, "critical"),
        ("B Negative", 4, 5, "medium"),
    ]:
        _db.put_item("shortage_alerts", {
            "blood_group": bg, "city_cluster": "Hyderabad",
            "eligible_donor_count": donors_n,
            "active_patient_count": patients_n,
            "severity": severity, "resolved": False,
        })

    logger.info("Auto-seed complete: %d requests, 3 shortage alerts", seeded_requests)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CommitMatch starting — DEMO_MODE=%s", config.DEMO_MODE)

    # Data layer (CSV → pandas, always available)
    app.state.data_loader = DataLoader(config.CSV_PATH)

    # DynamoDB — real tables in prod, in-memory store in demo
    if not config.DEMO_MODE:
        try:
            _db.create_tables_if_missing()
            logger.info("DynamoDB tables verified")
        except Exception as e:
            logger.warning("DynamoDB setup skipped: %s", e)
    else:
        logger.info("Demo mode: using in-memory DynamoDB substitute")
        _auto_seed(app.state.data_loader)

    yield

    logger.info("CommitMatch shut down")


app = FastAPI(
    title="CommitMatch API",
    version="2.0.0",
    description=(
        "AI-powered blood donor prioritization for Blood Warriors NGO. "
        "Layer 1: deterministic prioritizer. "
        "Layer 2: engagement + memory. "
        "Layer 3: Claude via Bedrock (language only — never ranking)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match.router,     tags=["matching"])
app.include_router(requests.router,  tags=["requests"])
app.include_router(donors.router,    tags=["donors"])
app.include_router(patients.router,  tags=["patients"])
app.include_router(webhook.router,   tags=["webhook"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(copilot.router,   tags=["copilot"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Local WebSocket endpoint — replaces API Gateway for dev/demo."""
    from websocket.manager import manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()   # keeps connection alive; ignores client messages
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "demo_mode": config.DEMO_MODE,
        "version":   "2.0.0",
        "layers": {
            "layer1": "Donor Prioritization Engine (deterministic, no LLM)",
            "layer2": "Engagement + Memory (DynamoDB-backed donor profiles)",
            "layer3": "Claude via Bedrock (outreach language + hesitation detection)",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
