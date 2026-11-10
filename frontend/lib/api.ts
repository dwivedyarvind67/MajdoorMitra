import type {
  Employer,
  ExtractionResponse,
  LedgerSummary,
  LedgerAlert,
  Payment,
  SpokenReceipt,
  StatementDetail,
  StatementListItem,
  TransactionList,
  VoiceConfirmation,
  VoiceReplyResponse,
  WorkEntry,
  AttendanceDay,
  WageAgreement,
  Worksite,
  EvidenceFileRecord,
  FinancialInsights,
  SavingsGoal,
  AssistanceResource,
  AssistanceFaq,
  PaymentRequestDraft,
} from '../types';

type WorkEntryInput = {
  work_date: string;
  days_worked: number | string;
  daily_wage?: number | string;
  hours_worked?: number | string;
  wage_basis?: 'daily' | 'hourly';
  hourly_rate?: number | string;
  overtime_hours?: number | string;
  overtime_multiplier?: number | string;
  employer_id?: string;
  worksite_id?: string;
  description?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type VoiceCorrections = {
  intent?: 'log_work' | 'log_payment';
  days_worked?: number | string | null;
  daily_wage?: number | string | null;
  hours_worked?: number | string | null;
  wage_basis?: 'daily' | 'hourly' | null;
  hourly_rate?: number | string | null;
  overtime_hours?: number | string | null;
  overtime_multiplier?: number | string | null;
  work_date?: string | null;
  amount_received?: number | string | null;
  payment_type?: 'cash' | 'upi' | 'bank' | 'advance' | 'other' | null;
  employer_name?: string | null;
  description?: string | null;
};

export type SpeechVoice = {
  id: string;
  gender: string;
  persona: string;
  description: string;
  languages: string[] | 'all';
};

export type VoiceCapabilities = {
  languages: Array<{ code: string; short_code: string; name: string; english_name: string }>;
  prisma: { model: string; configured: boolean; account_verification: string; languages: string[]; auto_detect: boolean; code_switching: { supported: boolean; format: string; max_languages: number } };
  timbre: {
    configured: boolean;
    v3_account_verification: string;
    models: Array<{ id: string; languages: string[]; voices: SpeechVoice[]; audio_tags: boolean }>;
    audio_tags: string[];
    speed: { min: number; max: number; default: number };
  };
  evon: { configured: boolean | null; access: string; reason: string; languages: string[] };
};

export type VoiceGeneration = {
  id: string;
  text: string;
  language: string;
  model_id: string;
  voice_id: string;
  status: 'success' | 'failed';
  latency_ms: number;
  audio_base64?: string;
  audio_content_type?: string;
  created_at: string;
};

export type VoiceHistoryItem = {
  id: string;
  text_input: string;
  language: string;
  model_id: string;
  voice_id: string;
  status: string;
  latency_ms?: number | null;
  created_at: string;
};

class ApiClient {
  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('mazdoor_token');
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers = new Headers(options.headers || {});

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(await this.getErrorMessage(response));
    }

    return response.json();
  }

  private async requestBlob(endpoint: string): Promise<Blob> {
    const headers = new Headers();
    const token = this.getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const response = await fetch(`${API_BASE}${endpoint}`, { headers });
    if (!response.ok) {
      throw new Error(await this.getErrorMessage(response));
    }
    return response.blob();
  }

  private async getErrorMessage(response: Response): Promise<string> {
    const errorData: unknown = await response.json().catch(() => null);
    if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
      const detail = errorData.detail;
      if (typeof detail === 'string') return detail;
    }
    return `Request failed with status ${response.status}`;
  }

  // Auth
  async register(data: { name: string; phone: string; pin: string; preferred_language?: string }) {
    return this.request<{ access_token: string; token_type: string; worker_id: string; name: string }>(
      '/api/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  }

  async login(data: { phone: string; pin: string }) {
    return this.request<{ access_token: string; token_type: string; worker_id: string; name: string }>(
      '/api/auth/login',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  }

  // Voice Sessions
  async createVoiceSession(language: string = 'hi') {
    return this.request<{ id: string; status: string; language: string; created_at: string }>(
      '/api/voice/sessions',
      {
        method: 'POST',
        body: JSON.stringify({ language }),
      }
    );
  }

  async uploadAudio(sessionId: string, audioBlob: Blob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');

    return this.request<{ id: string; transcript: string; status: string }>(
      `/api/voice/sessions/${sessionId}/audio`,
      {
        method: 'POST',
        body: formData,
      }
    );
  }

  async extractData(sessionId: string) {
    return this.request<ExtractionResponse>(`/api/voice/sessions/${sessionId}/extract`, {
      method: 'POST',
    });
  }

  async replySession(sessionId: string, text: string) {
    return this.request<VoiceReplyResponse>(`/api/voice/sessions/${sessionId}/reply`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  async replyAudio(sessionId: string, audioBlob: Blob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'clarification.wav');
    return this.request<VoiceReplyResponse>(`/api/voice/sessions/${sessionId}/reply/audio`, {
      method: 'POST',
      body: formData,
    });
  }

  async correctSession(sessionId: string, corrections: VoiceCorrections) {
    return this.request<VoiceReplyResponse>(`/api/voice/sessions/${sessionId}/correct`, {
      method: 'POST',
      body: JSON.stringify({ corrections }),
    });
  }

  async rejectSession(sessionId: string) {
    return this.request<{ id: string; status: string; message: string }>(
      `/api/voice/sessions/${sessionId}/reject`,
      { method: 'POST' }
    );
  }

  async confirmSession(sessionId: string) {
    return this.request<VoiceConfirmation>(
      `/api/voice/sessions/${sessionId}/confirm`,
      {
        method: 'POST',
      }
    );
  }

  async speakSummary(sessionId: string, text?: string) {
    return this.request<SpokenReceipt>(
      `/api/voice/sessions/${sessionId}/speak`,
      {
        method: 'POST',
        body: JSON.stringify({ text }),
      }
    );
  }

  async getVoiceCapabilities() {
    return this.request<VoiceCapabilities>('/api/voice/capabilities');
  }

  async generateStudioSpeech(data: {
    text: string;
    model_id: string;
    voice_id: string;
    language: string;
    speed: number;
  }) {
    return this.request<VoiceGeneration>('/api/voice/studio/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getVoiceHistory() {
    return this.request<VoiceHistoryItem[]>('/api/voice/studio/history');
  }

  async deleteVoiceHistory(id: string) {
    const token = this.getToken();
    const response = await fetch(`${API_BASE}/api/voice/studio/history/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error(await this.getErrorMessage(response));
  }

  // Ledger
  async getLedgerSummary(params?: { employer_id?: string; start_date?: string; end_date?: string }) {
    const query = new URLSearchParams();
    if (params?.employer_id) query.set('employer_id', params.employer_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';

    return this.request<LedgerSummary>(`/api/ledger/summary${qs}`);
  }

  async getWorkEntries(filters?: { start_date?: string; end_date?: string; employer_id?: string }) {
    const query = new URLSearchParams();
    if (filters?.start_date) query.set('start_date', filters.start_date);
    if (filters?.end_date) query.set('end_date', filters.end_date);
    if (filters?.employer_id) query.set('employer_id', filters.employer_id);
    const queryString = query.toString();
    return this.request<WorkEntry[]>(`/api/ledger/work${queryString ? `?${queryString}` : ''}`);
  }

  async addWorkEntry(data: WorkEntryInput) {
    return this.request<WorkEntry>('/api/ledger/work', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateWorkEntry(id: string, data: WorkEntryInput) {
    return this.request<WorkEntry>(`/api/ledger/work/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getAttendanceCalendar(year: number, month: number, employerId?: string) {
    const query = new URLSearchParams({ year: String(year), month: String(month) });
    if (employerId) query.set('employer_id', employerId);
    return this.request<AttendanceDay[]>(`/api/ledger/calendar?${query}`);
  }

  async getPayments() {
    return this.request<Payment[]>('/api/ledger/payments');
  }

  async allocatePayment(paymentId: string, workEntryId: string, amount: number | string) {
    return this.request<{
      id: string;
      worker_id: string;
      payment_id: string;
      work_entry_id: string;
      amount: string;
      created_at: string;
    }>(`/api/ledger/payments/${encodeURIComponent(paymentId)}/allocations`, {
      method: 'POST',
      body: JSON.stringify({ work_entry_id: workEntryId, amount }),
    });
  }

  async addPayment(data: {
    payment_date: string;
    amount: number | string;
    payment_type: string;
    employer_id?: string;
    notes?: string;
  }) {
    return this.request<Payment>('/api/ledger/payments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTransactions(
    limit: number = 50,
    filters?: { employer_id?: string; start_date?: string; end_date?: string },
  ) {
    const query = new URLSearchParams({ limit: String(limit) });
    if (filters?.employer_id) query.set('employer_id', filters.employer_id);
    if (filters?.start_date) query.set('start_date', filters.start_date);
    if (filters?.end_date) query.set('end_date', filters.end_date);
    return this.request<TransactionList>(`/api/ledger/transactions?${query.toString()}`);
  }

  async getLedgerAlerts() {
    return this.request<LedgerAlert[]>('/api/ledger/alerts');
  }

  // Employers
  async getEmployers() {
    return this.request<Employer[]>('/api/employers');
  }

  async addEmployer(data: { name: string; contact_details?: string }) {
    return this.request<Employer>('/api/employers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWorksites(employerId: string) {
    return this.request<Worksite[]>(`/api/employers/${encodeURIComponent(employerId)}/worksites`);
  }

  async addWorksite(employerId: string, data: { name: string; address?: string }) {
    return this.request<Worksite>(`/api/employers/${encodeURIComponent(employerId)}/worksites`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWageAgreements(employerId: string, worksiteId?: string) {
    const query = new URLSearchParams();
    if (worksiteId) query.set('worksite_id', worksiteId);
    const queryString = query.toString();
    return this.request<WageAgreement[]>(
      `/api/employers/${encodeURIComponent(employerId)}/agreements${queryString ? `?${queryString}` : ''}`,
    );
  }

  async addWageAgreement(employerId: string, data: {
    worksite_id?: string;
    wage_basis: 'daily' | 'hourly';
    daily_rate?: number | string;
    hourly_rate?: number | string;
    overtime_multiplier?: number | string;
    effective_from: string;
    effective_to?: string;
    terms?: string;
  }) {
    return this.request<WageAgreement>(`/api/employers/${encodeURIComponent(employerId)}/agreements`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Statements
  async getStatements() {
    return this.request<StatementListItem[]>('/api/statements');
  }

  async getStatement(id: string) {
    return this.request<StatementDetail>(`/api/statements/${id}`);
  }

  downloadStatementPdf(id: string): Promise<Blob> {
    return this.requestBlob(`/api/statements/${encodeURIComponent(id)}/pdf`);
  }

  downloadLedgerStatement(filters: { start_date?: string; end_date?: string; employer_id?: string }): Promise<Blob> {
    const query = new URLSearchParams();
    if (filters.start_date) query.set('start_date', filters.start_date);
    if (filters.end_date) query.set('end_date', filters.end_date);
    if (filters.employer_id) query.set('employer_id', filters.employer_id);
    return this.requestBlob(`/api/statements/export${query.toString() ? `?${query.toString()}` : ''}`);
  }

  async getEvidence() {
    return this.request<EvidenceFileRecord[]>('/api/evidence');
  }

  async uploadEvidence(data: {
    file: File;
    document_type: 'payment_receipt' | 'wage_agreement' | 'work_document' | 'audio' | 'other';
    statement_id?: string;
    work_entry_id?: string;
    payment_id?: string;
  }) {
    const form = new FormData();
    form.append('file', data.file);
    form.append('consent_given', 'true');
    form.append('document_type', data.document_type);
    if (data.statement_id) form.append('statement_id', data.statement_id);
    if (data.work_entry_id) form.append('work_entry_id', data.work_entry_id);
    if (data.payment_id) form.append('payment_id', data.payment_id);
    return this.request<EvidenceFileRecord>('/api/evidence', { method: 'POST', body: form });
  }

  async getEvidencePreview(id: string) {
    return this.requestBlob(`/api/evidence/${encodeURIComponent(id)}/preview`);
  }

  async downloadEvidence(id: string) {
    return this.requestBlob(`/api/evidence/${encodeURIComponent(id)}/download`);
  }

  async deleteEvidence(id: string) {
    const token = this.getToken();
    const response = await fetch(`${API_BASE}/api/evidence/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error(await this.getErrorMessage(response));
  }

  async getFinancialInsights(months: number = 6) {
    return this.request<FinancialInsights>(`/api/insights?months=${months}`);
  }

  async getSavingsGoals() {
    return this.request<SavingsGoal[]>('/api/insights/savings-goals');
  }

  async createSavingsGoal(data: { name: string; target_amount: string; target_date?: string }) {
    return this.request<SavingsGoal>('/api/insights/savings-goals', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async updateSavingsGoal(id: string, active: boolean) {
    return this.request<SavingsGoal>(`/api/insights/savings-goals/${encodeURIComponent(id)}`, {
      method: 'PATCH', body: JSON.stringify({ active }),
    });
  }

  async getAssistanceResources() {
    return this.request<AssistanceResource[]>('/api/assistance/resources');
  }

  async getAssistanceFaqs() {
    return this.request<{ items: AssistanceFaq[]; disclaimer: string }>('/api/assistance/faqs');
  }

  async createPaymentRequestDraft(employerId?: string, language: 'hi' | 'en' = 'hi') {
    const query = new URLSearchParams({ language });
    if (employerId) query.set('employer_id', employerId);
    return this.request<PaymentRequestDraft>(`/api/assistance/payment-request?${query.toString()}`);
  }
}

export const api = new ApiClient();
