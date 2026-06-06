"""
Creates data/Dataset_demo.csv by augmenting the real Dataset.csv.

Real data preserved: user_id, bridge_id, blood_group, bridge_blood_group, gender,
                     bridge_gender, role, quantity_required, transfusion dates,
                     registration_date, eligibility_status, inactive_trigger_comment.

Synthesized (realistic distributions): calls_to_donations_ratio, donations_till_date,
total_calls, last_donation_date, last_contacted_date, cycle_of_donations,
latitude, longitude, user_donation_active_status, next_eligible_date.
"""
import random
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ── Hyderabad neighbourhood centroids ─────────────────────────────────────────
HYDERABAD_CLUSTERS = [
    (17.3922792, 78.4602749),  # Blood Warriors / default
    (17.4156,    78.4347),     # Banjara Hills
    (17.4331,    78.4069),     # Jubilee Hills
    (17.4489,    78.3882),     # Madhapur
    (17.4401,    78.3489),     # Gachibowli
    (17.4731,    78.3688),     # Kondapur
    (17.4854,    78.4138),     # Kukatpally
    (17.3692,    78.5257),     # Dilsukhnagar
    (17.3616,    78.4747),     # Charminar
    (17.3929,    78.4374),     # Mehdipatnam
    (17.5001,    78.3667),     # Miyapur
    (17.4399,    78.4983),     # Secunderabad
]

def jitter_coords(lat, lon, radius_km=1.5):
    """Add a small random offset within radius_km."""
    deg_per_km = 1 / 111
    dlat = random.uniform(-radius_km, radius_km) * deg_per_km
    dlon = random.uniform(-radius_km, radius_km) * deg_per_km / math.cos(math.radians(lat))
    return round(lat + dlat, 7), round(lon + dlon, 7)

def rand_cluster():
    base = random.choice(HYDERABAD_CLUSTERS)
    return jitter_coords(*base)

def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()

# ── Donor archetypes ──────────────────────────────────────────────────────────
# Each archetype: (probability, config_dict)
ARCHETYPES = [
    # Champion — shows up reliably, many donations, recent
    (0.12, dict(
        ratio_range=(0.3, 1.0), donations_range=(8, 15),
        active="Active", eligible="eligible",
        cycle=90, calls_range=(4, 12),
        last_don_days=(20, 90), last_con_days=(7, 60),
    )),
    # Regular — reliable, several donations, somewhat recent
    (0.20, dict(
        ratio_range=(1.0, 2.0), donations_range=(3, 8),
        active="Active", eligible="eligible",
        cycle=90, calls_range=(3, 10),
        last_don_days=(60, 200), last_con_days=(30, 150),
    )),
    # Occasional — donates sometimes, contact a few months ago
    (0.22, dict(
        ratio_range=(2.0, 5.0), donations_range=(1, 4),
        active="Active", eligible="eligible",
        cycle=90, calls_range=(2, 8),
        last_don_days=(180, 400), last_con_days=(90, 350),
    )),
    # Hard to reach — called many times, few donations
    (0.18, dict(
        ratio_range=(5.0, 20.0), donations_range=(1, 2),
        active="Active", eligible="eligible",
        cycle=120, calls_range=(5, 20),
        last_don_days=(300, 700), last_con_days=(180, 500),
    )),
    # Lapsed — was active, now inactive
    (0.15, dict(
        ratio_range=(3.0, 15.0), donations_range=(1, 3),
        active="Inactive", eligible="eligible",
        cycle=0, calls_range=(2, 15),
        last_don_days=(400, 900), last_con_days=(365, 800),
    )),
    # New / first-time — registered recently, little history
    (0.13, dict(
        ratio_range=(0.0, 1.0), donations_range=(0, 1),
        active="Active", eligible="eligible",
        cycle=0, calls_range=(0, 2),
        last_don_days=None, last_con_days=(0, 30),  # None means no donation yet
    )),
]

def pick_archetype():
    probs = [a[0] for a in ARCHETYPES]
    idx = np.random.choice(len(ARCHETYPES), p=probs)
    return ARCHETYPES[idx][1]

