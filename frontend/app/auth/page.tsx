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
    <div className="mx-auto grid min-h-[calc(100dvh-10rem)] w-full max-w-5xl content-center gap-8 px-5 py-8 sm:px-7 md:min-h-[calc(100dvh-11rem)] md:grid-cols-[1fr_0.9fr] md:items-center md:gap-14 md:px-8">
      <div className="mb-1 text-center md:text-left">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-[22px] bg-[#173b2f] text-[#f1bf68] shadow-lg md:mx-0">
          <ShieldCheck className="h-9 w-9" />
        </div>
        <p className="mb-2 text-sm font-extrabold tracking-wide text-[#a66e2a]">MazdoorMitra · आपका अपना हिसाब</p>
        <h1 className="text-3xl font-black tracking-tight text-[#173b2f] sm:text-4xl">
          {isLogin ? 'मज़दूर लॉगिन' : 'नया खाता बनाएं'}
        </h1>
        <p className="mx-auto mt-3 max-w-md text-base leading-7 text-slate-600 md:mx-0">
          {isLogin
            ? 'अपना मोबाइल नंबर और 4 से 6 अंकों का सुरक्षा पिन दर्ज करें।'
            : 'अपनी जानकारी भरें और बोलकर काम व भुगतान का रिकॉर्ड रखना शुरू करें।'}
        </p>
        <div className="mx-auto mt-6 hidden max-w-md space-y-3 text-left md:mx-0 md:block">
          <p className="flex items-center gap-3 rounded-2xl border border-[#e2e6dc] bg-[#fffefa]/80 px-4 py-3 text-sm font-semibold text-[#35483b]"><span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#e6efe4] text-[#28734e]"><ShieldCheck className="h-4 w-4" /></span>आपकी पुष्टि के बाद ही हिसाब में रिकॉर्ड जुड़ता है।</p>
          <p className="flex items-center gap-3 rounded-2xl border border-[#e2e6dc] bg-[#fffefa]/80 px-4 py-3 text-sm font-semibold text-[#35483b]"><Phone className="ml-2 h-4 w-4 text-[#28734e]" />मोबाइल नंबर और निजी पिन से आपका खाता सुरक्षित रहता है।</p>
        </div>
      </div>

      <div className="rounded-[1.75rem] border border-[#e7e5dc] bg-[#fffefa] p-5 shadow-[0_20px_60px_rgba(40,54,43,0.08)] sm:p-7">
        {error && (
          <div role="alert" className="mb-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
            <label htmlFor="worker-name" className="mb-1.5 block text-sm font-bold text-slate-800">
                आपका नाम
              </label>
              <div className="relative">
                <User className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  id="worker-name"
                  type="text"
                  autoComplete="name"
                  maxLength={255}
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="उदा. रमेश कुमार"
                  className="min-h-12 w-full rounded-xl border border-[#d8ddd4] bg-[#fafaf6] py-2.5 pl-10 pr-4 text-base font-medium focus:outline-none focus:ring-2 focus:ring-[#28734e]"
                />
              </div>
            </div>
          )}

          <div>
            <label htmlFor="worker-phone" className="mb-1.5 block text-sm font-bold text-slate-800">
              मोबाइल नंबर
            </label>
            <div className="relative">
              <Phone className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                id="worker-phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                maxLength={10}
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="10 अंकों का मोबाइल नंबर"
                className="min-h-12 w-full rounded-xl border border-slate-300 bg-slate-50 py-2.5 pl-10 pr-4 text-base font-semibold tracking-wider focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="worker-pin" className="mb-1.5 block text-sm font-bold text-slate-800">
              सुरक्षा पिन <span className="font-medium text-slate-500">(4 से 6 अंक)</span>
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                id="worker-pin"
                type="password"
                inputMode="numeric"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                minLength={4}
                maxLength={6}
                pattern="[0-9]{4,6}"
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
            className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#173b2f] py-3.5 text-base font-extrabold text-white shadow-md transition hover:bg-[#22543f] disabled:cursor-wait disabled:opacity-60"
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
            className="min-h-11 rounded-lg px-2 text-sm font-extrabold text-[#28734e] hover:bg-[#f0f4ed]"
          >
            {isLogin ? 'नया खाता बनाना है? रजिस्ट्रेशन करें' : 'पहले से खाता है? लॉग इन करें'}
          </button>
        </div>
      </div>
    </div>
  );
}
