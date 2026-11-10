import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from xml.sax.saxutils import escape


class PDFService:
    """Generates professional wage statement PDFs."""

    @staticmethod
    def format_inr(amount) -> str:
        """Format amount in Indian Rupee format."""
        if amount is None:
            return "₹0.00"
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        # Indian number formatting
        sign = "" if amount >= 0 else "-"
        amount = abs(amount)
        amount_str = f"{amount:.2f}"
        integer_part, decimal_part = amount_str.split(".")

        if len(integer_part) <= 3:
            formatted = integer_part
        else:
            last_three = integer_part[-3:]
            rest = integer_part[:-3]
            # Add commas every 2 digits for the rest
            groups = []
            while len(rest) > 2:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.insert(0, rest)
            formatted = ",".join(groups) + "," + last_three

        return f"{sign}₹{formatted}.{decimal_part}"

    def generate_statement(
        self,
        worker_name: str,
        worker_phone: str,
        employer_name: Optional[str],
        period_start: Optional[datetime],
        period_end: Optional[datetime],
        work_entries: List[dict],
        payments: List[dict],
        summary: dict,
        transcript: Optional[str] = None,
        confirmation_status: str = "CONFIRMED",
        confirmed_at: Optional[datetime] = None,
    ) -> bytes:
        """Generate a professional wage statement PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=6*mm,
            alignment=TA_CENTER,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            spaceBefore=6*mm,
            spaceAfter=3*mm,
        )
        normal_style = styles['Normal']
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
        right_style = ParagraphStyle(
            'Right',
            parent=styles['Normal'],
            alignment=TA_RIGHT,
        )

        elements = []

        # Title
        elements.append(Paragraph("MazdoorMitra - Wage Statement", title_style))
        elements.append(Paragraph("मज़दूरमित्र - मज़दूरी विवरण", title_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue))
        elements.append(Spacer(1, 4*mm))

        # Worker details
        elements.append(Paragraph(f"<b>Worker / कर्मचारी:</b> {escape(worker_name)}", normal_style))
        elements.append(Paragraph(f"<b>Phone / फ़ोन:</b> {escape(worker_phone)}", normal_style))
        if employer_name:
            elements.append(Paragraph(f"<b>Employer / नियोक्ता:</b> {escape(employer_name)}", normal_style))

        period_str = ""
        if period_start:
            period_str = f"{period_start.strftime('%d/%m/%Y')}"
        if period_end:
            period_str += f" - {period_end.strftime('%d/%m/%Y')}"
        if period_str:
            elements.append(Paragraph(f"<b>Period / अवधि:</b> {period_str}", normal_style))

        elements.append(Paragraph(
            f"<b>Generated / जनरेट:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            normal_style,
        ))
        elements.append(Paragraph(
            f"<b>Worker confirmation / मज़दूर की पुष्टि:</b> {escape(confirmation_status)}",
            normal_style,
        ))
        if confirmed_at:
            elements.append(Paragraph(
                f"<b>Confirmed at / पुष्टि का समय:</b> {confirmed_at.strftime('%d/%m/%Y %H:%M UTC')}",
                normal_style,
            ))
        elements.append(Spacer(1, 6*mm))

        if transcript:
            elements.append(Paragraph("Original voice transcript / मूल आवाज़ का पाठ", heading_style))
            elements.append(Paragraph(escape(transcript), normal_style))
            elements.append(Spacer(1, 4*mm))

        # Summary
        elements.append(Paragraph("Summary / सारांश", heading_style))
        summary_data = [
            ["Total Earned / कुल कमाई", self.format_inr(summary.get("total_earned", 0))],
            ["Total Received / कुल भुगतान", self.format_inr(summary.get("total_received", 0))],
            ["Advances / अग्रिम", self.format_inr(summary.get("total_advances", 0))],
            ["Balance / शेष", self.format_inr(summary.get("balance", 0))],
            ["Pending / बकाया", self.format_inr(summary.get("pending", 0))],
            ["Overpaid / अतिरिक्त भुगतान", self.format_inr(summary.get("overpaid", 0))],
            ["Work Days / कार्य दिवस", str(summary.get("total_work_days", 0))],
        ]
        summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 6*mm))

        # Work Entries Table
        if work_entries:
            elements.append(Paragraph("Work Entries / काम का विवरण", heading_style))
            work_header = ["Date", "Work / Rate", "Earned", "Record status", "Description"]
            work_rows = [work_header]
            for entry in work_entries:
                work_date = entry.get("work_date", "")
                if isinstance(work_date, datetime):
                    work_date = work_date.strftime("%d/%m/%Y")
                if entry.get("wage_basis") == "hourly":
                    detail = f"{entry.get('hours_worked', 0)} h × {self.format_inr(entry.get('hourly_rate', 0))}/h"
                else:
                    detail = f"{entry.get('days_worked', 0)} days × {self.format_inr(entry.get('daily_wage', 0))}/day"
                if Decimal(str(entry.get("overtime_hours", 0) or 0)) > 0:
                    detail += f"; OT {entry.get('overtime_hours')} h × {entry.get('overtime_multiplier', '1.5')}"
                work_rows.append([
                    str(work_date),
                    self.format_inr(entry.get("total_earned", 0)),
                    escape(detail),
                    escape(str(entry.get("record_status", "worker reported"))),
                    escape(str(entry.get("description", "") or "")),
                ])

            work_rows = [work_header] + [[row[0], row[2], row[1], row[3], row[4]] for row in work_rows[1:]]
            work_table = Table(work_rows, colWidths=[2*cm, 4.5*cm, 2.5*cm, 2.3*cm, 4.2*cm])
            work_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ]))
            elements.append(work_table)
            elements.append(Spacer(1, 6*mm))

        # Payments Table
        if payments:
            elements.append(Paragraph("Payments / भुगतान विवरण", heading_style))
            pay_header = ["Date", "Amount", "Type", "Record status", "Notes"]
            pay_rows = [pay_header]
            for payment in payments:
                pay_date = payment.get("payment_date", "")
                if isinstance(pay_date, datetime):
                    pay_date = pay_date.strftime("%d/%m/%Y")
                pay_rows.append([
                    str(pay_date),
                    self.format_inr(payment.get("amount", 0)),
                    str(payment.get("payment_type", "")),
                    escape(str(payment.get("record_status", "worker reported"))),
                    escape(str(payment.get("notes", "") or "")),
                ])

            pay_table = Table(pay_rows, colWidths=[2*cm, 2.5*cm, 2*cm, 2.3*cm, 6.7*cm])
            pay_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ]))
            elements.append(pay_table)

        elements.append(Spacer(1, 10*mm))

        # Disclaimer
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(
            "This statement contains information reported by the worker and marks whether the worker confirmed it. "
            "MazdoorMitra has not independently verified employment, hours, wages, or payments. It is not legal advice.",
            small_style,
        ))
        elements.append(Paragraph(
            "इस विवरण में मज़दूर द्वारा बताई गई जानकारी और उसकी पुष्टि की स्थिति है। "
            "मज़दूरमित्र ने नौकरी, समय, मज़दूरी या भुगतान की स्वतंत्र जाँच नहीं की है। यह कानूनी सलाह नहीं है।",
            small_style,
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.read()


def get_pdf_service() -> PDFService:
    return PDFService()
