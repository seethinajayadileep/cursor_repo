export type SessionType =
  | "job_interview"
  | "technical_interview"
  | "coding_interview"
  | "hr_interview"
  | "sales_call"
  | "client_meeting"
  | "mock_interview"
  | "custom";

export type AiMode = "interview" | "coding" | "hr" | "sales" | "meeting" | "study";
export type ResponseMode = "fast" | "balanced" | "detailed";
export type ProcessingMode = "demo" | "local" | "cloud";
export type DocumentCategory =
  | "resume"
  | "job_description"
  | "company_information"
  | "project_information"
  | "study_material"
  | "sales_material"
  | "custom";

export type QuestionCategory =
  | "hr"
  | "behavioral"
  | "technical"
  | "coding"
  | "system_design"
  | "situational"
  | "follow_up"
  | "clarification"
  | "general";

export type SpeakerRole = "interviewer" | "candidate" | "participant" | "system" | "unknown";

export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  plan: "free" | "pro" | "premium";
}

export interface ResumeProfile {
  name?: string;
  email?: string;
  phone?: string;
  summary?: string;
  skills: string[];
  technologies: string[];
  languages: string[];
  education: Array<{
    institution: string;
    degree?: string;
    field?: string;
    year?: string;
  }>;
  experience: Array<{
    company: string;
    title: string;
    startDate?: string;
    endDate?: string;
    highlights: string[];
  }>;
  projects: Array<{
    name: string;
    description: string;
    technologies: string[];
  }>;
  certifications: string[];
  achievements: string[];
  internships: Array<{
    company: string;
    title: string;
    highlights: string[];
  }>;
}

export interface TranscriptSegment {
  id: string;
  speaker: SpeakerRole;
  text: string;
  timestamp: string;
  startMs?: number;
  endMs?: number;
  confidence?: number;
  isPartial?: boolean;
  isQuestion?: boolean;
  questionCategory?: QuestionCategory;
}

export interface DetectedQuestion {
  id: string;
  text: string;
  category: QuestionCategory;
  confidence: number;
  timestamp: string;
  segmentId?: string;
}

export interface GeneratedAnswer {
  id: string;
  questionId: string;
  mode: ResponseMode;
  concise?: string;
  detailed?: string;
  talkingPoints?: string[];
  star?: { situation: string; task: string; action: string; result: string };
  code?: {
    language: string;
    approach: string;
    algorithm: string;
    code: string;
    complexity: string;
    edgeCases: string[];
    explanation: string;
  };
  followUps?: string[];
  streaming?: boolean;
  createdAt: string;
}

export interface ActionItem {
  id: string;
  task: string;
  owner?: string;
  deadline?: string;
  status: "open" | "in_progress" | "done";
}

export interface SessionSummary {
  summary: string;
  keyPoints: string[];
  decisions: string[];
  questions: string[];
  actionItems: ActionItem[];
  importantDates: string[];
  peopleMentioned: string[];
  followUpTasks: string[];
  insights?: string[];
}

export interface InterviewSession {
  id: string;
  userId: string;
  title: string;
  sessionType: SessionType;
  jobRole?: string;
  company?: string;
  jobDescription?: string;
  language: string;
  aiMode: AiMode;
  responseMode: ResponseMode;
  instructions?: string;
  status: "draft" | "active" | "paused" | "ended";
  processingMode: ProcessingMode;
  createdAt: string;
  startedAt?: string;
  endedAt?: string;
  durationSec?: number;
  transcript: TranscriptSegment[];
  questions: DetectedQuestion[];
  answers: GeneratedAnswer[];
  documentIds: string[];
  resumeId?: string;
  summary?: SessionSummary;
}

export interface DocumentMeta {
  id: string;
  userId: string;
  name: string;
  category: DocumentCategory;
  mimeType: string;
  sizeBytes: number;
  createdAt: string;
  textPreview?: string;
  chunkCount?: number;
}

export interface DocumentChunk {
  id: string;
  documentId: string;
  index: number;
  text: string;
  embedding?: number[];
}

export interface AppSettings {
  theme: "light" | "dark" | "system";
  language: string;
  aiProvider: string;
  sttProvider: string;
  processingMode: ProcessingMode;
  responseMode: ResponseMode;
  aiMode: AiMode;
  alwaysOnTop: boolean;
  compactMode: boolean;
  analyticsOptIn: boolean;
  shortcuts: Record<string, string>;
}

export interface UsageStats {
  sttSeconds: number;
  llmTokens: number;
  documentProcessing: number;
  aiRequests: number;
  storageBytes: number;
}

export interface BillingPlan {
  id: "free" | "pro" | "premium";
  name: string;
  priceMonthly: number;
  features: string[];
  limits: {
    sessionsPerMonth: number;
    documents: number;
    sttMinutes: number;
  };
}

export const SUPPORTED_LANGUAGES = [
  { code: "en", name: "English" },
  { code: "hi", name: "Hindi" },
  { code: "te", name: "Telugu" },
] as const;

export const SESSION_TYPES: Array<{ id: SessionType; label: string }> = [
  { id: "job_interview", label: "Job Interview" },
  { id: "technical_interview", label: "Technical Interview" },
  { id: "coding_interview", label: "Coding Interview" },
  { id: "hr_interview", label: "HR Interview" },
  { id: "sales_call", label: "Sales Call" },
  { id: "client_meeting", label: "Client Meeting" },
  { id: "mock_interview", label: "Mock Interview" },
  { id: "custom", label: "Custom" },
];

export const BILLING_PLANS: BillingPlan[] = [
  {
    id: "free",
    name: "Free",
    priceMonthly: 0,
    features: ["Demo mode", "3 sessions / month", "2 documents", "Basic transcription"],
    limits: { sessionsPerMonth: 3, documents: 2, sttMinutes: 30 },
  },
  {
    id: "pro",
    name: "Pro",
    priceMonthly: 29,
    features: ["Unlimited sessions", "Resume intelligence", "Coding assistant", "Mock interviews"],
    limits: { sessionsPerMonth: 100, documents: 50, sttMinutes: 600 },
  },
  {
    id: "premium",
    name: "Premium",
    priceMonthly: 79,
    features: ["Everything in Pro", "Priority AI", "Meeting notes export", "Team-ready architecture"],
    limits: { sessionsPerMonth: 1000, documents: 500, sttMinutes: 5000 },
  },
];
