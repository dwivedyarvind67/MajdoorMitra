import type {
  Employer,
  ExtractionResponse,
  LedgerSummary,
  Payment,
  SpokenReceipt,
  StatementDetail,
  StatementListItem,
  TransactionList,
  VoiceConfirmation,
  VoiceReplyResponse,
  WorkEntry,
} from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type VoiceCorrections = {
  intent?: 'log_work' | 'log_payment';
  days_worked?: number | string | null;
  daily_wage?: number | string | null;
  hours_worked?: number | string | null;
  work_date?: string | null;
  amount_received?: number | string | null;
  payment_type?: 'cash' | 'upi' | 'bank' | 'advance' | 'other' | null;
  employer_name?: string | null;
  description?: string | null;
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

  // Ledger
  async getLedgerSummary(params?: { employer_id?: string; start_date?: string; end_date?: string }) {
    const query = new URLSearchParams();
    if (params?.employer_id) query.set('employer_id', params.employer_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';

    return this.request<LedgerSummary>(`/api/ledger/summary${qs}`);
  }

  async getWorkEntries() {
    return this.request<WorkEntry[]>('/api/ledger/work');
  }

  async addWorkEntry(data: {
    work_date: string;
    days_worked: number | string;
    daily_wage: number | string;
    hours_worked?: number | string;
    employer_id?: string;
    description?: string;
  }) {
    return this.request<WorkEntry>('/api/ledger/work', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPayments() {
    return this.request<Payment[]>('/api/ledger/payments');
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

  async getTransactions(limit: number = 50) {
    return this.request<TransactionList>(`/api/ledger/transactions?limit=${limit}`);
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
}

export const api = new ApiClient();
