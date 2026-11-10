"""
Tests for PDF Wage Statement generation using ReportLab.
"""

from datetime import datetime, timezone
from decimal import Decimal
from app.services.pdf_service import PDFService
from app.schemas.ledger import TransactionItem


def test_pdf_generation():
    service = PDFService()
    summary = {
        "total_earned": Decimal("4200.00"),
        "total_received": Decimal("3000.00"),
        "total_advances": Decimal("500.00"),
        "pending": Decimal("1200.00"),
        "total_work_days": Decimal("6.00"),
    }
    tx1 = TransactionItem(
        id="tx-1",
        type="work",
        date=datetime.now(timezone.utc),
        amount=Decimal("4200.00"),
        days_worked=Decimal("6.00"),
        daily_wage=Decimal("700.00"),
        employer_name="Sharma Construction",
        description="Masonry work",
    )
    tx2 = TransactionItem(
        id="tx-2",
        type="payment",
        date=datetime.now(timezone.utc),
        amount=Decimal("3000.00"),
        payment_type="cash",
        employer_name="Sharma Construction",
        description="Advance payment",
    )

    pdf_bytes = service.generate_statement(
        worker_name="Ramesh Kumar",
        worker_phone="9876543210",
        employer_name="Sharma Construction",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        work_entries=[{"date": "2026-11-10", "days": "6", "wage": "700", "total": "4200"}],
        payments=[{"date": "2026-11-10", "amount": "3000", "type": "cash"}],
        summary=summary,
    ) if hasattr(service, "generate_statement") else service.generate_wage_statement_pdf(
        worker_name="Ramesh Kumar",
        worker_phone="9876543210",
        summary=summary,
        transactions=[tx1, tx2],
        employer_name="Sharma Construction",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
