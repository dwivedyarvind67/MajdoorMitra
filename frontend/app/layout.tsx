import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '../lib/auth-context';
import { LanguageProvider } from '../lib/language-context';
import Navbar from '../components/Navbar';

export const metadata: Metadata = {
  title: 'MazdoorMitra — आपका काम, आपकी मज़दूरी',
  description: 'बोलकर काम और मज़दूरी का साफ़, भरोसेमंद रिकॉर्ड रखें।',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hi" className="h-full">
      <body className="min-h-full bg-[#f4f4f5] text-zinc-950 antialiased">
        <LanguageProvider>
          <AuthProvider>
            <Navbar />
            <main className="relative mx-auto min-h-[calc(100dvh-5rem)] w-full max-w-[1440px] px-0 pb-[calc(6.5rem+env(safe-area-inset-bottom))] pt-5 md:min-h-[calc(100dvh-4.5rem)] md:px-8 md:pb-12 md:pt-10">
              {children}
            </main>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
