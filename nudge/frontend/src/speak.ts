// Read-aloud using only voices built into your device.
// Some browsers also offer online voices (Chrome's "Google …" voices send the text to Google);
// those are skipped, so what's read out never leaves your phone or laptop.

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

if (canSpeak()) window.speechSynthesis.getVoices(); // start loading the voice list early

function waitForVoices(ms = 1500): Promise<SpeechSynthesisVoice[]> {
  const now = window.speechSynthesis.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, ms);
  });
}

function pickLocalVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  const local = voices.filter((v) => v.localService);
  return (
    local.find((v) => v.lang === "en-IN") ||
    local.find((v) => v.lang.startsWith("en-GB")) ||
    local.find((v) => v.lang.startsWith("en"))
  );
}

/** Resolves false (and calls onEnd) when the device has no built-in English voice. */
export async function speak(text: string, onEnd?: () => void): Promise<boolean> {
  if (!canSpeak()) {
    onEnd?.();
    return false;
  }
  window.speechSynthesis.cancel();
  const voice = pickLocalVoice(await waitForVoices());
  if (!voice) {
    onEnd?.();
    return false;
  }
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = 1;
  u.onend = () => onEnd?.();
  u.onerror = () => onEnd?.();
  window.speechSynthesis.speak(u);
  return true;
}

export function stopSpeaking(): void {
  if (canSpeak()) window.speechSynthesis.cancel();
}
