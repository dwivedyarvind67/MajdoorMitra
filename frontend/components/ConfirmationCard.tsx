'use client';

import React, { useState } from 'react';
import { Check, X, Edit2, Calculator } from 'lucide-react';
import { ExtractionResult } from '../types';

interface ConfirmationCardProps {
  data: ExtractionResult;
  onReviewChanges: (data: ExtractionResult) => void;
  onConfirm: () => void;
  onReject: () => void;
  isConfirming?: boolean;
}

const fieldClass = 'min-h-12 w-full rounded-xl border border-[#e4e4e7] bg-white px-3 text-base font-semibold text-slate-950 focus:outline-none focus:ring-2 focus:ring-[#52525b]';
const rowClass = 'flex min-h-12 items-center justify-between gap-3 border-b border-[#e4e4e7] py-2 text-sm';

export default function ConfirmationCard({
  data,
  onReviewChanges,
  onConfirm,
  onReject,
  isConfirming,
}: ConfirmationCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState(data);

  const update = (key: keyof ExtractionResult, value: string) => {
    setFormData((current) => ({ ...current, [key]: value }));
  };
  const isPayment = formData.intent === 'log_payment';
  const isHourly = formData.wage_basis === 'hourly';

  return (
    <section className="my-4 rounded-[1.75rem] border border-[#e4e4e7] bg-[#ffffff] p-5 text-left shadow-[0_12px_34px_rgba(24,24,27,0.06)] sm:p-6" aria-labelledby="confirm-heading">
      <div className="flex items-start justify-between gap-3 border-b border-[#f4f4f5] pb-4">
        <div>
          <span className="text-sm font-extrabold text-[#71717a]">आपकी बताई जानकारी · जाँचें</span>
          <h2 id="confirm-heading" className="mt-1 text-xl font-black text-[#27272a]">
            {isPayment ? 'मिला हुआ भुगतान' : 'काम का हिसाब'}
          </h2>
        </div>
        <button
          type="button"
          onClick={() => setIsEditing((value) => !value)}
          aria-expanded={isEditing}
          className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-[#f4f4f5] px-3 text-sm font-extrabold text-[#3f3f46] hover:bg-[#e4e4e7]"
        >
          <Edit2 className="h-4 w-4" aria-hidden="true" />
          {isEditing ? 'देखें' : 'बदलें'}
        </button>
      </div>

      {!!formData.possible_duplicates?.length && (
        <aside role="note" aria-label="मिलते-जुलते पुराने रिकॉर्ड" className="mt-4 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-950">
          <p className="text-sm font-black">पहले का रिकॉर्ड जाँचें</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-6">
            {formData.possible_duplicates.map((match) => (
              <li key={match.record_id}>{match.message}{match.employer_name ? ` (${match.employer_name}, ₹${match.amount})` : ` (₹${match.amount})`}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs leading-5">अगर यह अलग काम या अलग भुगतान है, विवरण जाँचकर पुष्टि करें। हूबहू दोहराव सेव नहीं होगा।</p>
        </aside>
      )}

      <div className="space-y-1 py-4">
        {!isPayment && (
          <>
            {isEditing && (
              <label className={`${rowClass} items-start`}>
                <span className="pt-3 font-medium text-slate-700">मज़दूरी का हिसाब</span>
                <select aria-label="मज़दूरी का हिसाब" className={`${fieldClass} max-w-52`} value={formData.wage_basis ?? 'daily'} onChange={(event) => update('wage_basis', event.target.value)}>
                  <option value="daily">दिहाड़ी</option>
                  <option value="hourly">घंटे के हिसाब से</option>
                </select>
              </label>
            )}
            {!isHourly && (
              <>
                <label className={rowClass}>
                  <span className="font-medium text-slate-700">काम के दिन</span>
                  {isEditing ? (
                    <input aria-label="काम के दिन" className={`${fieldClass} max-w-52 text-right`} type="number" min="0" max="31" step="0.25" value={formData.days_worked ?? ''} onChange={(event) => update('days_worked', event.target.value)} />
                  ) : <span className="font-bold text-slate-900">{formData.days_worked ?? '—'} दिन</span>}
                </label>
                <label className={rowClass}>
                  <span className="font-medium text-slate-700">दैनिक मज़दूरी</span>
                  {isEditing ? (
                    <input aria-label="दैनिक मज़दूरी" className={`${fieldClass} max-w-52 text-right`} type="number" min="0" step="0.01" value={formData.daily_wage ?? ''} onChange={(event) => update('daily_wage', event.target.value)} />
                  ) : <span className="font-bold text-slate-900">₹{formData.daily_wage ?? '—'}</span>}
                </label>
              </>
            )}
            {(isHourly || formData.hours_worked != null || isEditing) && (
              <label className={rowClass}>
                <span className="font-medium text-slate-700">काम के घंटे</span>
                {isEditing ? (
                  <input aria-label="काम के घंटे" className={`${fieldClass} max-w-52 text-right`} type="number" min={isHourly ? '0.01' : '0'} max="24" step="0.25" value={formData.hours_worked ?? ''} onChange={(event) => update('hours_worked', event.target.value)} />
                ) : <span className="font-bold text-slate-900">{formData.hours_worked ?? '—'} घंटे</span>}
              </label>
            )}
            {isHourly && (
              <label className={rowClass}>
                <span className="font-medium text-slate-700">प्रति घंटे की मज़दूरी</span>
                {isEditing ? (
                  <input aria-label="प्रति घंटे की मज़दूरी" className={`${fieldClass} max-w-52 text-right`} type="number" min="0.01" step="0.01" value={formData.hourly_rate ?? ''} onChange={(event) => update('hourly_rate', event.target.value)} />
                ) : <span className="font-bold text-slate-900">₹{formData.hourly_rate ?? '—'} / घंटा</span>}
              </label>
            )}
            {(isEditing || Number(formData.overtime_hours ?? 0) > 0) && (
              <>
                <label className={rowClass}>
                  <span className="font-medium text-slate-700">ओवरटाइम के घंटे</span>
                  {isEditing ? (
                    <input aria-label="ओवरटाइम के घंटे" className={`${fieldClass} max-w-52 text-right`} type="number" min="0" max="24" step="0.25" value={formData.overtime_hours ?? '0'} onChange={(event) => update('overtime_hours', event.target.value)} />
                  ) : <span className="font-bold text-slate-900">{formData.overtime_hours} घंटे</span>}
                </label>
                <label className={rowClass}>
                  <span className="font-medium text-slate-700">ओवरटाइम गुणक</span>
                  {isEditing ? (
                    <input aria-label="ओवरटाइम गुणक" className={`${fieldClass} max-w-52 text-right`} type="number" min="1" max="3" step="0.1" value={formData.overtime_multiplier ?? '1.5'} onChange={(event) => update('overtime_multiplier', event.target.value)} />
                  ) : <span className="font-bold text-slate-900">× {formData.overtime_multiplier ?? '1.5'}</span>}
                </label>
              </>
            )}
            <div className="mt-3 rounded-2xl border border-[#e4e4e7] bg-[#f4f4f5] p-4" aria-live="polite">
              <div className="flex items-center gap-2 text-sm font-extrabold text-[#52525b]">
                <Calculator className="h-4 w-4" aria-hidden="true" />
                हिसाब का साफ़ बँटवारा
              </div>
              <dl className="mt-2 space-y-1.5 text-sm">
                <div className="flex justify-between gap-3"><dt className="text-slate-600">सामान्य कमाई</dt><dd className="font-bold text-slate-900">₹{formData.base_earned ?? '—'}</dd></div>
                {Number(formData.overtime_hours ?? 0) > 0 && <div className="flex justify-between gap-3"><dt className="text-slate-600">ओवरटाइम कमाई</dt><dd className="font-bold text-slate-900">₹{formData.overtime_earned ?? '—'}</dd></div>}
                <div className="flex justify-between gap-3 border-t border-[#e4e4e7] pt-2 text-base"><dt className="font-black text-[#27272a]">कुल कमाई</dt><dd className="font-black text-[#27272a]">₹{formData.calculated_total ?? '—'}</dd></div>
              </dl>
              {isEditing && <p className="mt-2 text-xs leading-5 text-slate-600">बदले हुए अंकों का नया हिसाब देखने के लिए नीचे “बदलाव जाँचें” दबाएँ।</p>}
            </div>
          </>
        )}

        {isPayment && (
          <>
            <label className={rowClass}>
              <span className="font-medium text-slate-700">मिली रकम</span>
              {isEditing ? (
                <input aria-label="मिली रकम" className={`${fieldClass} max-w-52 text-right`} type="number" min="0.01" step="0.01" value={formData.amount_received ?? ''} onChange={(event) => update('amount_received', event.target.value)} />
              ) : <span className="text-xl font-black text-[#52525b]">₹{formData.amount_received ?? '—'}</span>}
            </label>
            <label className={rowClass}>
              <span className="font-medium text-slate-700">भुगतान का तरीका</span>
              {isEditing ? (
                <select aria-label="भुगतान का तरीका" className={`${fieldClass} max-w-52`} value={formData.payment_type ?? ''} onChange={(event) => update('payment_type', event.target.value)}>
                  <option value="">चुनें</option><option value="cash">नकद</option><option value="upi">UPI</option><option value="bank">बैंक</option><option value="advance">अग्रिम</option><option value="other">अन्य</option>
                </select>
              ) : <span className="font-bold text-slate-900">{formData.payment_type ?? '—'}</span>}
            </label>
          </>
        )}

        <label className={rowClass}>
          <span className="font-medium text-slate-700">तारीख</span>
          {isEditing ? (
            <input aria-label="तारीख" className={`${fieldClass} max-w-52 text-right`} type="date" value={formData.work_date ?? ''} onChange={(event) => update('work_date', event.target.value)} />
          ) : <span className="font-bold text-slate-900">{formData.work_date ?? '—'}</span>}
        </label>
        <label className={rowClass}>
          <span className="font-medium text-slate-700">मालिक / ठेकेदार</span>
          {isEditing ? (
            <input aria-label="मालिक या ठेकेदार" className={`${fieldClass} max-w-52 text-right`} type="text" value={formData.employer_name ?? ''} onChange={(event) => update('employer_name', event.target.value)} placeholder="नाम (वैकल्पिक)" />
          ) : <span className="font-bold text-slate-900">{formData.employer_name || 'नाम नहीं बताया'}</span>}
        </label>

        {isEditing && (
          <label className="block py-2 text-sm font-medium text-slate-700">
            काम का विवरण (वैकल्पिक)
            <textarea aria-label="काम का विवरण" className="mt-2 min-h-20 w-full rounded-xl border border-[#e4e4e7] p-3 text-base focus:outline-none focus:ring-2 focus:ring-[#52525b]" maxLength={500} value={formData.description ?? ''} onChange={(event) => update('description', event.target.value)} />
          </label>
        )}
      </div>

      <p className="border-t border-[#f4f4f5] pt-3 text-sm leading-6 text-slate-600">
        यह जानकारी आपकी आवाज़ से निकली है। इसमें बदलाव आप कर सकते हैं; आपके साफ़ कहने के बाद ही यह हिसाब में जुड़ेगी।
      </p>

      <div className="flex gap-3 pt-4">
        {isEditing ? (
          <button type="button" onClick={() => onReviewChanges(formData)} disabled={isConfirming} className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-[#27272a] px-4 text-base font-bold text-white shadow hover:bg-[#3f3f46] disabled:opacity-60">
            <Calculator className="h-5 w-5" aria-hidden="true" />
            {isConfirming ? 'हिसाब जाँचा जा रहा है…' : 'बदलाव जाँचें'}
          </button>
        ) : (
          <button type="button" onClick={onConfirm} disabled={isConfirming} className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-[#52525b] px-4 text-base font-bold text-white shadow hover:bg-[#3f3f46] disabled:opacity-60">
            <Check className="h-5 w-5" aria-hidden="true" />
            {isConfirming ? 'सेव हो रहा है…' : 'पुष्टि करें और सेव करें'}
          </button>
        )}
        <button type="button" onClick={onReject} disabled={isConfirming} aria-label="ड्राफ़्ट रद्द करें" className="flex min-h-12 min-w-12 items-center justify-center rounded-xl border border-[#e4e4e7] bg-white text-slate-700 hover:bg-red-50 hover:text-red-700 disabled:opacity-60">
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
