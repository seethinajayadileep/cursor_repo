import { uid, nowIso, type TranscriptSegment } from "@interviewpilot/shared";

export interface SpeechToTextProvider {
  readonly name: string;
  start(language: string): Promise<void>;
  stop(): Promise<void>;
  onPartial(cb: (text: string) => void): void;
  onFinal(cb: (segment: TranscriptSegment) => void): void;
}

/** Minimal Web Speech API surface for typed browser usage. */
interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
}

interface BrowserSpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string; confidence: number } }>;
}

type SpeechRecognitionCtor = new () => BrowserSpeechRecognition;

const DEMO_SCRIPT = [
  { speaker: "interviewer" as const, text: "Tell me about yourself." },
  { speaker: "candidate" as const, text: "I am currently pursuing experience as a data analyst with SQL and Python." },
  { speaker: "interviewer" as const, text: "What is normalization in SQL?" },
  { speaker: "candidate" as const, text: "Normalization organizes data to reduce redundancy across tables." },
  { speaker: "interviewer" as const, text: "Write a Python function to reverse a linked list." },
  { speaker: "interviewer" as const, text: "Tell me about a conflict you handled." },
  { speaker: "interviewer" as const, text: "How would you design a metrics dashboard for executives?" },
];

export class DemoSpeechProvider implements SpeechToTextProvider {
  readonly name: string = "demo";
  private timer?: ReturnType<typeof setInterval>;
  private idx = 0;
  private partialHandlers: Array<(t: string) => void> = [];
  private finalHandlers: Array<(s: TranscriptSegment) => void> = [];

  onPartial(cb: (text: string) => void): void {
    this.partialHandlers.push(cb);
  }
  onFinal(cb: (segment: TranscriptSegment) => void): void {
    this.finalHandlers.push(cb);
  }

  async start(_language?: string): Promise<void> {
    this.idx = 0;
    this.timer = setInterval(() => {
      const item = DEMO_SCRIPT[this.idx % DEMO_SCRIPT.length];
      this.idx += 1;
      const words = item.text.split(" ");
      let partial = "";
      let i = 0;
      const pushPartial = () => {
        if (i >= words.length) {
          const segment: TranscriptSegment = {
            id: uid("seg"),
            speaker: item.speaker,
            text: item.text,
            timestamp: nowIso(),
            confidence: 0.92,
            isPartial: false,
            isQuestion: item.speaker === "interviewer" && /\?$|tell me|what is|write |how would/i.test(item.text),
          };
          this.finalHandlers.forEach((h) => h(segment));
          return;
        }
        partial = partial ? `${partial} ${words[i]}` : words[i];
        i += 1;
        this.partialHandlers.forEach((h) => h(partial));
        setTimeout(pushPartial, 120);
      };
      pushPartial();
    }, 6500);
  }

  async stop(): Promise<void> {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }
}

export class BrowserSpeechProvider implements SpeechToTextProvider {
  readonly name: string = "browser";
  private recognition: BrowserSpeechRecognition | null = null;
  private partialHandlers: Array<(t: string) => void> = [];
  private finalHandlers: Array<(s: TranscriptSegment) => void> = [];

  onPartial(cb: (text: string) => void): void {
    this.partialHandlers.push(cb);
  }
  onFinal(cb: (segment: TranscriptSegment) => void): void {
    this.finalHandlers.push(cb);
  }

  async start(language: string): Promise<void> {
    const g = globalThis as unknown as {
      SpeechRecognition?: SpeechRecognitionCtor;
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    };
    const SR = g.SpeechRecognition || g.webkitSpeechRecognition;
    if (!SR) throw new Error("Web Speech API is unavailable. Use DEMO MODE or a cloud STT provider.");
    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = language === "hi" ? "hi-IN" : language === "te" ? "te-IN" : "en-US";
    this.recognition.onresult = (event: BrowserSpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const text = res[0].transcript;
        if (res.isFinal) {
          this.finalHandlers.forEach((h) =>
            h({
              id: uid("seg"),
              speaker: "unknown",
              text: text.trim(),
              timestamp: nowIso(),
              confidence: res[0].confidence,
              isPartial: false,
            })
          );
        } else {
          interim += text;
        }
      }
      if (interim) this.partialHandlers.forEach((h) => h(interim));
    };
    this.recognition.onerror = () => {
      try {
        this.recognition?.start();
      } catch {
        /* ignore */
      }
    };
    this.recognition.start();
  }

  async stop(): Promise<void> {
    this.recognition?.stop();
    this.recognition = null;
  }
}

export class LocalSpeechProvider extends DemoSpeechProvider {
  readonly name: string = "local";
}

export class CloudSpeechProvider extends DemoSpeechProvider {
  readonly name: string = "cloud";
  constructor(private apiKey?: string) {
    super();
  }
}

export function createSpeechProvider(name: string, apiKey?: string): SpeechToTextProvider {
  switch (name) {
    case "browser":
      return new BrowserSpeechProvider();
    case "local":
      return new LocalSpeechProvider();
    case "cloud":
      return new CloudSpeechProvider(apiKey);
    default:
      return new DemoSpeechProvider();
  }
}
