import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Header from './components/layout/Header';
import { isKnownLang, useLanguage, useT } from './i18n/strings';
import { useUiTranslation } from './i18n/useUiTranslation';
import ChoosePage from './pages/ChoosePage';
import DonePage from './pages/DonePage';
import GapsPage from './pages/GapsPage';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import ProgramsPage from './pages/ProgramsPage';
import ReviewPage from './pages/ReviewPage';
import SignPage from './pages/SignPage';

export default function App() {
  const { language, rtl, speechLocale } = useLanguage();
  const t = useT();
  const translating = useUiTranslation();

  // Flip the whole layout for right-to-left languages like Arabic
  useEffect(() => {
    document.documentElement.lang = isKnownLang(language) ? language : (speechLocale ?? '');
    document.documentElement.dir = rtl ? 'rtl' : 'ltr';
  }, [language, rtl, speechLocale]);

  return (
    <div className="min-h-screen">
      <Header />
      {translating && (
        <p role="status" className="bg-teal-50 px-4 py-2 text-center text-sm text-teal-900">{t('translating')}</p>
      )}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/choose" element={<ChoosePage />} />
        <Route path="/programs" element={<ProgramsPage />} />
        <Route path="/form/:formId/questions" element={<GapsPage />} />
        <Route path="/form/:formId/review" element={<ReviewPage />} />
        <Route path="/form/:formId/sign" element={<SignPage />} />
        <Route path="/form/:formId/done" element={<DonePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
