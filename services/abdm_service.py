"""Demo / sandbox ABDM-ABHA layer. No real government APIs are called."""

from datetime import datetime, timezone


DEMO_BANNER = "Demo / Prototype Integration — not connected to ABDM production APIs."


def verify_abha_demo(abha_id):
    digits = "".join(ch for ch in (abha_id or "") if ch.isdigit())
    if len(digits) < 8:
        return {
            "ok": False,
            "mode": "sandbox",
            "banner": DEMO_BANNER,
            "message": "Enter a mock ABHA-like number with at least 8 digits for this demo.",
        }
    return {
        "ok": True,
        "mode": "sandbox",
        "banner": DEMO_BANNER,
        "abha_id": digits,
        "status": "verified-demo",
        "message": "Sandbox verification succeeded. No national health ID was contacted.",
    }


def link_health_record_demo(patient, summary=None):
    return {
        "ok": True,
        "mode": "sandbox",
        "banner": DEMO_BANNER,
        "linked_to": patient.patient_id,
        "summary_status": summary.status if summary else "none",
        "message": "A health record link token was simulated locally. Nothing was sent outside this server.",
    }


def generate_fhir_like_payload(patient, session=None, documents=None, labs=None):
    documents = documents or []
    labs = labs or []
    now = datetime.now(timezone.utc).isoformat()
    resources = [
        {
            "resourceType": "Patient",
            "id": patient.patient_id,
            "name": [{"text": patient.full_name}],
            "gender": (patient.gender or "").lower(),
            "telecom": [{"system": "phone", "value": patient.phone}],
            "address": [{"text": patient.address}],
        }
    ]
    if session:
        resources.append(
            {
                "resourceType": "Encounter",
                "id": session.session_number,
                "status": session.status,
                "subject": {"reference": f"Patient/{patient.patient_id}"},
                "period": {"start": session.created_at.isoformat() if session.created_at else now},
            }
        )
    for lab in labs:
        resources.append(
            {
                "resourceType": "Observation",
                "id": f"lab-{lab.id}",
                "status": "preliminary",
                "code": {"text": lab.test_name},
                "valueString": f"{lab.value or ''} {lab.unit or ''}".strip(),
                "interpretation": [{"text": lab.flag}],
                "note": [
                    {
                        "text": "Automated extraction/flagging for review. Clinical interpretation must be performed by a qualified healthcare professional."
                    }
                ],
            }
        )
    for doc in documents:
        resources.append(
            {
                "resourceType": "DocumentReference",
                "id": f"doc-{doc.id}",
                "status": "current",
                "type": {"text": doc.category},
                "date": doc.created_at.isoformat() if doc.created_at else now,
                "content": [{"attachment": {"title": doc.original_filename}}],
            }
        )
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [{"display": DEMO_BANNER}]},
        "timestamp": now,
        "entry": [{"resource": item} for item in resources],
    }
