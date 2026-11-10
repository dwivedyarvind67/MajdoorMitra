'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { ShieldCheck, Phone, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';

export default function AuthPage() {
  const router = useRouter();
  const { login, register } = useAuth();

  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const cleanPhone = phone.replace(/\D/g, '');
      if (isLogin) {
        await login(cleanPhone, pin);
      } else {
        await register(name, cleanPhone, pin);
      }
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'त्रुटि हुई। कृपया पुनः प्रयास करें।');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen px-6 py-8 justify-center">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-blue-600 text-white flex items-center justify-center mx-auto mb-3 shadow-lg">
          <ShieldCheck className="w-10 h-10" />
        </div>
        <h1 className="text-2xl font-black text-slate-900">
          {isLogin ? 'मज़दूर लॉगिन' : 'नया खाता बनाएं'}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          {isLogin
            ? 'अपना मोबाइल नंबर और 4 से 6 अंकों का पिन दर्ज करें'
            : 'सुरक्षित रिकॉर्ड रखने के लिए अपनी जानकारी भरें'}
        </p>
      </div>

      <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
        {error && (
          <div role="alert" className="mb-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                आपका नाम (Full Name)
              </label>
              <div className="relative">
                <User className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel"
                  maxLength={10}
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="उदा. रमेश कुमार"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              मोबाइल नंबर (Phone Number)
            </label>
            <div className="relative">
              <Phone className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                  placeholder="10 अंकों का मोबाइल नंबर"
                  className="min-h-12 w-full rounded-xl border border-slate-300 bg-slate-50 py-2.5 pl-10 pr-4 text-base font-semibold tracking-wider focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              सुरक्षा पिन (4 Digits PIN)
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="password"
                inputMode="numeric"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                maxLength={6}
                required
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="4 से 6 अंक"
                className="min-h-12 w-full rounded-xl border border-slate-300 bg-slate-50 py-2.5 pl-10 pr-4 font-mono text-lg font-bold tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-700 py-3.5 text-base font-bold text-white shadow-md transition hover:bg-blue-800 disabled:opacity-60"
          >
            {loading ? 'कृपया प्रतीक्षा करें...' : isLogin ? 'लॉग इन करें' : 'खाता बनाएं'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 text-center pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="text-xs font-bold text-blue-600 hover:underline"
          >
            {isLogin ? 'नया खाता बनाना है? रजिस्ट्रेशन करें' : 'पहले से खाता है? लॉग इन करें'}
          </button>
        </div>
      </div>
    </div>
  );
}
