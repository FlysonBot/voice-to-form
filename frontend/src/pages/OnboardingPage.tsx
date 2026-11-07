import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { onboardingTurn } from '../api/client';
import ChatInput from '../components/chat/ChatInput';
import ChatWindow from '../components/chat/ChatWindow';
import ProfileSidebar from '../components/chat/ProfileSidebar';
import ProgressSteps from '../components/layout/ProgressSteps';
import DocScan from '../components/voice/DocScan';
import VoiceToggle from '../components/voice/VoiceToggle';
import { useListener } from '../hooks/useListener';
import { useReplyPlayer } from '../hooks/useReplyPlayer';
import { useLanguage, useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

/** Step 1, "tell us once": a spoken conversation that fills the profile (POST /onboarding/turn). */
export default function OnboardingPage() {
  const t = useT();
  const navigate = useNavigate();
  const { speechLocale: bcp47 } = useLanguage();
  const { session, messages, onboardingDone, voiceOn, setVoiceOn, addMessage, mergeProfile, setOnboardingDone } = useAppStore();
  const [thinking, setThinking] = useState(false);
  const [handsFree, setHandsFree] = useState(false);
  const started = useRef(false);
  const leaveTimer = useRef(0);
  useEffect(() => () => window.clearTimeout(leaveTimer.current), []);

  const player = useReplyPlayer();
  const listener = useListener(bcp47, (text, audio) => latest.current.onVoice(text, audio));

  // Callbacks that fire later (after speech ends) need the latest values
  const latest = useRef({ handsFree, listener, bcp47, onVoice: (_t: string, _a: Blob | null) => {} });
  useEffect(() => {
    latest.current = {
      handsFree,
      listener,
      bcp47,
      onVoice: (text, audio) => {
        setHandsFree(true);
        send(text, audio);
      },
    };
  });

  async function turn(audio: Blob | null, text: string | null) {
    setThinking(true);
    try {
      const s = useAppStore.getState(); // fresh state, including the user's new message
      const res = await onboardingTurn(s.session, s.messages, audio, text);
      // No browser transcript (e.g. Firefox): show what Gemini heard
      if (!text && res.transcript) addMessage({ role: 'user', text: res.transcript });
      mergeProfile(res.profile_updates ?? res.profile ?? {});
      const id = addMessage({ role: 'assistant', text: res.reply });
      if (res.done) setOnboardingDone(true);
      setThinking(false);
      player.play(id, res.reply, latest.current.bcp47, !useAppStore.getState().voiceOn, () => {
        if (res.done) leaveTimer.current = window.setTimeout(() => navigate('/choose'), 1200);
        else if (latest.current.handsFree) latest.current.listener.start();
      }, res);
    } catch {
      addMessage({ role: 'assistant', text: t('chatError') });
      setThinking(false);
    }
  }

  // Start with the assistant's greeting
  useEffect(() => {
    if (!started.current && messages.length === 0) {
      started.current = true;
      turn(null, null);
    }
    // Run once on mount only
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function send(text: string, audio: Blob | null = null) {
    player.stop();
    if (text) addMessage({ role: 'user', text });
    turn(audio, text || null);
  }

  function handleMic() {
    if (listener.listening) return listener.stop();
    player.stop(); // let the user talk over the assistant
    listener.start();
  }

  function leave() {
    listener.abort();
    player.stop();
    setOnboardingDone(true);
    navigate('/choose');
  }

  const notice = !listener.supported
    ? t('micUnsupported')
    : listener.error === 'not-allowed'
      ? t('micBlocked')
      : !player.speaker.hasVoice(bcp47)
        ? t('noVoice')
        : null;

  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <ProgressSteps current={0} />
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <section className="flex h-[70vh] flex-col overflow-hidden rounded-2xl bg-stone-100 ring-1 ring-stone-200">
          <div className="flex items-center gap-2 border-b border-stone-200 bg-white px-3 py-2">
            <VoiceToggle on={voiceOn} onToggle={() => { if (voiceOn) player.finishNow(); setVoiceOn(!voiceOn); }} />
            {handsFree && !onboardingDone && (
              <span className="rounded-full bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 ring-1 ring-red-200">{t('handsFree')}</span>
            )}
            {(onboardingDone || messages.some((m) => m.role === 'user') || Object.keys(session.profile).length > 0) && (
              <button onClick={leave} className="ms-auto rounded-full px-3 py-1.5 text-sm font-medium text-teal-800 hover:bg-teal-50">
                {t('doneTalking')} <span aria-hidden className="inline-block rtl:-scale-x-100">→</span>
              </button>
            )}
          </div>
          {notice && <p className="bg-amber-50 px-4 py-2 text-sm text-amber-900">{notice}</p>}

          <ChatWindow
            messages={messages}
            typing={thinking}
            anim={player.anim}
            listening={listener.listening}
            liveUserText={listener.interim}
            onReplay={(text) => player.speaker.speak(text, bcp47)}
          />

          {onboardingDone ? (
            <div className="border-t border-stone-200 bg-white p-3">
              <button onClick={() => navigate('/choose')} className="min-h-14 w-full rounded-xl bg-teal-700 text-lg font-semibold text-white hover:bg-teal-800">
                {t('continue')} →
              </button>
            </div>
          ) : (
            <ChatInput
              onSend={(text) => { setHandsFree(false); send(text); }}
              disabled={thinking}
              micAvailable={listener.supported}
              listening={listener.listening}
              onMic={handleMic}
            />
          )}
        </section>
        <div className="space-y-4">
          <DocScan />
          <ProfileSidebar profile={session.profile} />
        </div>
      </div>
    </main>
  );
}
