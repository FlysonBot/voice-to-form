// Mic recording -> 16 kHz mono WAV (base64), with automatic stop on silence.
// WAV because Gemini accepts it everywhere (Chrome's MediaRecorder gives webm/opus).

let stream = null;

export async function getMic() {
  if (stream && stream.getTracks().every((t) => t.readyState === "live")) return stream;
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  return stream;
}

export function releaseMic() {
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
}

/**
 * Start recording one spoken answer.
 * Returns { stop, cancel, result } where result resolves to
 *   { audio_b64, mime_type: "audio/wav", durationMs }  or  null if nothing was said / cancelled.
 */
export async function startRecording({
  maxMs = 20000,        // hard cap per answer
  silenceMs = 1600,     // stop after this much silence once they've spoken
  noSpeechMs = 9000,    // give up if they never start talking
  onLevel = () => {},   // 0..1 mic level for the UI
} = {}) {
  const s = await getMic();
  const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
  const recorder = new MediaRecorder(s, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);

  // --- simple voice-activity detection ---
  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(s);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  src.connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);
  const started = performance.now();
  let noiseFloor = 0.01, heardSpeech = false, lastLoud = started, cancelled = false;

  const rms = () => {
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) { const x = (v - 128) / 128; sum += x * x; }
    return Math.sqrt(sum / buf.length);
  };

  let stopResolve;
  const stopped = new Promise((r) => (stopResolve = r));
  recorder.onstop = () => stopResolve();

  const timer = setInterval(() => {
    const now = performance.now();
    const level = rms();
    onLevel(Math.min(1, level * 8));
    if (now - started < 300) { noiseFloor = Math.max(noiseFloor, level); return; } // calibrate
    const threshold = Math.max(0.02, noiseFloor * 2.5);
    if (level > threshold) { heardSpeech = true; lastLoud = now; }
    if ((heardSpeech && now - lastLoud > silenceMs) || now - started > maxMs || (!heardSpeech && now - started > noSpeechMs)) {
      stop();
    }
  }, 80);

  function stop() {
    clearInterval(timer);
    onLevel(0);
    if (recorder.state !== "inactive") recorder.stop();
  }
  function cancel() { cancelled = true; stop(); }

  recorder.start(250);

  const result = (async () => {
    await stopped;
    ctx.close();
    if (cancelled || !heardSpeech || chunks.length === 0) return null;
    const blob = new Blob(chunks, { type: recorder.mimeType });
    const wav = await toWav16k(await blob.arrayBuffer());
    return { audio_b64: arrayBufferToBase64(wav), mime_type: "audio/wav", durationMs: performance.now() - started };
  })();

  return { stop, cancel, result };
}

async function toWav16k(arrayBuffer) {
  const decodeCtx = new AudioContext();
  const decoded = await decodeCtx.decodeAudioData(arrayBuffer);
  decodeCtx.close();
  const rate = 16000;
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate);
  const node = offline.createBufferSource();
  node.buffer = decoded;
  node.connect(offline.destination);
  node.start();
  const rendered = await offline.startRendering();
  return encodeWav(rendered.getChannelData(0), rate);
}

function encodeWav(samples, rate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}
