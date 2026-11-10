'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Mic, History, Users, FileText } from 'lucide-react';
import { useAuth } from '../lib/auth-context';

export default function Navbar() {
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();

  const navItems = isAuthenticated
    ? [
        { label: 'होम', href: '/', icon: Home },
        { label: 'हिसाब', href: '/dashboard', icon: FileText },
        { label: 'बोलें', href: '/voice', icon: Mic, highlight: true },
        { label: 'इतिहास', href: '/history', icon: History },
        { label: 'मालिक', href: '/employers', icon: Users },
      ]
    : [{ label: 'होम', href: '/', icon: Home }];

  if (isLoading) return null;

  return (
    <nav aria-label="मुख्य नेविगेशन" className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white shadow-lg md:mx-auto md:max-w-md">
      <div className="flex items-center justify-around h-16 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          if (item.highlight) {
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                className="-mt-5 flex flex-col items-center justify-center rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-700"
              >
                <div className="w-14 h-14 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-lg border-4 border-white hover:bg-blue-700 transition">
                  <Icon className="w-7 h-7" />
                </div>
                <span className="text-xs font-bold text-blue-700 mt-1">{item.label}</span>
              </Link>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={`flex flex-col items-center justify-center flex-1 py-1 transition ${
                isActive ? 'text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <Icon className="w-5 h-5 mb-1" />
              <span className="text-[11px]">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
