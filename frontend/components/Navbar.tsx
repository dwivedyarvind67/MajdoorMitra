'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, HandCoins, History, Home, Mic, Users } from 'lucide-react';
import { useAuth } from '../lib/auth-context';

const signedInItems = [
  { label: 'होम', href: '/', icon: Home },
  { label: 'हिसाब', href: '/dashboard', icon: FileText },
  { label: 'बोलें', href: '/voice', icon: Mic, highlight: true },
  { label: 'इतिहास', href: '/history', icon: History },
  { label: 'मालिक', href: '/employers', icon: Users },
];

export default function Navbar() {
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;

  const items = isAuthenticated ? signedInItems : [{ label: 'होम', href: '/', icon: Home }];
  return (
    <>
      <header className="sticky top-0 z-40 hidden border-b border-[#e7e5dc]/90 bg-[#f8f7f2]/90 backdrop-blur-xl md:block">
        <div className="mx-auto flex h-[4.5rem] max-w-[1440px] items-center justify-between px-8">
          <Link href="/" className="flex items-center gap-3 rounded-xl" aria-label="MazdoorMitra होम">
            <span className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#173b2f] text-[#f8d89c] shadow-sm">
              <HandCoins className="h-5 w-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-[17px] font-black tracking-tight text-[#173b2f]">MazdoorMitra</span>
              <span className="-mt-0.5 block text-[11px] font-medium text-slate-500">आपका काम · आपका हिसाब</span>
            </span>
          </Link>

          {isAuthenticated ? (
            <nav aria-label="मुख्य नेविगेशन" className="flex items-center gap-1">
              {items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                    className={`inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-bold transition ${active ? 'bg-[#e5ece4] text-[#173b2f]' : 'text-slate-600 hover:bg-white hover:text-[#173b2f]'}`}>
                    <Icon className="h-[17px] w-[17px]" aria-hidden="true" />{item.label}
                  </Link>
                );
              })}
            </nav>
          ) : (
            <Link href="/auth" className="inline-flex min-h-11 items-center rounded-xl bg-[#173b2f] px-5 text-sm font-bold text-white shadow-sm transition hover:bg-[#22543f]">
              लॉग इन करें
            </Link>
          )}
        </div>
      </header>

      <nav aria-label="मुख्य नेविगेशन" className="fixed inset-x-0 bottom-0 z-50 border-t border-[#e7e5dc] bg-[#fffefa]/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_30px_rgba(25,43,33,0.08)] backdrop-blur-xl md:hidden">
        <div className="mx-auto flex h-[4.35rem] max-w-xl items-center justify-around px-2">
          {items.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            if (item.highlight) {
              return (
                <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                  className="-mt-3 flex min-w-[4.25rem] flex-col items-center justify-center gap-0.5 rounded-xl px-2 focus:outline-none">
                  <span className={`flex h-[3.2rem] w-[3.2rem] items-center justify-center rounded-[20px] border-[4px] border-[#fffefa] shadow-lg transition ${active ? 'bg-[#b96b27] text-white' : 'bg-[#173b2f] text-white'}`}>
                    <Icon className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <span className="text-[11px] font-extrabold text-[#173b2f]">{item.label}</span>
                </Link>
              );
            }
            return (
              <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                className={`flex min-w-[3.75rem] flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 transition ${active ? 'text-[#246443]' : 'text-slate-500 hover:text-slate-900'}`}>
                <Icon className={`h-5 w-5 ${active ? 'stroke-[2.5]' : ''}`} aria-hidden="true" />
                <span className="text-[10px] font-bold">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
