"""Worker assistance content and record-based payment-request drafts."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer
from app.schemas.assistance import AssistanceResource, PaymentRequestDraft
from app.services.ledger_service import LedgerService
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/assistance", tags=["worker assistance"])


def _format_inr(amount) -> str:
    whole, fraction = f"{amount:.2f}".split(".")
    if len(whole) > 3:
        last = whole[-3:]
        prefix = whole[:-3]
        groups = []
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(groups + [last])
    return f"{whole}.{fraction}"

RESOURCES = [
    AssistanceResource(
        id="eshram-helpdesk",
        title="e-Shram helpdesk",
        description="e-Shram registration and portal support. Government helpdesk; Hindi and several Indian languages.",
        url="https://www.eshram.gov.in/helpdesk",
        source="Ministry of Labour & Employment, Government of India",
        phone="14434 / 1800 889 6811",
        availability="9:00 AM–6:00 PM, daily including Sundays (as listed by e-Shram)",
    ),
    AssistanceResource(
        id="eshram-grievance",
        title="e-Shram grievance portal",
        description="Register or track a grievance related to e-Shram services.",
        url="https://gms.eshram.gov.in/gmsportal/",
        source="Ministry of Labour & Employment, Government of India",
    ),
    AssistanceResource(
        id="samadhan-labour",
        title="SAMADHAN labour portal",
        description="Official portal for labour-related claims and employment grievances. Check portal guidance to confirm the right route for your issue.",
        url="https://samadhan.labour.gov.in/",
        source="Ministry of Labour & Employment, Government of India",
    ),
]

FAQS = [
    {
        "id": "record-keeping",
        "question_hi": "काम और भुगतान का रिकॉर्ड कैसे रखें?",
        "answer_hi": "काम की तारीख़, मालिक, जगह, तय दर और मिली रकम अलग-अलग दर्ज करें। रसीद या संदेश हो तो उसे संबंधित रिकॉर्ड के साथ सुरक्षित रखें।",
        "question_en": "How should I keep work and payment records?",
        "answer_en": "Record the work date, employer, site, agreed rate, and each payment separately. Keep receipts or messages with the related record.",
    },
    {
        "id": "check-difference",
        "question_hi": "मेरे हिसाब और मालिक के हिसाब में फर्क हो तो?",
        "answer_hi": "पहले तारीख़, काम के दिन, दर, अग्रिम और भुगतान को दोनों रिकॉर्ड से मिलाएँ। अंतर बना रहे तो अपने दस्तावेज़ सुरक्षित रखें और उपयुक्त सरकारी सहायता से पूछें।",
        "question_en": "What if my record differs from the employer's?",
        "answer_en": "Compare dates, work units, rates, advances, and payments. Keep supporting documents; if the difference remains, ask an appropriate official support service about next steps.",
    },
]


@router.get("/resources", response_model=list[AssistanceResource])
async def list_assistance_resources(worker_id: str = Depends(get_current_worker_id)):
    """Return official, non-commercial assistance resources."""
    return RESOURCES


@router.get("/faqs")
async def list_assistance_faqs(worker_id: str = Depends(get_current_worker_id)):
    """Return general record-keeping guidance, not legal advice."""
    return {"items": FAQS, "disclaimer": "General information only. This is not legal advice or a decision about legal eligibility."}


@router.get("/payment-request", response_model=PaymentRequestDraft)
async def create_payment_request_draft(
    employer_id: str | None = None,
    language: Literal["hi", "en"] = "hi",
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Prepare a copy-only message from the actual recorded pending balance."""
    employer_name = "मालिक जी" if language == "hi" else "your employer"
    if employer_id:
        employer = (await db.execute(
            select(Employer).where(Employer.id == employer_id, Employer.worker_id == worker_id)
        )).scalar_one_or_none()
        if employer is None:
            raise HTTPException(status_code=404, detail="Employer not found.")
        employer_name = employer.name

    summary = await LedgerService.get_summary(db, worker_id, employer_id=employer_id)
    amount = summary.pending
    if amount <= 0:
        raise HTTPException(status_code=409, detail="There is no positive pending balance in the selected recorded ledger.")

    if language == "hi":
        message = (
            f"नमस्ते {employer_name}, मेरे दर्ज हिसाब में काम के लिए {_format_inr(amount)} रुपये बाकी दिख रहे हैं। "
            "कृपया अपने रिकॉर्ड से मिलाकर भुगतान की स्थिति बता दें। धन्यवाद।"
        )
    else:
        name = employer_name if employer_id else "hello"
        greeting = f"Hello {name}," if employer_id else "Hello,"
        message = (
            f"{greeting} my recorded ledger shows ₹{_format_inr(amount)} pending for work. "
            "Could you please compare it with your records and let me know the payment status? Thank you."
        )
    return PaymentRequestDraft(
        employer_id=employer_id,
        employer_name=employer_name,
        amount_in_recorded_balance=amount,
        language=language,
        message=message,
    )
