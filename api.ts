const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface PreLearnResponse {
  knowledge_gaps: string[];
  likely_misconceptions: string[];
  learning_plan: string[];
  opening_message: string;
}

export interface FeynmanResponse {
  scores: {
    accuracy: number;
    clarity: number;
    depth: number;
    transfer: number;
  };
  overall: number;
  strengths: string;
  gaps: string;
  next_step: string;
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: Record<string, string>;
  correct: string;
  explanation: string;
  difficulty: string;
}

export interface QuizResponse {
  questions: QuizQuestion[];
}

export interface QuizSubmitResponse {
  quiz_score: number;
  correct_count: number;
  total: number;
  results: {
    question_id: number;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    explanation: string;
  }[];
  calibration: {
    pre_confidence: number;
    actual_score: number;
    error: number;
    label: "well_calibrated" | "overconfident" | "underconfident";
    message: string;
  };
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  startSession: (body: {
    topic: string;
    mode: string;
    confidence: number;
    prior_knowledge: string;
  }) => post<PreLearnResponse>("/session/start", body),

  /** Returns a ReadableStream of SSE tokens. Caller handles parsing. */
  chat: (body: {
    topic: string;
    mode: string;
    prior_knowledge: string;
    confidence: number;
    history: ChatMessage[];
    user_message: string;
  }) =>
    fetch(`${BASE}/session/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  evaluateFeynman: (body: { topic: string; explanation: string }) =>
    post<FeynmanResponse>("/session/feynman", body),

  generateQuiz: (body: { topic: string; history: ChatMessage[] }) =>
    post<QuizResponse>("/session/quiz/generate", body),

  submitQuiz: (body: {
    topic: string;
    questions: QuizQuestion[];
    answers: string[];
    pre_confidence: number;
  }) => post<QuizSubmitResponse>("/session/quiz/submit", body),
};