def synthesize_donor_fields(cfg: dict) -> dict:
    donations = random.randint(*cfg["donations_range"])
    calls     = random.randint(*cfg["calls_range"])
    calls     = max(calls, donations)  # can't have fewer calls than donations

    if donations > 0:
        ratio = round(calls / donations, 2)
    else:
        ratio = None  # truly new donor with no data

    # last_donation_date
    if cfg["last_don_days"] and donations > 0:
        d_days = random.randint(*cfg["last_don_days"])
        last_don = days_ago(d_days)
    else:
        last_don = None

    # last_contacted_date
    if cfg["last_con_days"]:
        c_days = random.randint(*cfg["last_con_days"])
        last_con = days_ago(c_days)
    else:
        last_con = None

    # next_eligible_date: 90 days after last donation
    if last_don:
        ned = (date.fromisoformat(last_don) + timedelta(days=90)).isoformat()
    else:
        ned = None

    # lat/lon: 70% from a Hyderabad cluster, 30% same default
    if random.random() < 0.70:
        lat, lon = rand_cluster()
    else:
        lat, lon = 17.3922792, 78.4602749

    return {
        "user_donation_active_status": cfg["active"],
        "eligibility_status":          cfg["eligible"],
        "calls_to_donations_ratio":    ratio,
        "donations_till_date":         donations if donations > 0 else None,
        "total_calls":                 calls,
        "cycle_of_donations":          cfg["cycle"],
        "frequency_in_days":           cfg["cycle"] if cfg["cycle"] > 0 else 0,
        "last_donation_date":          last_don,
        "last_contacted_date":         last_con,
        "next_eligible_date":          ned,
        "latitude":                    lat,
        "longitude":                   lon,
    }

# ── Load and augment ──────────────────────────────────────────────────────────

root = Path(__file__).parent.parent
src  = root / "data" / "Dataset.csv"
dst  = root / "data" / "Dataset_demo.csv"

df = pd.read_csv(src, low_memory=False)

REAL_COLS = [
    "user_id", "bridge_id", "role", "role_status", "bridge_status",
    "blood_group", "gender", "bridge_gender", "bridge_blood_group",
    "quantity_required", "last_transfusion_date", "expected_next_transfusion_date",
    "registration_date", "donor_type", "status", "donated_earlier",
    "last_bridge_donation_date", "status_of_bridge", "inactive_trigger_comment",
]
SYNTH_COLS = [
    "user_donation_active_status", "eligibility_status",
    "calls_to_donations_ratio", "donations_till_date", "total_calls",
    "cycle_of_donations", "frequency_in_days",
    "last_donation_date", "last_contacted_date", "next_eligible_date",
    "latitude", "longitude",
]

donors   = df[df["bridge_id"].isna()].copy()
patients = df[df["bridge_id"].notna()].copy()

print(f"Original: {len(donors)} donors, {len(patients)} patients")

# Synthesize behavioral fields for every donor
synth_rows = [synthesize_donor_fields(pick_archetype()) for _ in range(len(donors))]
synth_df   = pd.DataFrame(synth_rows, index=donors.index)

# Preserve eligibility_status for the "not eligible" donors (357 real ones)
# so the eligibility gate still filters them correctly
not_eligible_mask = donors["eligibility_status"].str.lower() == "not eligible"
synth_df.loc[not_eligible_mask, "eligibility_status"] = "not eligible"
synth_df.loc[not_eligible_mask, "user_donation_active_status"] = "Inactive"

# Replace synthesized cols in the donor rows
for col in SYNTH_COLS:
    donors[col] = synth_df[col]

# Give patients varied coordinates too (real patient lat/lon from their area)
patient_synth = []
for _, row in patients.iterrows():
    if random.random() < 0.60:
        lat, lon = rand_cluster()
    else:
        lat, lon = 17.3922792, 78.4602749
    patient_synth.append({"latitude": lat, "longitude": lon})

patients["latitude"]  = [p["latitude"]  for p in patient_synth]
patients["longitude"] = [p["longitude"] for p in patient_synth]

augmented = pd.concat([donors, patients], ignore_index=True)
augmented.to_csv(dst, index=False)

# ── Stats ─────────────────────────────────────────────────────────────────────
print(f"Written: {dst}")
print(f"\nDonor stats after augmentation:")
for col in ["user_donation_active_status", "eligibility_status", "cycle_of_donations"]:
    print(f"  {col}: {donors[col].value_counts().to_dict()}")
print(f"  calls_to_donations_ratio null: {donors['calls_to_donations_ratio'].isna().mean()*100:.1f}%")
print(f"  donations_till_date dist: {donors['donations_till_date'].value_counts().head(6).to_dict()}")
print(f"  unique lat/lon pairs: {len(donors[['latitude','longitude']].drop_duplicates())}")
