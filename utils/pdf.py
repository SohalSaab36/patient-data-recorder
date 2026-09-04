from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#0f4c5c")
TEAL = colors.HexColor("#1b7a6e")
LIGHT = colors.HexColor("#e8f4f2")
TEXT = colors.HexColor("#243038")
MUTED = colors.HexColor("#5b6b73")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            fontName="Times-Bold",
            fontSize=18,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DocSub",
            fontName="Times-Italic",
            fontSize=10,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHead",
            fontName="Times-Bold",
            fontSize=12,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyText2",
            fontName="Times-Roman",
            fontSize=10,
            textColor=TEXT,
            leading=14,
            alignment=TA_JUSTIFY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            fontName="Times-Bold",
            fontSize=10,
            textColor=NAVY,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Value",
            fontName="Times-Roman",
            fontSize=10,
            textColor=TEXT,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Footer",
            fontName="Times-Italic",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        )
    )
    return styles


def _nl(text):
    return (text or "Not recorded").replace("\n", "<br/>")


def _section(title, styles):
    data = [[Paragraph(title, styles["SectionHead"])]]
    table = Table(data, colWidths=[6.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _kv_table(rows, styles):
    data = []
    for label, value in rows:
        data.append(
            [
                Paragraph(label, styles["Label"]),
                Paragraph(_nl(value), styles["Value"]),
            ]
        )
    table = Table(data, colWidths=[1.8 * inch, 4.7 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d9d5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_case_sheet_pdf(case):
    patient = case.patient
    history = case.history
    doctor = case.doctor
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Case Sheet {case.case_number}",
    )

    story = [
        Paragraph("Smart Patient Case-Taking System", styles["DocTitle"]),
        Paragraph("SIH26047 &nbsp;|&nbsp; Confidential Medical Record", styles["DocSub"]),
        _section("Patient Identification", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Patient ID", patient.patient_id),
                ("Full Name", patient.full_name),
                ("Age / Gender", f"{patient.age} years / {patient.gender}"),
                ("Phone", patient.phone),
                ("Address", patient.address),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("Case Details", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Case Number", case.case_number),
                ("Attending Doctor", doctor.full_name if doctor else "—"),
                (
                    "Recorded On",
                    case.created_at.strftime("%d %B %Y, %H:%M") if case.created_at else "—",
                ),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("1. Chief Complaints", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Main Symptoms", case.main_symptoms),
                ("Duration", case.duration),
                ("Severity", case.severity),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("2. History of Present Illness", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Detailed Description", case.present_illness_description),
                ("When Symptoms Started", case.symptoms_started),
                ("Progression", case.progression),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("3. Past Medical History", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Previous Diseases", history.previous_diseases if history else "—"),
                ("Previous Surgeries", history.previous_surgeries if history else "—"),
                ("Hospitalizations", history.hospitalizations if history else "—"),
                ("Current Medications", history.current_medications if history else "—"),
                ("Allergies", history.allergies if history else "—"),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("4. Family History", styles),
        Spacer(1, 6),
        _kv_table([("Relevant History", case.family_history)], styles),
        Spacer(1, 10),
        _section("5. Personal History", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Diet", case.diet),
                ("Sleep", case.sleep),
                ("Lifestyle", case.lifestyle),
            ],
            styles,
        ),
        Spacer(1, 18),
        Paragraph(
            "This document is generated by SIH26047 Smart Patient Case-Taking System. "
            "For clinical use by authorized medical staff only.",
            styles["Footer"],
        ),
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_clinical_summary_pdf(summary, patient, session):
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Clinical Summary {session.session_number}",
    )
    rows = [
        ("Chief Complaint", summary.chief_complaint),
        ("History of Present Illness", summary.hpi),
        ("Past Medical History", summary.past_medical),
        ("Past Surgical History", summary.past_surgical),
        ("Drug & Medication History", summary.drug_history),
        ("Allergies", summary.allergy_history),
        ("Family History", summary.family_history),
        ("Personal History", summary.personal_history),
        ("Review of Systems", summary.review_of_systems),
        ("Prior Investigations", summary.prior_investigations),
        ("Document Timeline", summary.document_timeline),
        ("Red Flags / Notes", summary.red_flag_notes),
        ("Important notes", summary.important_notes),
        ("Review status", summary.status),
    ]
    story = [
        Paragraph("Physician-ready clinical history summary", styles["DocTitle"]),
        Paragraph(
            "SIH26047 prototype &nbsp;|&nbsp; Not a diagnosis or certified medical device",
            styles["DocSub"],
        ),
        _section("Patient", styles),
        Spacer(1, 6),
        _kv_table(
            [
                ("Patient ID", patient.patient_id),
                ("Name", patient.full_name),
                ("Age / Gender", f"{patient.age} / {patient.gender}"),
                ("Session", session.session_number),
                ("Language", session.language),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section("Structured history", styles),
        Spacer(1, 6),
        _kv_table(rows, styles),
        Spacer(1, 18),
        Paragraph(
            "Clinician confirmation is required before this summary is used for care.",
            styles["Footer"],
        ),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer
