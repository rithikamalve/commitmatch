import logging
from pathlib import Path

import numpy as np
import pandas as pd

from matching.blood_compat import normalize_blood_group

logger = logging.getLogger(__name__)

DATE_COLS = [
    "last_donation_date", "last_contacted_date", "next_eligible_date",
    "registration_date", "last_transfusion_date", "expected_next_transfusion_date",
    "last_bridge_donation_date",
]


class DataLoader:
    def __init__(self, csv_path: str):
        self.csv_path  = Path(csv_path)
        self.raw_df: pd.DataFrame     = pd.DataFrame()
        self.donors_df: pd.DataFrame  = pd.DataFrame()
        self.patients_df: pd.DataFrame = pd.DataFrame()
        self._load()

    # ── Public ────────────────────────────────────────────────────────────

    def get_donors(self) -> pd.DataFrame:
        return self.donors_df

    def get_patients(self) -> pd.DataFrame:
        return self.patients_df

    def get_donor_by_id(self, user_id: str) -> dict | None:
        rows = self.donors_df[self.donors_df["user_id"].astype(str) == str(user_id)]
        return self._row_to_dict(rows.iloc[0]) if not rows.empty else None

    def get_patient_by_id(self, bridge_id: str) -> dict | None:
        rows = self.patients_df[self.patients_df["bridge_id"].astype(str) == str(bridge_id)]
        return self._row_to_dict(rows.iloc[0]) if not rows.empty else None

    # ── Private ───────────────────────────────────────────────────────────

    def _load(self):
        if not self.csv_path.exists():
            logger.warning("CSV not found at %s — DataLoader empty", self.csv_path)
            return
        logger.info("Loading CSV from %s", self.csv_path)
        self.raw_df = pd.read_csv(self.csv_path, low_memory=False)

        self.patients_df = self._clean_patients(
            self.raw_df[self.raw_df["bridge_id"].notna()].copy()
        )
        self.donors_df = self._clean_donors(
            self.raw_df[self.raw_df["bridge_id"].isna()].copy()
        )
        logger.info("Loaded %d donors, %d patients", len(self.donors_df), len(self.patients_df))

    def _clean_donors(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "eligibility_status" in df.columns:
            df["is_eligible"] = (
                df["eligibility_status"].str.lower().str.contains("eligible", na=False) &
                ~df["eligibility_status"].str.lower().str.contains("ineligible", na=False)
            )
        else:
            df["is_eligible"] = False

        if "donations_till_date" in df.columns:
            df["has_donation_history"] = (
                df["donations_till_date"].notna() & (df["donations_till_date"] > 0)
            )
        else:
            df["has_donation_history"] = False

        if "blood_group" in df.columns:
            df["blood_group"] = df["blood_group"].apply(normalize_blood_group)

        if "user_id" not in df.columns:
            df = df.reset_index(drop=True)
            df["user_id"] = df.index.astype(str)

        return df.reset_index(drop=True)

    def _clean_patients(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "bridge_blood_group" in df.columns:
            df["bridge_blood_group"] = df["bridge_blood_group"].apply(normalize_blood_group)

        return df.reset_index(drop=True)

    @staticmethod
    def _row_to_dict(row: pd.Series) -> dict:
        d = row.to_dict()
        for k, v in d.items():
            if v is None:
                continue
            try:
                if isinstance(v, float) and np.isnan(v):
                    d[k] = None
                elif pd.isnull(v):
                    d[k] = None
            except (TypeError, ValueError):
                pass
        return d
