from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/patients")
async def list_patients(request: Request):
    dl = request.app.state.data_loader
    df = dl.get_patients()
    records = []
    for _, row in df.iterrows():
        d = dl._row_to_dict(row)
        records.append({
            "bridge_id":                      str(d.get("bridge_id", "")),
            "bridge_blood_group":             d.get("bridge_blood_group"),
            "quantity_required":              d.get("quantity_required"),
            "expected_next_transfusion_date": str(d.get("expected_next_transfusion_date") or ""),
            "last_transfusion_date":          str(d.get("last_transfusion_date") or ""),
            "latitude":                       d.get("latitude"),
            "longitude":                      d.get("longitude"),
        })
    return records


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, request: Request):
    dl = request.app.state.data_loader
    patient = dl.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(404, f"Patient {patient_id} not found")
    return {k: (str(v) if hasattr(v, "date") else v) for k, v in patient.items()}
