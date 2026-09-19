export const en = {
  appName: "InterviewPilot AI",
  tagline: "Your real-time AI copilot for interviews, meetings and technical conversations.",
  heroTitle: "Think clearly. Answer confidently. In real time.",
  heroSub:
    "InterviewPilot AI listens, understands your conversation, and helps you prepare better answers using your resume, job description, and knowledge base.",
  startFree: "Start Free",
  tryMock: "Try Mock Interview",
  demoMode: "DEMO MODE",
  listening: "Listening...",
  transcribing: "Transcribing...",
  understanding: "Understanding...",
  generating: "Generating...",
  ready: "Ready",
  legalNotice:
    "Users are responsible for complying with interview and meeting rules. Some interviews prohibit AI assistance. Obtain required consent before recording. Local laws and platform policies may apply.",
};

export type Messages = typeof en;

const catalogs: Record<string, Messages> = { en };

export function t(lang: string): Messages {
  return catalogs[lang] || en;
}
