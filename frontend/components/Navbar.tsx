'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AudioLines, CalendarDays, CircleHelp, FileText, HandCoins, History, Home, Mic, ShieldCheck, TrendingUp, Users } from 'lucide-react';
import { useAuth } from '../lib/auth-context';
import { useLanguage } from '../lib/language-context';
import LanguageToggle from './LanguageToggle';

export default function Navbar() {
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const { t } = useLanguage();
  if (isLoading) return null;

  const signedInItems = [
    { label: t.home, href: '/', icon: Home },
    { label: t.dashboard, href: '/dashboard', icon: FileText },
    { label: t.voice, href: '/voice', icon: Mic, highlight: true },
    { label: t.studio, href: '/voice-studio', icon: AudioLines },
    { label: t.work, href: '/diary', icon: CalendarDays },
    { label: t.evidence, href: '/evidence', icon: ShieldCheck },
    { label: t.insights, href: '/insights', icon: TrendingUp },
    { label: t.help, href: '/help', icon: CircleHelp },
    { label: t.history, href: '/history', icon: History },
    { label: t.employers, href: '/employers', icon: Users },
  ];

  const items = isAuthenticated ? signedInItems : [{ label: t.home, href: '/', icon: Home }];
  const mobileItems = isAuthenticated
    ? signedInItems.filter((item) => item.href !== '/' && item.href !== '/employers' && item.href !== '/insights' && item.href !== '/voice-studio')
    : items;
  return (
    <>
      <header className="sticky top-0 z-40 hidden border-b border-[#e4e4e7]/90 bg-[#fafafa]/90 backdrop-blur-xl md:block">
        <div className="mx-auto flex h-[4.5rem] max-w-[1440px] items-center justify-between px-8">
          <Link href="/" className="flex items-center gap-3 rounded-xl" aria-label="MazdoorMitra होम">
            <span className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#27272a] text-[#ffffff] shadow-sm">
              <HandCoins className="h-5 w-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-[17px] font-black tracking-tight text-[#27272a]">MazdoorMitra</span>
              <span className="-mt-0.5 block text-[11px] font-medium text-slate-500">{t.tagline}</span>
            </span>
          </Link>

          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <nav aria-label="मुख्य नेविगेशन" className="flex items-center gap-1">
                {items.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href;
                  return (
                    <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                      className={`inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-bold transition ${active ? 'bg-[#e4e4e7] text-[#27272a]' : 'text-slate-600 hover:bg-white hover:text-[#27272a]'}`}>
                      <Icon className="h-[17px] w-[17px]" aria-hidden="true" />{item.label}
                    </Link>
                  );
                })}
              </nav>
            ) : (
              <Link href="/auth" className="inline-flex min-h-11 items-center rounded-xl bg-[#27272a] px-5 text-sm font-bold text-white shadow-sm transition hover:bg-[#3f3f46]">
                {t.login}
              </Link>
            )}

            <div className="border-l border-[#e4e4e7] pl-3">
              <LanguageToggle />
            </div>
          </div>
        </div>
      </header>

      <nav aria-label="मुख्य नेविगेशन" className="fixed inset-x-0 bottom-0 z-50 border-t border-[#e4e4e7] bg-[#ffffff]/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_30px_rgba(24,24,27,0.08)] backdrop-blur-xl md:hidden">
        <div className="mx-auto flex h-[4.35rem] max-w-xl items-center justify-around px-2">
          {mobileItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            if (item.highlight) {
              return (
                <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                  className="-mt-3 flex min-w-[4.25rem] flex-col items-center justify-center gap-0.5 rounded-xl px-2 focus:outline-none">
                  <span className={`flex h-[3.2rem] w-[3.2rem] items-center justify-center rounded-[20px] border-[4px] border-[#ffffff] shadow-lg transition ${active ? 'bg-[#3f3f46] text-white' : 'bg-[#27272a] text-white'}`}>
                    <Icon className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <span className="text-[11px] font-extrabold text-[#27272a]">{item.label}</span>
                </Link>
              );
            }
            return (
              <Link key={item.href} href={item.href} aria-current={active ? 'page' : undefined}
                className={`flex min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-xl px-0.5 py-2 transition ${active ? 'text-[#27272a]' : 'text-slate-500 hover:text-slate-900'}`}>
                <Icon className={`h-5 w-5 ${active ? 'stroke-[2.5]' : ''}`} aria-hidden="true" />
                <span className="max-w-full text-center text-[9px] font-bold leading-3">{item.label}</span>
              </Link>
            );
          })}
          <div className="flex items-center px-1">
            <LanguageToggle compact />
          </div>
        </div>
      </nav>
    </>
  );
}
