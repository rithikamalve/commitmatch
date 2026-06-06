from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Match ──────────────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    patient_id:    str
    required_date: Optional[date] = None
    notes:         Optional[str]  = None


class RankedDonor(BaseModel):
    donor_id:                  str
    donor_name:                str                    = ""
    blood_group:               Optional[str]          = None
    rank:                      int
    commitment_score:          int
    confidence:                str                    = "low"   # high|medium|low
    is_primary:                bool
    is_standby:                bool
    latitude:                  Optional[float]        = None
    longitude:                 Optional[float]        = None
    eligibility_status:        Optional[str]          = None
    next_eligible_date:        Optional[str]          = None
    total_donations:           int                    = 0
    calls_to_donations_ratio:  Optional[float]        = None
    outreach_status:           str                    = "pending"
    hesitation_detected:       bool                   = False
    donor_reply_raw:           Optional[str]          = None
    signals:                   dict[str, int]         = Field(default_factory=dict)
    # New explainability fields
    reasons:                   list[str]              = Field(default_factory=list)
    flags:                     list[str]              = Field(default_factory=list)
    # Memory fields
    lifetime_show_rate:        Optional[float]        = None
    memory_summary:            str                    = ""
    phone_number:              Optional[str]          = None
    last_donation_date:        Optional[str]          = None
    frequency_in_days:         int                    = 0
    cycle_of_donations:        int                    = 0
    user_donation_active_status: str                  = ""
    preferred_language:        str                    = "Hindi"
    donor_type:                Optional[str]          = None
    role:                      Optional[str]          = None
    distance_km:               Optional[float]        = None
    est_travel_min:            Optional[int]          = None


class MatchResponse(BaseModel):
    request_id:      str
    patient_id:      str
    ranked_donors:   list[RankedDonor]
    message_preview: Optional[str] = None
    match_time_ms:   int


# ── Blood Requests ─────────────────────────────────────────────────────────

class BloodRequest(BaseModel):
    id:               str
    patient_bridge_id: Optional[str]     = None
    required_date:    Optional[Any]      = None
    status:           str
    notes:            Optional[str]      = None
    matched_donor_id: Optional[str]      = None
    standby_donor_id: Optional[str]      = None
    match_time_seconds: Optional[int]    = None
    created_at:       Optional[Any]      = None
    updated_at:       Optional[Any]      = None
    patient_blood_group: Optional[str]   = None
    top_donor:        Optional[RankedDonor] = None
    has_amber_alert:  bool               = False


class InteractionEntry(BaseModel):
    id:           str
    direction:    str
    message_body: Optional[str]  = None
    sentiment:    Optional[str]  = None
    created_at:   Optional[Any]  = None


class BloodRequestDetail(BaseModel):
    request:       BloodRequest
    ranked_donors: list[RankedDonor]
    timeline:      list[InteractionEntry]
    ai_summary:    str = ""


# ── Engagement ─────────────────────────────────────────────────────────────

class EngagementAssessment(BaseModel):
    ready_now:           bool
    window_open:         bool
    days_until_window:   Optional[int]  = None
    predicted_next_date: Optional[str]  = None
    confidence:          str            = "unknown"
    priority_label:      str            = "unknown"
    reasoning:           str            = ""


# ── Donor Score ────────────────────────────────────────────────────────────

class DonorScore(BaseModel):
    donor_id:           str
    commitment_score:   int
    confidence:         str                    = "low"
    signals:            dict[str, int]
    reasons:            list[str]              = Field(default_factory=list)
    flags:              list[str]              = Field(default_factory=list)
    engagement:         EngagementAssessment
    eligibility_status: Optional[str]          = None
    blood_group:        Optional[str]          = None
    total_donations:    int                    = 0
    lifetime_show_rate: Optional[float]        = None
    memory_summary:     str                    = ""


# ── Analytics ──────────────────────────────────────────────────────────────

class AnalyticsSupplyDemand(BaseModel):
    blood_group:     str
    eligible_donors: int
    active_patients: int
    gap:             int


class ChurnRiskDonor(BaseModel):
    donor_id:           str
    donor_name:         str            = ""
    blood_group:        Optional[str]  = None
    days_since_contact: int
    total_donations:    int
    risk_level:         str
    churn_reason:       str            = ""


class ShortageAlert(BaseModel):
    id:                   str
    blood_group:          str
    city_cluster:         str           = "Hyderabad"
    eligible_donor_count: int
    active_patient_count: int
    severity:             str
    resolved:             bool
    created_at:           Optional[Any] = None


class NetworkHealth(BaseModel):
    total_donors:              int
    pct_eligible:              float
    pct_active:                float
    pct_with_donation_history: float
    pct_complete_profile:      float
    avg_commitment_score:      float


class ChainHealth(BaseModel):
    patient_id:           str
    blood_group:          Optional[str] = None
    status:               str           # critical | warning | healthy
    eligible_count:       int
    at_risk_count:        int
    ineligible_count:     int
    total_donors_checked: int
    needs_attention:      bool


class ChainHealthSummary(BaseModel):
    total_chains:    int
    critical:        int
    warning:         int
    healthy:         int
    needs_attention: int
    chains:          list[ChainHealth]


class LifecycleSummary(BaseModel):
    request_id:      str
    current_state:   str
    state_index:     int
    total_states:    int
    progress_pct:    int
    is_terminal:     bool
    states:          list[str]
    state_entered_at: Optional[str] = None


# ── WebSocket ──────────────────────────────────────────────────────────────

class WebSocketEvent(BaseModel):
    type:           str
    request_id:     Optional[str] = None
    donor_name:     Optional[str] = None
    reply_text:     Optional[str] = None
    blood_group:    Optional[str] = None
    city_cluster:   Optional[str] = None
    donor_count:    Optional[int] = None
    new_donor_name: Optional[str] = None
    donor_id:       Optional[str] = None
    new_score:      Optional[int] = None
