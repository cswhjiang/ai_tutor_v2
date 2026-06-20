export type SessionCreateResponse = {
  user_id: string;
  session_id: string;
  message: string;
};

export type StepEvent = {
  type: "step";
  content: string;
};

export type ErrorEvent = {
  type: "error";
  content: string;
};

export type FinalContent = {
  text?: string | null;
  final_output_text?: string | null;
  image?: string[];
  filenames?: string[];
};

export type FinalEvent = {
  type: "final";
  content: FinalContent;
};

export type AgentEvent = StepEvent | ErrorEvent | FinalEvent;

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  variant?: "step" | "error" | "final";
};

