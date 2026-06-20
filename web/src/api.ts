import type { AgentEvent, SessionCreateResponse } from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:9501";

type SendChatOptions = {
  message: string;
  sessionId: string;
  userId: string;
  username: string;
  images: File[];
  documents: File[];
  onEvent: (event: AgentEvent) => void;
};

export async function createSession(username: string): Promise<SessionCreateResponse> {
  const formData = new FormData();
  formData.set("username", username);

  const response = await fetch(`${API_BASE_URL}/session/create`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Session create failed: ${response.status}`);
  }

  return response.json() as Promise<SessionCreateResponse>;
}

export async function sendChatMessage(options: SendChatOptions): Promise<void> {
  const formData = new FormData();
  formData.set("message", options.message);
  formData.set("session_id", options.sessionId);
  formData.set("user_id", options.userId);
  formData.set("username", options.username);

  for (const image of options.images) {
    formData.append("images", image);
  }
  for (const document of options.documents) {
    formData.append("documents", document);
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Chat response body is empty.");
  }

  await readServerSentEvents(response.body, options.onEvent);
}

async function readServerSentEvents(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: AgentEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      parseEventBlock(rawEvent, onEvent);
      boundary = buffer.indexOf("\n\n");
    }
  }

  if (buffer.trim()) {
    parseEventBlock(buffer, onEvent);
  }
}

function parseEventBlock(rawEvent: string, onEvent: (event: AgentEvent) => void): void {
  const dataLines = rawEvent
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trim());

  if (!dataLines.length) {
    return;
  }

  const payload = dataLines.join("\n");
  if (!payload) {
    return;
  }

  try {
    onEvent(JSON.parse(payload) as AgentEvent);
  } catch (error) {
    console.error("Failed to parse SSE payload", error, payload);
  }
}

