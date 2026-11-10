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
  worksite_id?: string;
  worksite_name?: string;
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

export interface Worksite {
  id: string;
  worker_id: string;
  employer_id?: string | null;
  name: string;
  address?: string | null;
  created_at: string;
}

export interface WageAgreement {
  id: string;
  worker_id: string;
  employer_id: string;
  worksite_id?: string | null;
  wage_basis: 'daily' | 'hourly';
  daily_rate?: string | null;
  hourly_rate?: string | null;
  overtime_multiplier: string;
  effective_from: string;
  effective_to?: string | null;
  terms?: string | null;
  created_at: string;
}

export interface AttendanceDay {
  date: string;
  recorded_entries: number;
  total_days_worked: string;
  total_hours_worked: string;
  total_earned: string;
}

export interface EvidenceFileRecord {
  id: string;
  worker_id: string;
  file_name?: string | null;
  document_type?: string | null;
  content_type?: string | null;
  size_bytes?: number | null;
  checksum_sha256?: string | null;
  consent_given: boolean;
  statement_id?: string | null;
  work_entry_id?: string | null;
  payment_id?: string | null;
  created_at: string;
}

export interface MonthlyInsight {
  month: string;
  earnings: string;
  payments: string;
  pending: string;
  recorded_workdays: number;
  worked_days: string;
}

export interface EmployerInsight {
  employer_id?: string | null;
  employer_name: string;
  earnings: string;
  payments: string;
  pending: string;
}

export interface FinancialInsights {
  period_start: string;
  period_end: string;
  total_earnings: string;
  total_payments: string;
  total_pending: string;
  average_daily_earnings: string;
  recorded_workdays: number;
  worked_days: string;
  monthly: MonthlyInsight[];
  employers: EmployerInsight[];
}

export interface SavingsGoal {
  id: string;
  worker_id: string;
  name: string;
  target_amount: string;
  target_date?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssistanceResource {
  id: string;
  title: string;
  description: string;
  url: string;
  source: string;
  phone?: string | null;
  availability?: string | null;
}

export interface AssistanceFaq {
  id: string;
  question_hi: string;
  answer_hi: string;
  question_en: string;
  answer_en: string;
}

export interface PaymentRequestDraft {
  employer_id?: string | null;
  employer_name: string;
  amount_in_recorded_balance: string;
  language: 'hi' | 'en';
  message: string;
  delivery: 'copy_only';
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
