// Standalone test page for the voice flow: onboarding -> gap questions -> recap.
// Use it while the real screens are being built:  <VoiceDemo />  in App.jsx, with VITE_MOCK=true to run without a key.
import { useState } from "react";
import GapQuestions from "./GapQuestions";
import VoiceOnboarding from "./VoiceOnboarding";
import VoiceRecap from "./VoiceRecap";
import "./voice.css";

export default function VoiceDemo() {
  const [language, setLanguage] = useState("es");
  const [step, setStep] = useState("lang");
  const [profile, setProfile] = useState({});

  return (
    <div>
      {step === "lang" && (
        <div className="voice-screen">
          {[["auto", "🌐 Auto"], ["es", "Español"], ["en", "English"], ["zh", "中文"], ["vi", "Tiếng Việt"]].map(([code, name]) => (
            <button key={code} className="big-btn" onClick={() => { setLanguage(code); setStep("onboarding"); }}>{name}</button>
          ))}
        </div>
      )}
      {step === "onboarding" && (
        <VoiceOnboarding language={language} profile={profile} onProfile={setProfile} onLanguage={setLanguage} onDone={(p) => { setProfile(p); setStep("gaps"); }} />
      )}
      {step === "gaps" && (
        <GapQuestions language={language} profile={profile} formName="SDG&E CARE"
          missingFields={[{ field: "sdge_account_number", description: "SDG&E account number from the energy bill" }]}
          onProfile={setProfile} onDone={(p) => { setProfile(p); setStep("recap"); }} />
      )}
      {step === "recap" && (
        <VoiceRecap language={language} profile={profile} formName="SDG&E CARE" blankFields={[]}
          onProfile={setProfile} onConfirm={(p) => { setProfile(p); setStep("done"); }} />
      )}
      {step === "done" && <pre className="voice-screen" style={{ fontSize: 12 }}>{JSON.stringify(profile, null, 2)}</pre>}
    </div>
  );
}
