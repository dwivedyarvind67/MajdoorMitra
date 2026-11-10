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
  wage_basis?: 'daily' | 'hourly';
  hourly_rate?: string;
  overtime_hours?: string;
  overtime_multiplier?: string;
  total_earned: string;
  allocated_amount?: string;
  outstanding_amount?: string;
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
  allocated_amount?: string;
  unallocated_amount?: string;
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
  wage_basis?: 'daily' | 'hourly';
  hourly_rate?: string;
  hours_worked?: string;
  overtime_hours?: string;
  overtime_multiplier?: string;
  payment_type?: string;
  employer_id?: string;
  employer_name?: string;
  description?: string;
  source_statement_id?: string;
  record_status: 'worker_reported' | 'worker_confirmed';
  was_corrected: boolean;
  confirmed_at?: string | null;
}

export interface ExtractionResult {
  intent?: string;
  days_worked?: string | number | null;
  daily_wage?: string | number | null;
  hours_worked?: string | number | null;
  wage_basis?: 'daily' | 'hourly';
  hourly_rate?: string | number | null;
  overtime_hours?: string | number | null;
  overtime_multiplier?: string | number | null;
  base_earned?: string | number | null;
  overtime_earned?: string | number | null;
  calculated_total?: string | number | null;
  possible_duplicates?: Array<{
    kind: 'work' | 'payment';
    record_id: string;
    date: string;
    employer_name?: string | null;
    amount: string;
    exact: boolean;
    message: string;
  }>;
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

export interface LedgerAlert {
  id: string;
  alert_type: 'recorded_balance' | 'unallocated_payment' | 'possible_duplicate' | 'rate_change' | 'possible_overpayment';
  severity: 'review' | 'information';
  employer_id?: string | null;
  employer_name?: string | null;
  amount?: string | null;
  source_record_ids: string[];
  source_records: Array<{
    id: string;
    record_type: 'work' | 'payment';
    date: string;
    amount: string;
    description?: string | null;
  }>;
  explanation: string;
  recommendation: string;
}
