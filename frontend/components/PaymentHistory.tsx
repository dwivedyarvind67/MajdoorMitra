'use client';

import React from 'react';
import { ArrowDownLeft } from 'lucide-react';
import { Payment } from '../types';

interface PaymentHistoryProps {
  payments: Payment[];
  isLoading?: boolean;
}

export default function PaymentHistory({ payments, isLoading }: PaymentHistoryProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse"></div>
        ))}
      </div>
    );
  }

  if (!payments || payments.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 bg-white rounded-2xl border border-dashed border-slate-200">
        <ArrowDownLeft className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm font-medium">कोई भुगतान रिकॉर्ड नहीं मिला</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {payments.map((p) => {
        const dateStr = new Date(p.payment_date).toLocaleDateString('hi-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        return (
          <div
            key={p.id}
            className="flex items-center justify-between p-3.5 bg-white border border-slate-100 rounded-xl shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <ArrowDownLeft className="w-5 h-5" />
              </div>
              <div className="text-left">
                <h4 className="text-sm font-bold text-slate-800">
                  {p.employer_name || 'मालिक का नाम नहीं'}
                </h4>
                <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                  <span>{dateStr}</span>
                  <span>•</span>
                  <span className="capitalize">{p.payment_type}</span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <span className="text-base font-extrabold text-emerald-700">
                +₹{p.amount}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
