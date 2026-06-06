"""
Chain Health Monitor.

A "chain" is a thalassemia patient (bridge_id) + their pool of compatible donors.
Chain health = how many currently eligible, non-churn-risk donors are available right now.

Status:
  critical — fewer than 2 eligible donors
  warning  — fewer than 4 eligible donors
  healthy  — 4 or more eligible donors
"""
from matching.eligibility import is_eligible
from engagement.churn_detection import assess_churn_risk

CRITICAL_THRESHOLD = 2
WARNING_THRESHOLD  = 4


def assess_chain_health(patient: dict, donors_df) -> dict:
    eligible, at_risk, ineligible = [], [], []

    for _, row in donors_df.iterrows():
        donor = row.to_dict()
        ok, _ = is_eligible(donor, patient)
        if ok:
            churn = assess_churn_risk(donor)
            if churn["risk_level"] in ("High", "Medium"):
                at_risk.append(str(donor.get("user_id", "")))
            else:
                eligible.append(str(donor.get("user_id", "")))
        else:
            ineligible.append(str(donor.get("user_id", "")))

    total_eligible = len(eligible) + len(at_risk)

    if total_eligible < CRITICAL_THRESHOLD:
        status = "critical"
    elif total_eligible < WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "healthy"

    return {
        "patient_id":           patient.get("bridge_id", ""),
        "blood_group":          patient.get("bridge_blood_group", ""),
        "status":               status,
        "eligible_count":       len(eligible),
        "at_risk_count":        len(at_risk),
        "ineligible_count":     len(ineligible),
        "total_donors_checked": len(eligible) + len(at_risk) + len(ineligible),
        "needs_attention":      status in ("critical", "warning"),
    }


def get_all_chain_health(data_loader) -> list[dict]:
    """Returns chain health for every active patient, sorted critical-first."""
    patients_df = data_loader.get_patients()
    donors_df   = data_loader.get_donors()
    results = []

    for _, row in patients_df.iterrows():
        patient = row.to_dict()
        if not patient.get("bridge_blood_group"):
            continue
        results.append(assess_chain_health(patient, donors_df))

    results.sort(
        key=lambda x: {"critical": 0, "warning": 1, "healthy": 2}.get(x["status"], 3)
    )
    return results


def get_chain_health_summary(data_loader) -> dict:
    """Aggregate summary for the analytics dashboard."""
    chains = get_all_chain_health(data_loader)
    return {
        "total_chains":    len(chains),
        "critical":        sum(1 for c in chains if c["status"] == "critical"),
        "warning":         sum(1 for c in chains if c["status"] == "warning"),
        "healthy":         sum(1 for c in chains if c["status"] == "healthy"),
        "needs_attention": sum(1 for c in chains if c["needs_attention"]),
        "chains":          chains,
    }
