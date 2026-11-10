'use client';

import React, { useState } from 'react';
import { Check, X, Edit2 } from 'lucide-react';
import { ExtractionResult } from '../types';

interface ConfirmationCardProps {
  data: ExtractionResult;
  onConfirm: (data: ExtractionResult) => void;
  onReject: () => void;
  isConfirming?: boolean;
}

const fieldClass = 'w-36 min-h-11 border border-slate-300 rounded-lg px-3 py-2 text-right text-base font-semibold focus:outline-none focus:ring-2 focus:ring-blue-600';

function totalPreview(days: string, wage: string): string {
  try {
    const zero = BigInt(0);
    const hundred = BigInt(100);
    const fifty = BigInt(50);
    const scaled = (value: string) => {
      const [whole = '0', fraction = ''] = value.trim().split('.');
      const negative = whole.startsWith('-');
      const absoluteWhole = negative ? whole.slice(1) : whole;
      const cents = BigInt(absoluteWhole || '0') * hundred + BigInt((fraction + '00').slice(0, 2));
      return negative ? -cents : cents;
    };
    const product = scaled(days) * scaled(wage);
    const paise = product >= zero ? (product + fifty) / hundred : (product - fifty) / hundred;
    const sign = paise < zero ? '-' : '';
    const absolute = paise < zero ? -paise : paise;
    return `${sign}${absolute / hundred}.${String(absolute % hundred).padStart(2, '0')}`;
  } catch {
    return '0.00';
  }
}

