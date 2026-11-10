'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export type Language = 'hi' | 'en';

export interface Translations {
  // Common / Navbar
  home: string;
  dashboard: string;
  voice: string;
  studio: string;
  work: string;
  evidence: string;
  insights: string;
  help: string;
  history: string;
  employers: string;
  login: string;
  logout: string;
  tagline: string;
  languageLabel: string;

  // Home Page
  heroBadge: string;
  greetingReady: string;
  guestTitle: string;
  heroDescription: string;
  recordVoiceBtn: string;
  startBtn: string;
  viewFullDashboardBtn: string;
  speakToRecord: string;
  badgeConfirmFirst: string;
  badgeTimestamped: string;
  earningsAndPayments: string;
  summaryAtAGlance: string;
  details: string;
  byEmployer: string;
  byEmployerSub: string;
  wageSlips: string;
  wageSlipsSub: string;
  howItWorks: string;
  step1Title: string;
  step1Desc: string;
  step2Title: string;
  step2Desc: string;
  step3Title: string;
  step3Desc: string;

  // Common UI
  loading: string;
  save: string;
  cancel: string;
  back: string;
  next: string;
  retry: string;
}

const translations: Record<Language, Translations> = {
  hi: {
    // Common / Navbar
    home: 'होम',
    dashboard: 'हिसाब',
    voice: 'बोलें',
    studio: 'स्टूडियो',
    work: 'काम',
    evidence: 'दस्तावेज़',
    insights: 'रुझान',
    help: 'मदद',
    history: 'इतिहास',
    employers: 'मालिक',
    login: 'लॉग इन करें',
    logout: 'लॉग आउट',
    tagline: 'आपका काम · आपका हिसाब',
    languageLabel: 'भाषा',

    // Home Page
    heroBadge: 'रोज़ की मेहनत का साफ़ हिसाब',
    greetingReady: 'जी, आपका हिसाब तैयार है।',
    guestTitle: 'आपकी मेहनत। आपका पूरा हिसाब।',
    heroDescription: 'काम या मिला हुआ पैसा अपनी भाषा में बोलिए। रिकॉर्ड जाँचें, खुद पुष्टि करें, फिर आपका हिसाब सुरक्षित होगा।',
    recordVoiceBtn: 'आवाज़ से रिकॉर्ड करें',
    startBtn: 'शुरू करें',
    viewFullDashboardBtn: 'पूरा हिसाब देखें',
    speakToRecord: 'बोलकर बताइए',
    badgeConfirmFirst: 'आपकी पुष्टि के बाद ही सेव',
    badgeTimestamped: 'साफ़ और समय सहित रिकॉर्ड',
    earningsAndPayments: 'आपकी कमाई और भुगतान',
    summaryAtAGlance: 'एक नज़र में हिसाब',
    details: 'विस्तार',
    byEmployer: 'मालिक के हिसाब से',
    byEmployerSub: 'हर ठेकेदार का अलग बकाया देखें',
    wageSlips: 'आपकी मज़दूरी पर्ची',
    wageSlipsSub: 'पुष्टि किए रिकॉर्ड की PDF पाएँ',
    howItWorks: 'यह कैसे काम करता है?',
    step1Title: 'अपनी भाषा में बोलें',
    step1Desc: 'काम के दिन, दैनिक मज़दूरी, या मिला हुआ भुगतान हिंदी में बोलकर दर्ज करें।',
    step2Title: 'पहले खुद जाँचें',
    step2Desc: 'आवाज़ से निकली जानकारी कार्ड पर देखें। कुछ छूट गया हो तो सुधारें या मना करें।',
    step3Title: 'अपना हिसाब देखें',
    step3Desc: 'कुल कमाई, मिला पैसा और बकाया राशि कभी भी एक क्लिक में देखें।',

    // Common UI
    loading: 'लोड हो रहा है...',
    save: 'सहेजें',
    cancel: 'रद्द करें',
    back: 'वापस जाएँ',
    next: 'आगे बढ़ें',
    retry: 'फिर से कोशिश करें',
  },
  en: {
    // Common / Navbar
    home: 'Home',
    dashboard: 'Ledger',
    voice: 'Voice',
    studio: 'Studio',
    work: 'Work',
    evidence: 'Evidence',
    insights: 'Trends',
    help: 'Help',
    history: 'History',
    employers: 'Employers',
    login: 'Log In',
    logout: 'Log Out',
    tagline: 'Your Work · Your Records',
    languageLabel: 'Language',

    // Home Page
    heroBadge: 'Clear record of your daily hard work',
    greetingReady: ', your records are ready.',
    guestTitle: 'Your hard work. Your complete ledger.',
    heroDescription: 'Speak work details or received payments naturally. Verify records, confirm them yourself, and keep your finances safe.',
    recordVoiceBtn: 'Record with Voice',
    startBtn: 'Get Started',
    viewFullDashboardBtn: 'View Complete Ledger',
    speakToRecord: 'Speak to Record',
    badgeConfirmFirst: 'Saved only after your confirmation',
    badgeTimestamped: 'Clean, timestamped records',
    earningsAndPayments: 'Your earnings & payments',
    summaryAtAGlance: 'Summary at a glance',
    details: 'Details',
    byEmployer: 'By Employer',
    byEmployerSub: 'View pending balances per contractor',
    wageSlips: 'Wage Statements',
    wageSlipsSub: 'Download PDF of confirmed records',
    howItWorks: 'How it works',
    step1Title: 'Speak naturally',
    step1Desc: 'Log days worked, daily wage, or money received in Hindi or English.',
    step2Title: 'Review first',
    step2Desc: 'Review extracted info on the card. Correct details or reject if needed.',
    step3Title: 'Track your ledger',
    step3Desc: 'Check total earned, payments received, and pending balances anytime in one tap.',

    // Common UI
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
    back: 'Back',
    next: 'Next',
    retry: 'Retry',
  },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>('hi');

  useEffect(() => {
    try {
      const saved = localStorage.getItem('mazdoormitra_app_lang') as Language | null;
      if (saved === 'hi' || saved === 'en') {
        setLanguageState(saved);
        if (typeof document !== 'undefined') {
          document.documentElement.lang = saved;
        }
      }
    } catch {
      // ignore localStorage errors
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem('mazdoormitra_app_lang', lang);
      if (typeof document !== 'undefined') {
        document.documentElement.lang = lang;
      }
    } catch {
      // ignore localStorage errors
    }
  };

  const toggleLanguage = () => {
    const nextLang: Language = language === 'hi' ? 'en' : 'hi';
    setLanguage(nextLang);
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        toggleLanguage,
        t: translations[language],
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
