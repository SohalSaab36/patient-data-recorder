"""Rule-based document intelligence for the hackathon demo — not medical-grade."""

import re
from datetime import datetime

LAB_PATTERNS = [
    ("Hemoglobin", r"h(?:ae)?emoglobin|hb\b", r"(\d+(?:\.\d+)?)", "g/dL", 12.0, 16.0),
    ("WBC", r"\bwbc\b|white blood", r"(\d+(?:\.\d+)?)", "x10^3/uL", 4.0, 11.0),
    ("Platelets", r"platelet", r"(\d+(?:\.\d+)?)", "x10^3/uL", 150.0, 450.0),
    ("Fasting glucose", r"glucose|fbs|fasting blood sugar", r"(\d+(?:\.\d+)?)", "mg/dL", 70.0, 100.0),
    ("Creatinine", r"creatinine", r"(\d+(?:\.\d+)?)", "mg/dL", 0.6, 1.3),
    ("TSH", r"\btsh\b", r"(\d+(?:\.\d+)?)", "mIU/L", 0.4, 4.0),
]

MED_LINE = re.compile(
    r"\b(tab|tablet|cap|capsule|syrup|inj|injection)\.?\s+([A-Za-z][A-Za-z0-9\-]{2,})\s*(\d+\s*(?:mg|mcg|g|ml))?",
    re.I,
)
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
DR_RE = re.compile(r"\b(?:dr\.?|hospital|clinic)\s*[:\-]?\s*([A-Za-z][A-Za-z .]{2,40})", re.I)
DX_RE = re.compile(r"\b(?:diagnosis|impression|condition)\s*[:\-]\s*(.+)", re.I)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def flag_lab(value, low, high):
    number = _to_float(value)
    if number is None or low is None or high is None:
        return "needs_manual_review"
    if number < low:
        return "potentially_low"
    if number > high:
        return "potentially_high"
    return "within_range"


def parse_date(text):
    match = DATE_RE.search(text or "")
    if not match:
        return None
    raw = match.group(1)
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def extract_from_text(text):
    text = text or ""
    findings = {
        "document_date": None,
        "facility_or_doctor": None,
        "diagnosis_text": None,
        "medications": [],
        "labs": [],
        "procedures": [],
        "fields": [],
    }
    parsed_date = parse_date(text)
    if parsed_date:
        findings["document_date"] = parsed_date.isoformat()
        findings["fields"].append(("document_date", parsed_date.isoformat()))

    dr = DR_RE.search(text)
    if dr:
        findings["facility_or_doctor"] = dr.group(1).strip()[:180]
        findings["fields"].append(("doctor_or_hospital", findings["facility_or_doctor"]))

    dx = DX_RE.search(text)
    if dx:
        findings["diagnosis_text"] = dx.group(1).strip()[:400]
        findings["fields"].append(("diagnosis_text", findings["diagnosis_text"]))

    for match in MED_LINE.finditer(text):
        name = match.group(2)
        dose = (match.group(3) or "").strip()
        findings["medications"].append({"name": name, "dosage": dose})
        findings["fields"].append(("medication", f"{name} {dose}".strip()))

    lower = text.lower()
    for test_name, name_re, value_re, unit, low, high in LAB_PATTERNS:
        nm = re.search(name_re, lower)
        if not nm:
            continue
        window = text[nm.start() : nm.start() + 80]
        vm = re.search(value_re, window)
        if not vm:
            continue
        value = vm.group(1)
        flag = flag_lab(value, low, high)
        findings["labs"].append(
            {
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "ref_low": str(low),
                "ref_high": str(high),
                "flag": flag,
            }
        )
        findings["fields"].append(("lab_result", f"{test_name}={value} {unit} [{flag}]"))

    if re.search(r"\b(surgery|operated|cholecystectomy|appendectomy|cabg|angioplasty)\b", lower):
        findings["procedures"].append("Procedure term mentioned in document text")
        findings["fields"].append(("procedure", "Procedure-related term found — verify manually"))

    return findings
