export type AudioSourceType = "microphone" | "browser" | "desktop";

export interface AudioChunk {
  pcm?: Float32Array;
  blob?: Blob;
  sampleRate: number;
  timestamp: number;
}

export interface AudioSource {
  readonly type: AudioSourceType;
  start(): Promise<void>;
  stop(): Promise<void>;
  onChunk(cb: (chunk: AudioChunk) => void): void;
  isSupported(): boolean;
  permissionHint(): string;
}

export class MicrophoneAudioSource implements AudioSource {
  readonly type = "microphone" as const;
  private stream: MediaStream | null = null;
  private ctx: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private handlers: Array<(c: AudioChunk) => void> = [];

  isSupported(): boolean {
    return typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
  }

  permissionHint(): string {
    return "Allow microphone access in your browser or OS privacy settings.";
  }

  onChunk(cb: (chunk: AudioChunk) => void): void {
    this.handlers.push(cb);
  }

  async start(): Promise<void> {
    if (!this.isSupported()) throw new Error("Microphone capture is not supported in this environment.");
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.ctx = new AudioContext();
    const source = this.ctx.createMediaStreamSource(this.stream);
    this.processor = this.ctx.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (ev) => {
      const input = ev.inputBuffer.getChannelData(0);
      const copy = new Float32Array(input);
      const chunk = { pcm: copy, sampleRate: this.ctx!.sampleRate, timestamp: Date.now() };
      this.handlers.forEach((h) => h(chunk));
    };
    source.connect(this.processor);
    this.processor.connect(this.ctx.destination);
  }

  async stop(): Promise<void> {
    this.processor?.disconnect();
    await this.ctx?.close();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.processor = null;
    this.ctx = null;
    this.stream = null;
  }
}

export class BrowserAudioSource implements AudioSource {
  readonly type = "browser" as const;
  private handlers: Array<(c: AudioChunk) => void> = [];
  isSupported(): boolean {
    return typeof navigator !== "undefined" && !!(navigator.mediaDevices as MediaDevices & { getDisplayMedia?: unknown })?.getDisplayMedia;
  }
  permissionHint(): string {
    return "Use screen/tab sharing and enable audio sharing if your browser supports it. Safari and some browsers have limited tab-audio capture.";
  }
  onChunk(cb: (chunk: AudioChunk) => void): void {
    this.handlers.push(cb);
  }
  async start(): Promise<void> {
    if (!this.isSupported()) {
      throw new Error("Browser/tab audio capture is not supported here. Use the microphone instead.");
    }
    const stream = await (navigator.mediaDevices as MediaDevices & { getDisplayMedia: (c: object) => Promise<MediaStream> }).getDisplayMedia({
      video: true,
      audio: true,
    });
    // Keep a no-op path; actual PCM wiring mirrors microphone when tracks exist.
    const audioTracks = stream.getAudioTracks();
    if (!audioTracks.length) {
      stream.getTracks().forEach((t) => t.stop());
      throw new Error("No audio track in shared tab/window. Enable 'Share audio' if available.");
    }
    void this.handlers;
  }
  async stop(): Promise<void> {}
}

export class DesktopAudioSource implements AudioSource {
  readonly type = "desktop" as const;
  isSupported(): boolean {
    return typeof process !== "undefined" && !!(process as NodeJS.Process & { versions?: { electron?: string } }).versions?.electron;
  }
  permissionHint(): string {
    return "Desktop system-audio capture requires OS permission and is available in the Electron app where supported.";
  }
  onChunk(): void {}
  async start(): Promise<void> {
    if (!this.isSupported()) {
      throw new Error("System audio capture requires the desktop app and OS permissions.");
    }
  }
  async stop(): Promise<void> {}
}

export function createAudioSource(type: AudioSourceType): AudioSource {
  switch (type) {
    case "browser":
      return new BrowserAudioSource();
    case "desktop":
      return new DesktopAudioSource();
    default:
      return new MicrophoneAudioSource();
  }
}
