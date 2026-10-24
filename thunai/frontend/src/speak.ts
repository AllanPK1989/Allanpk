// Read-aloud with the phone's own text-to-speech (works offline, no cost).
import type { Lang } from "./i18n";

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function hasVoice(lang: Lang): boolean {
  if (!canSpeak()) return false;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return true; // voices load late on some phones; try anyway
  return voices.some((v) => v.lang.toLowerCase().startsWith(lang));
}

export function speak(text: string, lang: Lang) {
  if (!canSpeak() || !text.trim()) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === "ta" ? "ta-IN" : "en-IN";
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang));
  if (voice) u.voice = voice;
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if (canSpeak()) window.speechSynthesis.cancel();
}
