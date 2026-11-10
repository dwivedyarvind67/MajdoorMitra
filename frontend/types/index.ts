export type PaymentType = 'cash' | 'upi' | 'bank' | 'advance' | 'other';

export type StatementStatus = 
  | 'INITIAL'
  | 'TRANSCRIBED'
  | 'EXTRACTED'
  | 'AWAITING_INFORMATION'
  | 'READY_FOR_CONFIRMATION'
  | 'CONFIRMED'
  | 'REJECTED';

export interface Worker {
  id: string;
  name: string;
  phone: string;
  preferred_language: string;
  created_at: string;
}

export interface Employer {
  id: string;
  worker_id: string;
  name: string;
  contact_details?: string;
  created_at: string;
}

export interface WorkEntry {
  id: string;
  worker_id: string;
  employer_id?: string;
  employer_name?: string;
  work_date: string;
  days_worked: string;
  hours_worked?: string;
  daily_wage: string;
  total_earned: string;
  description?: string;
  source_statement_id?: string;
  created_at: string;
}

export interface Payment {
  id: string;
  worker_id: string;
  employer_id?: string;
  employer_name?: string;
  amount: string;
  payment_date: string;
  payment_type: PaymentType;
  notes?: string;
  source_statement_id?: string;
  created_at: string;
}

export interface EmployerSummary {
  employer_id: string;
  employer_name: string;
  total_earned: string;
  total_received: string;
  total_advances: string;
  balance: string;
  pending: string;
  overpaid: string;
  total_work_days: string;
}

export interface LedgerSummary {
  total_earned: string;
  total_received: string;
  total_advances: string;
  balance: string;
  pending: string;
  overpaid: string;
  total_work_days: string;
  employer_count: number;
  employers?: EmployerSummary[];
}

export interface TransactionItem {
  id: string;
  type: 'work' | 'payment';
  date: string;
  amount: string;
  days_worked?: string;
  daily_wage?: string;
  payment_type?: string;
  employer_id?: string;
  employer_name?: string;
  description?: string;
  source_statement_id?: string;
}

export interface ExtractionResult {
  intent?: string;
  days_worked?: string | number | null;
  daily_wage?: string | number | null;
  hours_worked?: string | number | null;
  work_date?: string | null;
  amount_received?: string | number | null;
  payment_type?: PaymentType | null;
  employer_name?: string | null;
  description?: string | null;
  missing_fields: string[];
  ambiguities: string[];
  requires_confirmation: boolean;
}

export interface VoiceSession {
  id: string;
  status: StatementStatus;
  language: string;
  created_at: string;
}

export interface ExtractionResponse {
  id: string;
  status: StatementStatus;
  extracted_data?: ExtractionResult;
  question?: string;
  conversation_history?: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
}

export interface VoiceReplyResponse extends ExtractionResponse {
  transcript?: string | null;
}

export interface VoiceConfirmation {
  id: string;
  status: StatementStatus;
  work_entry_id?: string;
  payment_id?: string;
  message: string;
}

export interface SpokenReceipt {
  audio_url?: string;
  audio_base64?: string;
  audio_content_type?: string;
  text: string;
}

export interface StatementListItem {
  id: string;
  transcript?: string | null;
  language: string;
  status: StatementStatus;
  created_at: string;
  confirmed_at?: string | null;
}

export interface StatementDetail extends StatementListItem {
  worker_id: string;
  extracted_data?: ExtractionResult | null;
  conversation_history?: Array<{
    role: string;
    content: string;
    timestamp: string;
  }> | null;
}

export interface TransactionList {
  transactions: TransactionItem[];
  total_count: number;
}
