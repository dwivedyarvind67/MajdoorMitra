"""Explainable, read-only checks over worker-owned wage ledger records."""

from collections import defaultdict
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Employer, Payment, PaymentAllocation, WorkEntry
from app.schemas.ledger import LedgerAlertResponse, LedgerAlertSource
from app.services.wage_calculator import WageCalculator, quantize_money


class MismatchService:
    """Build review prompts from recorded facts; never changes financial data."""

    @staticmethod
    def _alert_id(alert_type: str, *parts: str) -> str:
        digest = sha256("|".join((alert_type, *parts)).encode("utf-8")).hexdigest()[:20]
        return f"{alert_type}:{digest}"

    @classmethod
    async def get_alerts(cls, session: AsyncSession, worker_id: str) -> list[LedgerAlertResponse]:
        works = list((await session.execute(
            select(WorkEntry).where(WorkEntry.worker_id == worker_id).order_by(WorkEntry.work_date)
        )).scalars().all())
        payments = list((await session.execute(
            select(Payment).where(Payment.worker_id == worker_id).order_by(Payment.payment_date)
        )).scalars().all())
        employer_rows = (await session.execute(
            select(Employer).where(Employer.worker_id == worker_id)
        )).scalars().all()
        employer_names = {employer.id: employer.name for employer in employer_rows}

        allocation_rows = await session.execute(
            select(PaymentAllocation.payment_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .where(PaymentAllocation.worker_id == worker_id)
            .group_by(PaymentAllocation.payment_id)
        )
        allocated_by_payment = {payment_id: Decimal(str(amount or 0)) for payment_id, amount in allocation_rows.all()}
        source_map = {
            **{
                work.id: LedgerAlertSource(
                    id=work.id,
                    record_type="work",
                    date=work.work_date,
                    amount=Decimal(str(work.total_earned)),
                    description=work.description or f"{work.days_worked} दिन का काम",
                )
                for work in works
            },
            **{
                payment.id: LedgerAlertSource(
                    id=payment.id,
                    record_type="payment",
                    date=payment.payment_date,
                    amount=Decimal(str(payment.amount)),
                    description=payment.notes or f"भुगतान ({payment.payment_type.value if hasattr(payment.payment_type, 'value') else payment.payment_type})",
                )
                for payment in payments
            },
        }

        def sources(record_ids: list[str]) -> list[LedgerAlertSource]:
            return [source_map[record_id] for record_id in record_ids if record_id in source_map]

        works_by_employer: dict[str | None, list[WorkEntry]] = defaultdict(list)
        payments_by_employer: dict[str | None, list[Payment]] = defaultdict(list)
        for work in works:
            works_by_employer[work.employer_id].append(work)
        for payment in payments:
            payments_by_employer[payment.employer_id].append(payment)

        alerts: list[LedgerAlertResponse] = []
        employer_ids = set(works_by_employer) | set(payments_by_employer)
        for employer_id in employer_ids:
            employer_works = works_by_employer[employer_id]
            employer_payments = payments_by_employer[employer_id]
            employer_name = employer_names.get(employer_id) if employer_id else None
            label = employer_name or "मालिक दर्ज नहीं"
            calculation = WageCalculator.calculate_summary(employer_works, employer_payments)
            pending = quantize_money(Decimal(str(calculation["pending"])))
            overpaid = quantize_money(Decimal(str(calculation["overpaid"])))

            if pending > 0 and employer_works:
                record_ids = [entry.id for entry in employer_works[:20]]
                alerts.append(LedgerAlertResponse(
                    id=cls._alert_id("recorded_balance", employer_id or "unassigned", *record_ids),
                    alert_type="recorded_balance",
                    severity="review",
                    employer_id=employer_id,
                    employer_name=employer_name,
                    amount=pending,
                    source_record_ids=record_ids,
                    source_records=sources(record_ids),
                    explanation=f"आपके दर्ज काम और भुगतान के हिसाब में {label} से {pending} रुपये बाकी दिखते हैं। यह केवल आपके दर्ज रिकॉर्ड का हिसाब है।",
                    recommendation="काम और भुगतान की तारीख़ें जाँचें। रकम सही लगे तो मालिक से अपने रिकॉर्ड मिलाएँ।",
                ))

            if overpaid > 0 and employer_payments:
                record_ids = [payment.id for payment in employer_payments[-10:]] + [entry.id for entry in employer_works[-10:]]
                alerts.append(LedgerAlertResponse(
                    id=cls._alert_id("possible_overpayment", employer_id or "unassigned", *record_ids),
                    alert_type="possible_overpayment",
                    severity="review",
                    employer_id=employer_id,
                    employer_name=employer_name,
                    amount=overpaid,
                    source_record_ids=record_ids,
                    source_records=sources(record_ids),
                    explanation=f"दर्ज भुगतान, {label} के दर्ज काम से {overpaid} रुपये ज़्यादा हैं। अग्रिम या पुराना बकाया भी कारण हो सकता है।",
                    recommendation="भुगतान और काम की तारीख़ें मिलाएँ; कोई पुराना बकाया या अग्रिम छूटा हो तो उसे दर्ज करें।",
                ))

            for payment in employer_payments:
                unallocated = quantize_money(Decimal(str(payment.amount)) - allocated_by_payment.get(payment.id, Decimal("0")))
                if unallocated <= 0:
                    continue
                alerts.append(LedgerAlertResponse(
                    id=cls._alert_id("unallocated_payment", payment.id),
                    alert_type="unallocated_payment",
                    severity="information",
                    employer_id=employer_id,
                    employer_name=employer_name,
                    amount=unallocated,
                    source_record_ids=[payment.id],
                    source_records=sources([payment.id]),
                    explanation=f"{unallocated} रुपये का भुगतान किसी खास काम से नहीं जोड़ा गया है। यह कुल मिले भुगतान में एक बार गिना जाता है।",
                    recommendation="अगर यह भुगतान किसी दर्ज काम के लिए था, तो इतिहास में जाकर उसे उस काम से जोड़ें।",
                ))

            duplicate_groups: dict[tuple, list[WorkEntry]] = defaultdict(list)
            for work in employer_works:
                signature = (
                    work.work_date.date(), work.wage_basis, str(work.days_worked), str(work.daily_wage),
                    str(work.hours_worked), str(work.hourly_rate), str(work.overtime_hours),
                )
                duplicate_groups[signature].append(work)
            for same_work in duplicate_groups.values():
                if len(same_work) < 2:
                    continue
                record_ids = [entry.id for entry in same_work]
                alerts.append(LedgerAlertResponse(
                    id=cls._alert_id("possible_duplicate", employer_id or "unassigned", *record_ids),
                    alert_type="possible_duplicate",
                    severity="review",
                    employer_id=employer_id,
                    employer_name=employer_name,
                    amount=quantize_money(sum((Decimal(str(entry.total_earned)) for entry in same_work), Decimal("0"))),
                    source_record_ids=record_ids,
                    source_records=sources(record_ids),
                    explanation=f"{label} के लिए एक ही तारीख़ और समान मज़दूरी विवरण वाले {len(same_work)} काम दर्ज हैं। ये अलग-अलग काम भी हो सकते हैं।",
                    recommendation="रिकॉर्ड की तारीख़ और काम का विवरण देखें। गलती हो तो सही जानकारी दर्ज करने से पहले मौजूदा रिकॉर्ड जाँचें।",
                ))

            rate_groups: dict[str, list[WorkEntry]] = defaultdict(list)
            for work in employer_works:
                rate = work.hourly_rate if work.wage_basis == "hourly" else work.daily_wage
                unit = "hourly" if work.wage_basis == "hourly" else "daily"
                rate_groups[unit].append(work)
            for unit, rate_entries in rate_groups.items():
                rates = {str(entry.hourly_rate if unit == "hourly" else entry.daily_wage) for entry in rate_entries}
                if len(rates) < 2:
                    continue
                record_ids = [entry.id for entry in rate_entries[-10:]]
                unit_hi = "घंटे" if unit == "hourly" else "दिन"
                alerts.append(LedgerAlertResponse(
                    id=cls._alert_id("rate_change", employer_id or "unassigned", unit, *sorted(rates), *record_ids),
                    alert_type="rate_change",
                    severity="information",
                    employer_id=employer_id,
                    employer_name=employer_name,
                    source_record_ids=record_ids,
                    source_records=sources(record_ids),
                    explanation=f"{label} के लिए अलग-अलग तारीख़ों पर {unit_hi} की एक से अधिक दरें दर्ज हैं। दर बदलना सही हो सकता है।",
                    recommendation="हर काम पर लागू सहमत दर जाँचें; यह सूचना अपने आप पुराने या नए रिकॉर्ड नहीं बदलती।",
                ))

        return alerts