export default function ConfirmationCard({ data, onConfirm, onReject, isConfirming }: ConfirmationCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState(data);

  const update = (key: keyof ExtractionResult, value: string) => {
    setFormData((current) => ({ ...current, [key]: value }));
  };
  const isPayment = formData.intent === 'log_payment';
  const total = totalPreview(String(formData.days_worked ?? '0'), String(formData.daily_wage ?? '0'));

  return (
    <section className="my-4 rounded-2xl border-2 border-blue-600 bg-white p-5 text-left shadow-md" aria-labelledby="confirm-heading">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <span className="text-sm font-bold text-blue-700">बताई गई जानकारी · जाँचें</span>
          <h2 id="confirm-heading" className="mt-1 text-lg font-bold text-slate-900">
            {isPayment ? 'मिला भुगतान (Payment received)' : 'काम का रिकॉर्ड (Work record)'}
          </h2>
        </div>
        <button
          type="button"
          onClick={() => setIsEditing((value) => !value)}
          aria-expanded={isEditing}
          className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-100 px-3 text-sm font-bold text-slate-800 hover:bg-slate-200"
        >
          <Edit2 className="h-4 w-4" aria-hidden="true" />
          {isEditing ? 'पूरा हुआ' : 'बदलें'}
        </button>
      </div>

      <div className="space-y-4 py-4">
        {!isPayment && (
          <>
            <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">काम के दिन</span>
              {isEditing ? (
                <input aria-label="काम के दिन" className={fieldClass} type="number" min="0" max="31" step="0.25" value={formData.days_worked ?? ''} onChange={(event) => update('days_worked', event.target.value)} />
              ) : <span className="font-bold text-slate-900">{formData.days_worked ?? '—'} दिन</span>}
            </label>
            <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">दैनिक मज़दूरी</span>
              {isEditing ? (
                <input aria-label="दैनिक मज़दूरी" className={fieldClass} type="number" min="0" step="0.01" value={formData.daily_wage ?? ''} onChange={(event) => update('daily_wage', event.target.value)} />
              ) : <span className="font-bold text-slate-900">₹{formData.daily_wage ?? '—'}</span>}
            </label>
            <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">काम के घंटे (वैकल्पिक)</span>
              {isEditing ? (
                <input aria-label="काम के घंटे" className={fieldClass} type="number" min="0" max="24" step="0.25" value={formData.hours_worked ?? ''} onChange={(event) => update('hours_worked', event.target.value)} />
              ) : <span className="font-bold text-slate-900">{formData.hours_worked ?? '—'}</span>}
            </label>
            <div className="flex min-h-12 items-center justify-between gap-3 border-y border-slate-200 py-2 text-sm">
              <span className="font-bold text-slate-800">हिसाब की गई कमाई</span>
              <span className="text-xl font-black text-blue-800">₹{total}</span>
            </div>
          </>
        )}

        {isPayment && (
          <>
            <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">मिली रकम</span>
              {isEditing ? (
                <input aria-label="मिली रकम" className={fieldClass} type="number" min="0" step="0.01" value={formData.amount_received ?? ''} onChange={(event) => update('amount_received', event.target.value)} />
              ) : <span className="text-xl font-black text-emerald-800">₹{formData.amount_received ?? '—'}</span>}
            </label>
            <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">भुगतान का तरीका</span>
              {isEditing ? (
                <select aria-label="भुगतान का तरीका" className={fieldClass} value={formData.payment_type ?? ''} onChange={(event) => update('payment_type', event.target.value)}>
                  <option value="">चुनें</option>
                  <option value="cash">नकद</option>
                  <option value="upi">UPI</option>
                  <option value="bank">बैंक</option>
                  <option value="advance">अग्रिम</option>
                  <option value="other">अन्य</option>
                </select>
              ) : <span className="font-bold text-slate-900">{formData.payment_type ?? '—'}</span>}
            </label>
          </>
        )}

        <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
          <span className="font-medium text-slate-700">तारीख</span>
          {isEditing ? (
            <input aria-label="तारीख" className={fieldClass} type="date" value={formData.work_date ?? ''} onChange={(event) => update('work_date', event.target.value)} />
          ) : <span className="font-bold text-slate-900">{formData.work_date ?? '—'}</span>}
        </label>

        <label className="flex min-h-11 items-center justify-between gap-3 text-sm">
          <span className="font-medium text-slate-700">मालिक / ठेकेदार</span>
          {isEditing ? (
            <input aria-label="मालिक या ठेकेदार" className={fieldClass} type="text" value={formData.employer_name ?? ''} onChange={(event) => update('employer_name', event.target.value)} placeholder="नाम (वैकल्पिक)" />
          ) : <span className="font-bold text-slate-900">{formData.employer_name || 'नाम नहीं बताया'}</span>}
        </label>

        {isEditing && (
          <label className="block text-sm font-medium text-slate-700">
            काम का विवरण (वैकल्पिक)
            <textarea aria-label="काम का विवरण" className="mt-2 min-h-20 w-full rounded-lg border border-slate-300 p-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-600" maxLength={500} value={formData.description ?? ''} onChange={(event) => update('description', event.target.value)} />
          </label>
        )}
      </div>

      <p className="border-t border-slate-200 pt-3 text-sm leading-6 text-slate-600">
        यह जानकारी आपकी आवाज़ से निकाली गई है। सेव करने से पहले जाँचें; आपकी पुष्टि के बाद ही हिसाब में जुड़ेगी।
      </p>

      <div className="flex gap-3 pt-4">
        <button
          type="button"
          onClick={() => onConfirm(formData)}
          disabled={isConfirming}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 text-base font-bold text-white shadow hover:bg-emerald-800 disabled:opacity-60"
        >
          <Check className="h-5 w-5" aria-hidden="true" />
          {isConfirming ? 'सेव हो रहा है…' : 'पुष्टि करें और सेव करें'}
        </button>
        <button
          type="button"
          onClick={onReject}
          disabled={isConfirming}
          aria-label="ड्राफ़्ट रद्द करें"
          className="flex min-h-12 min-w-12 items-center justify-center rounded-xl border border-slate-300 bg-slate-50 text-slate-700 hover:bg-red-50 hover:text-red-700 disabled:opacity-60"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
