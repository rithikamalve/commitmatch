"""
Demo seed script — populates the in-memory DynamoDB store (or real DynamoDB)
with representative data so judges can demo without needing AWS.

Usage:
    cd backend
    python ../scripts/seed_demo.py
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import config
import db
from data_loader import DataLoader
from matching.prioritizer import rank_donors_for_patient

CSV_PATH = os.environ.get("CSV_PATH", "data/Dataset.csv")
dl = DataLoader(CSV_PATH)


def _safe_str(v) -> str | None:
    if v is None:
        return None
    try:
        import pandas as pd
        if pd.isnull(v):
            return None
    except Exception:
        pass
    return str(v)


def seed_donors(n: int = 50):
    donors_df = dl.get_donors()
    valid = donors_df[
        donors_df["blood_group"].notna() &
        donors_df["latitude"].notna() &
        donors_df["longitude"].notna()
    ]
    selected = (
        valid.groupby("blood_group", group_keys=False)
             .apply(lambda g: g.head(max(1, n // 8)))
             .head(n)
    )

    inserted = 0
    demo_phones = [
        os.environ.get("DEMO_PHONE_1", "").replace("whatsapp:", ""),
        os.environ.get("DEMO_PHONE_2", "").replace("whatsapp:", ""),
    ]
    rows_list = list(selected.iterrows())

    for i, (_, row) in enumerate(rows_list):
        d = dl._row_to_dict(row)
        uid = str(d.get("user_id", ""))
        phone = demo_phones[i] if i < len(demo_phones) and demo_phones[i] else None

        db.put_item("donors", {
            "user_id":             uid,
            "blood_group":         d.get("blood_group"),
            "gender":              d.get("gender"),
            "latitude":            d.get("latitude"),
            "longitude":           d.get("longitude"),
            "eligibility_status":  d.get("eligibility_status"),
            "user_donation_active_status": d.get("user_donation_active_status"),
            "donations_till_date": d.get("donations_till_date"),
            "total_calls":         d.get("total_calls"),
            "calls_to_donations_ratio": d.get("calls_to_donations_ratio"),
            "cycle_of_donations":  d.get("cycle_of_donations"),
            "frequency_in_days":   d.get("frequency_in_days"),
            "last_donation_date":  _safe_str(d.get("last_donation_date")),
            "last_contacted_date": _safe_str(d.get("last_contacted_date")),
            "next_eligible_date":  _safe_str(d.get("next_eligible_date")),
            "registration_date":   _safe_str(d.get("registration_date")),
            "preferred_language":  "Hindi",
            "phone_number":        phone,
        }, pk="user_id")
        inserted += 1

    print(f"  Inserted {inserted} donors (in-memory store)")
    return inserted


def seed_patients(n: int = 5):
    patients_df = dl.get_patients()
    valid = patients_df[
        patients_df["bridge_blood_group"].notna() &
        patients_df["latitude"].notna() &
        patients_df["longitude"].notna()
    ]
    selected = valid.groupby("bridge_blood_group", group_keys=False).apply(lambda g: g.head(1)).head(n)

    inserted = 0
    for _, row in selected.iterrows():
        d = dl._row_to_dict(row)
        bid = str(d.get("bridge_id", ""))
        db.put_item("patients", {
            "bridge_id":           bid,
            "bridge_blood_group":  d.get("bridge_blood_group"),
            "quantity_required":   d.get("quantity_required"),
            "latitude":            d.get("latitude"),
            "longitude":           d.get("longitude"),
            "last_transfusion_date": _safe_str(d.get("last_transfusion_date")),
            "expected_next_transfusion_date": _safe_str(d.get("expected_next_transfusion_date")),
        }, pk="bridge_id")
        inserted += 1

    print(f"  Inserted {inserted} patients (in-memory store)")
    return inserted


def seed_requests():
    patients = db.scan_table("patients")[:3]
    donors_df = dl.get_donors()

    statuses       = ["confirmed", "open", "open"]
    amber_request  = 2   # request index that gets amber alert

    for i, p in enumerate(patients):
        patient = dl.get_patient_by_id(p["bridge_id"])
        if patient is None:
            patient = {"bridge_blood_group": p.get("bridge_blood_group"),
                       "latitude": 17.39, "longitude": 78.47}

        ranked = rank_donors_for_patient(donors_df, patient, top_n=5)
        if not ranked:
            continue

        status = statuses[i]
        req_id = db.put_item("requests", {
            "patient_bridge_id": p["bridge_id"],
            "required_date":     "2026-06-12",
            "status":            status,
            "match_time_seconds": 312,
        })

        for r in ranked:
            out_status  = "pending"
            hesitation  = False
            if i == amber_request and r["rank"] == 1:
                out_status = "amber"
                hesitation = True
            elif i == 0 and r["rank"] == 1:
                out_status = "confirmed"

            db.put_item("rankings", {
                "request_id":       req_id,
                "donor_id":         r["donor_id"],
                "rank":             r["rank"],
                "commitment_score": r["score"],
                "confidence":       r.get("confidence", "low"),
                "signal_breakdown": json.dumps(r.get("signals", {})),
                "reasons":          r.get("reasons", []),
                "flags":            r.get("flags", []),
                "is_primary":       r["is_primary"],
                "is_standby":       r["is_standby"],
                "outreach_status":  out_status,
                "hesitation_detected": hesitation,
                "donor_reply_raw":  "dekhunga traffic hai" if hesitation else None,
            })

        print(f"  Request {req_id[:8]}… status={status}, top={ranked[0]['donor_id'][:10]}")


def seed_shortage_alerts():
    alerts = [
        ("O Negative",  2, 4, "critical"),
        ("AB Negative", 1, 2, "critical"),
        ("B Negative",  4, 5, "medium"),
        ("O Positive",  5, 8, "medium"),
        ("A Negative",  3, 3, "medium"),
    ]
    for bg, donors, patients, severity in alerts:
        db.put_item("shortage_alerts", {
            "blood_group":         bg,
            "city_cluster":        "Hyderabad",
            "eligible_donor_count": donors,
            "active_patient_count": patients,
            "severity":            severity,
            "resolved":            False,
        })
    print(f"  Inserted {len(alerts)} shortage alerts")


def main():
    print("CommitMatch Demo Seed Script v2.0")
    print("=" * 42)
    print(f"  Mode:     {'DEMO (in-memory)' if config.DEMO_MODE else 'PRODUCTION (DynamoDB)'}")
    print(f"  CSV:      {CSV_PATH}")
    print()

    print("[1/4] Seeding donors…")
    n_donors = seed_donors(50)

    print("[2/4] Seeding patients…")
    n_patients = seed_patients(5)

    print("[3/4] Creating demo blood requests…")
    seed_requests()

    print("[4/4] Creating shortage alerts…")
    seed_shortage_alerts()

    # Show demo donor phones
    donors_with_phones = [
        d for d in db.scan_table("donors") if d.get("phone_number")
    ]

    print()
    print("=" * 42)
    print(f"Seeded: {n_donors} donors | {n_patients} patients | 3 requests | 5 shortage alerts")
    print("Demo WhatsApp numbers:")
    for d in donors_with_phones[:3]:
        print(f"  {d['user_id']}: {d['phone_number']}")
    print(f"Dashboard:  {config.FRONTEND_URL}")
    print(f"API health: http://localhost:{config.PORT}/health")


if __name__ == "__main__":
    main()
