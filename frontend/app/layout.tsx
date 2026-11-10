import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '../lib/auth-context';
import Navbar from '../components/Navbar';

export const metadata: Metadata = {
  title: 'MazdoorMitra - आपका काम, आपकी मज़दूरी, आपका रिकॉर्ड',
  description: 'Voice-first AI wage and work-record assistant for Indian daily-wage workers.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="hi" className="h-full bg-slate-50">
      <body className="min-h-full flex flex-col text-slate-900 bg-slate-50 pb-20">
        <AuthProvider>
          <div className="w-full max-w-md mx-auto min-h-screen flex flex-col bg-white shadow-xl relative">
            <main className="flex-1 pb-16">{children}</main>
            <Navbar />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
