from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.services.wage_calculator import FinancialService


class ConversationService:
    """
    Manages conversation state machine for voice sessions.
    States: INITIAL -> TRANSCRIBED -> EXTRACTED -> AWAITING_INFORMATION -> READY_FOR_CONFIRMATION -> CONFIRMED/REJECTED
    """

    FOLLOW_UP_QUESTIONS_HI = {
        "days_worked": "आपने कितने दिन काम किया?",
        "daily_wage": "आपकी दैनिक मज़दूरी कितनी है?",
        "work_date": "यह काम/भुगतान किस तारीख को हुआ/मिला? (जैसे: 15 नवंबर 2024)",
        "employer_name": "आपके ठेकेदार/मालिक का नाम क्या है?",
        "amount_received": "आपको कितने रुपये मिले?",
        "payment_type": "भुगतान कैसे मिला? (नकद/UPI/बैंक/अग्रिम)",
        "intent": "क्या आप काम दर्ज करना चाहते हैं या भुगतान दर्ज करना चाहते हैं?",
        "hours_worked": "आपने कितने घंटे काम किया?",
        "hourly_rate": "आपकी प्रति घंटे की मज़दूरी कितनी है?",
        "wage_basis": "मज़दूरी रोज़ के हिसाब से है या घंटे के हिसाब से?",
        "overtime_hours": "इनमें से कितने घंटे ओवरटाइम थे?",
        "overtime_multiplier": "ओवरटाइम का गुणक कितना तय हुआ है? (जैसे 1.5)",
    }

    FOLLOW_UP_QUESTIONS_EN = {
        "days_worked": "How many days did you work?",
        "daily_wage": "What is your daily wage rate?",
        "work_date": "On which date was this work done or payment received? (e.g., 15 November 2024)",
        "employer_name": "What is your employer/contractor's name?",
        "amount_received": "How much money did you receive?",
        "payment_type": "How was the payment made? (cash/UPI/bank/advance)",
        "intent": "Do you want to log work or log a payment?",
        "hours_worked": "How many hours did you work?",
        "hourly_rate": "What is your wage per hour?",
        "wage_basis": "Is the wage agreed per day or per hour?",
        "overtime_hours": "How many of those hours were overtime?",
        "overtime_multiplier": "What overtime multiplier was agreed? (for example, 1.5)",
    }

    def get_next_state(self, current_status: str, extracted_data: Optional[dict] = None) -> str:
        """Determine the next state based on current state and data."""
        if current_status == "INITIAL":
            return "TRANSCRIBED"
        elif current_status == "TRANSCRIBED":
            return "EXTRACTED"
        elif current_status == "EXTRACTED":
            if extracted_data and not extracted_data.get("missing_fields") and not extracted_data.get("ambiguities"):
                return "READY_FOR_CONFIRMATION"
            return "AWAITING_INFORMATION"
        elif current_status == "AWAITING_INFORMATION":
            if extracted_data and not extracted_data.get("missing_fields") and not extracted_data.get("ambiguities"):
                return "READY_FOR_CONFIRMATION"
            return "AWAITING_INFORMATION"
        elif current_status == "READY_FOR_CONFIRMATION":
            return "READY_FOR_CONFIRMATION"  # stays until confirmed/rejected
        return current_status

    def generate_question(
        self,
        missing_fields: List[str],
        language: str = "hi",
        intent: Optional[str] = None,
        ambiguities: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Generate the next follow-up question for missing fields."""
        hindi = language in {"hi", "hinglish"}
        if not missing_fields and ambiguities:
            return (
                "एक विवरण स्पष्ट नहीं है। कृपया उसे ठीक करके फिर से जाँचें।"
                if hindi
                else "One detail is unclear. Please correct it and review the record again."
            )
        if not missing_fields:
            return None

        questions = self.FOLLOW_UP_QUESTIONS_HI if hindi else self.FOLLOW_UP_QUESTIONS_EN

        # Ask for the first missing field
        field = missing_fields[0]
        if field == "intent":
            if hindi:
                return "क्या आप काम दर्ज करना चाहते हैं या मिला हुआ भुगतान?"
            return "Would you like to record work or a payment received?"
        return questions.get(field, f"कृपया {field} बताएं।" if hindi else f"Please provide {field}.")

    def generate_confirmation_message(self, extracted_data: dict, language: str = "hi") -> str:
        """Generate a summary message for user confirmation."""
        intent = extracted_data.get("intent")
        hindi = language in {"hi", "hinglish"}
        lines = ["कृपया इन विवरणों की पुष्टि करें:" if hindi else "Please confirm these details:"]
        employer = extracted_data.get("employer_name")
        work_date = extracted_data.get("work_date")
        if employer:
            lines.append(f"ठेकेदार: {employer}" if hindi else f"Employer: {employer}")
        if intent == "log_work":
            self._append_work_breakdown(lines, extracted_data, hindi)
        elif intent == "log_payment":
            lines.append(f"मिला भुगतान: ₹{extracted_data.get('amount_received')}" if hindi else f"Payment received: ₹{extracted_data.get('amount_received')}")
            lines.append(f"भुगतान का तरीका: {extracted_data.get('payment_type')}" if hindi else f"Payment method: {extracted_data.get('payment_type')}")
        if work_date:
            lines.append(f"तारीख: {work_date}" if hindi else f"Date: {work_date}")
        lines.append("\nक्या यह सही है? (हाँ/ना)" if hindi else "\nIs this correct? (yes/no)")
        return "\n".join(lines)

    def generate_receipt_message(self, extracted_data: dict, language: str = "hi") -> str:
        """Create a post-save receipt message that does not ask for confirmation again."""
        intent = extracted_data.get("intent")
        employer = extracted_data.get("employer_name")
        work_date = extracted_data.get("work_date")
        if language in {"hi", "hinglish"}:
            lines = ["आपका रिकॉर्ड आपकी पुष्टि के बाद सुरक्षित कर लिया गया है।"]
            if employer:
                lines.append(f"ठेकेदार: {employer}")
            if intent == "log_work":
                self._append_work_breakdown(lines, extracted_data, True)
            elif intent == "log_payment":
                lines.append(f"मिला भुगतान: ₹{extracted_data.get('amount_received')}")
                lines.append(f"भुगतान का तरीका: {extracted_data.get('payment_type')}")
            if work_date:
                lines.append(f"तारीख: {work_date}")
            return "\n".join(lines)

        lines = ["Your record has been saved after your confirmation."]
        if employer:
            lines.append(f"Employer: {employer}")
        if intent == "log_work":
            self._append_work_breakdown(lines, extracted_data, False)
        elif intent == "log_payment":
            lines.append(f"Payment received: ₹{extracted_data.get('amount_received')}")
            lines.append(f"Payment method: {extracted_data.get('payment_type')}")
        if work_date:
            lines.append(f"Date: {work_date}")
        return "\n".join(lines)

    @staticmethod
    def _append_work_breakdown(lines: List[str], data: dict, hindi: bool) -> None:
        """Use the shared financial engine for spoken and visible totals."""
        breakdown = FinancialService.calculate_work_breakdown(
            days_worked=data.get("days_worked") or 0,
            daily_wage=data.get("daily_wage"),
            hours_worked=data.get("hours_worked"),
            wage_basis=data.get("wage_basis", "daily"),
            hourly_rate=data.get("hourly_rate"),
            overtime_hours=data.get("overtime_hours") or 0,
            overtime_multiplier=data.get("overtime_multiplier") or "1.5",
        )
        if data.get("wage_basis") == "hourly":
            lines.append(
                f"घंटे: {data.get('hours_worked')} × ₹{data.get('hourly_rate')} प्रति घंटा"
                if hindi
                else f"Hours: {data.get('hours_worked')} × ₹{data.get('hourly_rate')} per hour"
            )
        else:
            lines.append(
                f"काम के दिन: {data.get('days_worked')}"
                if hindi else f"Work days: {data.get('days_worked')}"
            )
            lines.append(
                f"दैनिक मज़दूरी: ₹{data.get('daily_wage')}"
                if hindi else f"Daily wage: ₹{data.get('daily_wage')}"
            )
        if data.get("hours_worked") is not None and data.get("wage_basis") != "hourly":
            lines.append(f"घंटे: {data['hours_worked']}" if hindi else f"Hours: {data['hours_worked']}")
        if data.get("overtime_hours"):
            lines.append(
                f"ओवरटाइम: {data['overtime_hours']} घंटे × {data.get('overtime_multiplier') or '1.5'}"
                if hindi
                else f"Overtime: {data['overtime_hours']} hours × {data.get('overtime_multiplier') or '1.5'}"
            )
            lines.append(
                f"ओवरटाइम कमाई: ₹{breakdown['overtime_earned']:.2f}"
                if hindi
                else f"Overtime earnings: ₹{breakdown['overtime_earned']:.2f}"
            )
        lines.append(
            f"कुल कमाई: ₹{breakdown['total_earned']:.2f}"
            if hindi
            else f"Total earned: ₹{breakdown['total_earned']:.2f}"
        )

    def apply_correction(self, extracted_data: dict, field: str, value: Any) -> dict:
        """Apply a user correction to extracted data."""
        updated = dict(extracted_data)
        updated[field] = value
        # Remove the field from missing_fields if present
        missing = list(updated.get("missing_fields", []))
        if field in missing:
            missing.remove(field)
        updated["missing_fields"] = missing
        return updated

    def update_from_reply(self, extracted_data: dict, reply_text: str, missing_fields: List[str]) -> dict:
        """
        Update extracted data based on user reply.
        Simple heuristic: try to fill the first missing field from the reply.
        """
        updated = dict(extracted_data)
        if not missing_fields:
            return updated

        field = missing_fields[0]

        # Try to parse the value based on field type
        if field in ("days_worked", "daily_wage", "hours_worked", "amount_received"):
            # Extract number from reply
            import re
            numbers = re.findall(r'[\d,]+\.?\d*', reply_text.replace(',', ''))
            if numbers:
                try:
                    updated[field] = str(Decimal(numbers[0]))
                    missing = list(updated.get("missing_fields", []))
                    if field in missing:
                        missing.remove(field)
                    updated["missing_fields"] = missing
                except Exception:
                    pass
        elif field == "payment_type":
            reply_lower = reply_text.lower().strip()
            type_map = {
                "cash": "cash", "नकद": "cash", "naqad": "cash",
                "upi": "upi", "यूपीआई": "upi",
                "bank": "bank", "बैंक": "bank",
                "advance": "advance", "अग्रिम": "advance", "एडवांस": "advance",
            }
            for key, val in type_map.items():
                if key in reply_lower:
                    updated[field] = val
                    missing = list(updated.get("missing_fields", []))
                    if field in missing:
                        missing.remove(field)
                    updated["missing_fields"] = missing
                    break
        elif field == "intent":
            reply_lower = reply_text.lower().strip()
            if any(w in reply_lower for w in ["काम", "work", "कम"]):
                updated[field] = "log_work"
            elif any(w in reply_lower for w in ["भुगतान", "payment", "पैसा", "पैसे", "money"]):
                updated[field] = "log_payment"
            if updated.get(field) != extracted_data.get(field):
                missing = list(updated.get("missing_fields", []))
                if field in missing:
                    missing.remove(field)
                updated["missing_fields"] = missing
        elif field == "work_date":
            # Try to parse a date
            import re
            date_patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(\d{1,2})-(\d{1,2})-(\d{4})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, reply_text)
                if match:
                    groups = match.groups()
                    try:
                        if len(groups[0]) == 4:
                            updated[field] = f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                        else:
                            updated[field] = f"{groups[2]}-{int(groups[1]):02d}-{int(groups[0]):02d}"
                        missing = list(updated.get("missing_fields", []))
                        if field in missing:
                            missing.remove(field)
                        updated["missing_fields"] = missing
                    except Exception:
                        pass
                    break
        else:
            # For string fields like employer_name, description - use the reply directly
            cleaned = reply_text.strip()
            if cleaned:
                updated[field] = cleaned
                missing = list(updated.get("missing_fields", []))
                if field in missing:
                    missing.remove(field)
                updated["missing_fields"] = missing

        return updated

    def add_to_history(self, history: Optional[List[dict]], role: str, content: str) -> List[dict]:
        """Add an entry to conversation history."""
        # Return a new list so SQLAlchemy's JSON column sees the change and persists it.
        updated_history = list(history or [])
        updated_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return updated_history


def get_conversation_service() -> ConversationService:
    return ConversationService()
