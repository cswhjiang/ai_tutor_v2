import "./styles.css";
import { API_BASE_URL, createSession, sendChatMessage } from "./api";
import type { AgentEvent, ChatMessage, FinalContent, VideoPreviewContent } from "./types";

const SAMPLE_PROMPT =
  "What is the percentage increase in the area of a triangle if the height of the triangle is decreased by 10% and its base is increased by 20%? 请做一个视频讲解。";

type AppState = {
  userId: string | null;
  sessionId: string | null;
  username: string;
  busy: boolean;
  messages: ChatMessage[];
  activeAssistantMessageId: string | null;
  assistantStreamedThisTurn: boolean;
  statusSteps: string[];
  statusExpanded: boolean;
  videos: string[];
  previewSegments: VideoPreviewContent[];
  previewFinalUrl: string | null;
  previewFinalLabel: string;
  previewCurrentIndex: number;
  previewSoundEnabled: boolean;
  previewAutoplayBlocked: boolean;
  filenames: string[];
  finalText: string;
};

const state: AppState = {
  userId: null,
  sessionId: null,
  username: "web_user",
  busy: false,
  messages: [],
  activeAssistantMessageId: null,
  assistantStreamedThisTurn: false,
  statusSteps: [],
  statusExpanded: false,
  videos: [],
  previewSegments: [],
  previewFinalUrl: null,
  previewFinalLabel: "",
  previewCurrentIndex: 0,
  previewSoundEnabled: false,
  previewAutoplayBlocked: false,
  filenames: [],
  finalText: "",
};

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("Missing #app root.");
}

app.innerHTML = `
  <main class="shell">
    <header class="topbar">
      <div class="brand-mark">AI</div>
      <div class="brand-copy">
        <h1>AI Tutor</h1>
        <p>数学讲解、步骤推理和视频结果都会显示在这里。</p>
      </div>
      <div class="connection" id="connectionStatus">未连接</div>
    </header>

    <section class="messages" id="messages" aria-live="polite"></section>

    <section class="live-preview" id="livePreview" hidden>
      <div class="live-preview-header">
        <div>
          <h2 id="livePreviewTitle">正在生成视频</h2>
          <p id="livePreviewMeta">等待第一个可播放片段</p>
        </div>
        <button id="previewSoundButton" class="preview-sound-button" type="button">
          开启声音预览
        </button>
      </div>
      <video id="livePreviewVideo" controls playsinline></video>
    </section>

    <form class="composer" id="chatForm">
      <textarea
        id="promptInput"
        name="message"
        rows="3"
        placeholder="给 AI Tutor 发送消息"
        required
      ></textarea>
      <div class="composer-row">
        <label class="file-button">
          图片
          <input id="imageInput" type="file" accept="image/*" multiple />
        </label>
        <label class="file-button">
          文档
          <input id="documentInput" type="file" multiple />
        </label>
        <button id="sampleButton" class="secondary-button" type="button">填入样例</button>
        <button id="sendButton" class="send-button" type="submit">发送</button>
      </div>
    </form>
  </main>
`;

const messagesEl = mustGet<HTMLDivElement>("messages");
const livePreviewEl = mustGet<HTMLElement>("livePreview");
const livePreviewTitleEl = mustGet<HTMLHeadingElement>("livePreviewTitle");
const livePreviewMetaEl = mustGet<HTMLParagraphElement>("livePreviewMeta");
const livePreviewVideoEl = mustGet<HTMLVideoElement>("livePreviewVideo");
const previewSoundButton = mustGet<HTMLButtonElement>("previewSoundButton");
const connectionStatusEl = mustGet<HTMLDivElement>("connectionStatus");
const chatForm = mustGet<HTMLFormElement>("chatForm");
const promptInput = mustGet<HTMLTextAreaElement>("promptInput");
const imageInput = mustGet<HTMLInputElement>("imageInput");
const documentInput = mustGet<HTMLInputElement>("documentInput");
const sendButton = mustGet<HTMLButtonElement>("sendButton");
const sampleButton = mustGet<HTMLButtonElement>("sampleButton");

sampleButton.addEventListener("click", () => {
  promptInput.value = SAMPLE_PROMPT;
  promptInput.focus();
});

livePreviewVideoEl.addEventListener("ended", () => {
  if (state.previewFinalUrl) {
    return;
  }
  if (state.previewCurrentIndex + 1 >= state.previewSegments.length) {
    return;
  }
  state.previewCurrentIndex += 1;
  updateLivePreview();
});

previewSoundButton.addEventListener("click", () => {
  state.previewSoundEnabled = true;
  state.previewAutoplayBlocked = false;
  livePreviewVideoEl.muted = false;
  requestPreviewPlay();
  updateLivePreview();
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void handleSubmit();
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }

  event.preventDefault();
  void handleSubmit();
});

void ensureSession();
render();

async function ensureSession(): Promise<void> {
  if (state.sessionId && state.userId) {
    return;
  }

  setBusy(true);
  setConnectionStatus("连接中");
  try {
    const session = await createSession(state.username);
    state.userId = session.user_id;
    state.sessionId = session.session_id;
    setConnectionStatus("已连接");
  } catch (error) {
    setConnectionStatus("连接失败");
    addMessage("system", normalizeError(error), "error");
  } finally {
    setBusy(false);
    render();
  }
}

async function handleSubmit(): Promise<void> {
  const message = promptInput.value.trim();
  if (!message || state.busy) {
    return;
  }

  await ensureSession();
  if (!state.sessionId || !state.userId) {
    return;
  }

  const images = Array.from(imageInput.files ?? []);
  const documents = Array.from(documentInput.files ?? []);

  state.statusSteps = [];
  state.statusExpanded = false;
  state.activeAssistantMessageId = null;
  state.assistantStreamedThisTurn = false;
  state.videos = [];
  state.previewSegments = [];
  state.previewFinalUrl = null;
  state.previewFinalLabel = "";
  state.previewCurrentIndex = 0;
  state.previewAutoplayBlocked = false;
  state.filenames = [];
  state.finalText = "";
  updateLivePreview();
  addMessage("user", message);
  promptInput.value = "";
  imageInput.value = "";
  documentInput.value = "";
  setBusy(true);
  render();

  try {
    await sendChatMessage({
      message,
      sessionId: state.sessionId,
      userId: state.userId,
      username: state.username,
      images,
      documents,
      onEvent: handleAgentEvent,
    });
  } catch (error) {
    addMessage("system", normalizeError(error), "error");
  } finally {
    setBusy(false);
    render();
  }
}

function handleAgentEvent(event: AgentEvent): void {
  if (event.type === "step") {
    addStatusStep(event.content);
    return;
  }

  if (event.type === "error") {
    addMessage("system", event.content, "error");
    finalizeActiveAssistantMessage();
    return;
  }

  if (event.type === "assistant_delta") {
    appendAssistantDelta(event.content);
    return;
  }

  if (event.type === "assistant_message") {
    mergeAssistantMessage(event.content);
    return;
  }

  if (event.type === "video_preview") {
    handleVideoPreview(event.content);
    return;
  }

  handleFinalContent(event.content);
}

function handleFinalContent(content: FinalContent): void {
  const finalSummary = content.text?.trim();
  if (finalSummary && !state.assistantStreamedThisTurn) {
    addMessage("assistant", finalSummary, "final");
  } else {
    finalizeActiveAssistantMessage();
  }

  state.finalText = content.final_output_text || "";
  state.filenames = content.filenames || [];
  const videoUrls = (content.video_urls || []).map(resolveMediaUrl);
  const encodedVideos = (content.image || []).filter((item) => item.startsWith("data:video/"));
  state.videos = [...videoUrls, ...encodedVideos];
  if (videoUrls[0] && !state.previewFinalUrl) {
    state.previewFinalUrl = videoUrls[0];
    state.previewFinalLabel = "完整视频";
    updateLivePreview();
  }
  render();
}

function handleVideoPreview(content: VideoPreviewContent): void {
  const normalizedContent = {
    ...content,
    url: resolveMediaUrl(content.url),
  };

  if (normalizedContent.status === "final") {
    state.previewFinalUrl = normalizedContent.url;
    state.previewFinalLabel = normalizedContent.label || "完整视频";
    updateLivePreview();
    return;
  }

  const exists = state.previewSegments.some(
    (segment) => segment.url === normalizedContent.url,
  );
  if (!exists) {
    state.previewSegments.push(normalizedContent);
    state.previewSegments.sort(
      (left, right) => (left.sequence ?? 0) - (right.sequence ?? 0),
    );
  }

  if (
    livePreviewVideoEl.ended &&
    state.previewCurrentIndex + 1 < state.previewSegments.length
  ) {
    state.previewCurrentIndex += 1;
  }
  updateLivePreview();
}

function updateLivePreview(): void {
  if (!state.previewFinalUrl && !state.previewSegments.length) {
    livePreviewEl.hidden = true;
    livePreviewVideoEl.removeAttribute("src");
    livePreviewVideoEl.dataset.currentUrl = "";
    previewSoundButton.hidden = true;
    livePreviewVideoEl.load();
    return;
  }

  livePreviewEl.hidden = false;
  if (state.previewFinalUrl) {
    livePreviewTitleEl.textContent = state.previewFinalLabel || "完整视频已生成";
    livePreviewMetaEl.textContent = "最终视频已就绪，可以播放带声音版本。";
    previewSoundButton.hidden = true;
    setLivePreviewSource(state.previewFinalUrl, false);
    return;
  }

  if (state.previewCurrentIndex >= state.previewSegments.length) {
    state.previewCurrentIndex = Math.max(0, state.previewSegments.length - 1);
  }

  const currentSegment = state.previewSegments[state.previewCurrentIndex];
  previewSoundButton.hidden = false;
  previewSoundButton.disabled =
    state.previewSoundEnabled && !state.previewAutoplayBlocked;
  previewSoundButton.textContent = state.previewAutoplayBlocked
    ? "继续播放"
    : state.previewSoundEnabled
      ? "声音预览已开启"
      : "开启声音预览";
  livePreviewTitleEl.textContent = "正在生成视频";
  const autoplayStatus = state.previewAutoplayBlocked
    ? " · 浏览器需要手动点击播放"
    : "";
  livePreviewMetaEl.textContent = `${state.previewSegments.length} 个片段已生成 · 正在预览第 ${
    state.previewCurrentIndex + 1
  } 个${autoplayStatus}`;
  setLivePreviewSource(currentSegment.url, state.previewSoundEnabled);
}

function setLivePreviewSource(source: string, autoplay: boolean): void {
  if (livePreviewVideoEl.dataset.currentUrl === source) {
    livePreviewVideoEl.muted = false;
    if (autoplay && !state.previewAutoplayBlocked) {
      requestPreviewPlay();
    }
    return;
  }

  livePreviewVideoEl.dataset.currentUrl = source;
  livePreviewVideoEl.src = source;
  livePreviewVideoEl.muted = false;
  livePreviewVideoEl.controls = true;

  if (autoplay && !state.previewAutoplayBlocked) {
    requestPreviewPlay();
  }
}

function requestPreviewPlay(): void {
  void livePreviewVideoEl.play().then(
    () => {
      state.previewAutoplayBlocked = false;
    },
    () => {
      state.previewAutoplayBlocked = true;
      updateLivePreview();
    },
  );
}

function addStatusStep(text: string): void {
  const normalized = text.trim();
  if (!normalized) {
    return;
  }

  state.statusSteps.push(normalized);
  render();
}

function appendAssistantDelta(text: string): void {
  if (!text) {
    return;
  }

  const message = getOrCreateActiveAssistantMessage();
  message.text += text;
  message.variant = "streaming";
  state.assistantStreamedThisTurn = true;
  render();
}

function mergeAssistantMessage(text: string): void {
  const normalized = text.trim();
  if (!normalized) {
    return;
  }

  const message = getOrCreateActiveAssistantMessage();
  if (!message.text || normalized.startsWith(message.text)) {
    message.text = normalized;
  } else if (!message.text.endsWith(normalized)) {
    message.text = `${message.text}\n${normalized}`;
  }
  message.variant = "streaming";
  state.assistantStreamedThisTurn = true;
  render();
}

function getOrCreateActiveAssistantMessage(): ChatMessage {
  if (state.activeAssistantMessageId) {
    const existing = state.messages.find(
      (message) => message.id === state.activeAssistantMessageId,
    );
    if (existing) {
      return existing;
    }
  }

  const message: ChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    text: "",
    variant: "streaming",
  };
  state.messages.push(message);
  state.activeAssistantMessageId = message.id;
  return message;
}

function finalizeActiveAssistantMessage(): void {
  if (!state.activeAssistantMessageId) {
    return;
  }

  const message = state.messages.find(
    (item) => item.id === state.activeAssistantMessageId,
  );
  if (message && message.text.trim()) {
    message.variant = "final";
  }
  state.activeAssistantMessageId = null;
}

function addMessage(
  role: ChatMessage["role"],
  text: string,
  variant?: ChatMessage["variant"],
): void {
  state.messages.push({
    id: crypto.randomUUID(),
    role,
    text,
    variant,
  });
  render();
}

function setBusy(value: boolean): void {
  state.busy = value;
  sendButton.disabled = value;
  promptInput.disabled = value;
  imageInput.disabled = value;
  documentInput.disabled = value;
}

function setConnectionStatus(label: string): void {
  connectionStatusEl.textContent = label;
  connectionStatusEl.dataset.state = label;
}

function render(): void {
  renderMessages();
  updateLivePreview();
  sendButton.textContent = state.busy ? "处理中" : "发送";
}

function renderMessages(): void {
  messagesEl.innerHTML = "";
  if (!state.messages.length) {
    messagesEl.appendChild(createWelcomeMessage());
  }

  const hasUserTurn = state.messages.some((message) => message.role === "user");
  const shouldShowStatus = hasUserTurn && (state.busy || state.statusSteps.length);
  let statusInserted = false;

  for (const message of state.messages) {
    if (shouldShowStatus && !statusInserted && message.role !== "user") {
      messagesEl.appendChild(createStatusMessage());
      statusInserted = true;
    }

    const row = document.createElement("article");
    row.className = `message ${message.role} ${message.variant ?? ""}`.trim();

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = message.role === "user" ? "You" : message.role === "system" ? "System" : "Tutor";

    const body = document.createElement("p");
    body.textContent = message.text;

    row.append(meta, body);
    messagesEl.appendChild(row);
  }

  if (shouldShowStatus && !statusInserted) {
    messagesEl.appendChild(createStatusMessage());
  }

  if (state.videos.length || state.finalText || state.filenames.length) {
    messagesEl.appendChild(createResultMessage());
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function createWelcomeMessage(): HTMLElement {
  const welcome = document.createElement("article");
  welcome.className = "welcome";

  const title = document.createElement("h2");
  title.textContent = "今天想讲解什么题？";

  const body = document.createElement("p");
  body.textContent = "输入题目后，我会把规划、执行步骤和最终视频放在同一个对话流里。";

  welcome.append(title, body);
  return welcome;
}

function createStatusMessage(): HTMLElement {
  const row = document.createElement("article");
  row.className = "message assistant status-message";

  const details = document.createElement("details");
  details.className = "status-panel";
  details.open = state.statusExpanded;
  details.addEventListener("toggle", () => {
    state.statusExpanded = details.open;
  });

  const summary = document.createElement("summary");
  summary.className = "status-summary";

  const chevron = document.createElement("span");
  chevron.className = "status-chevron";
  chevron.setAttribute("aria-hidden", "true");

  const title = document.createElement("span");
  title.className = "status-title";
  title.textContent = state.busy ? "执行中" : "执行过程";

  const meta = document.createElement("span");
  meta.className = "status-meta";
  const latestStep = state.statusSteps.at(-1);
  meta.textContent = latestStep
    ? `${state.statusSteps.length} 条状态 · ${latestStep}`
    : "等待后端返回状态";

  summary.append(chevron, title, meta);

  const list = document.createElement("ol");
  list.className = "status-list";

  const items = state.statusSteps.length
    ? state.statusSteps
    : ["正在提交任务并等待后端返回执行进度..."];

  for (const item of items) {
    const listItem = document.createElement("li");
    listItem.className = "status-item";
    listItem.textContent = item;
    list.appendChild(listItem);
  }

  details.append(summary, list);
  row.appendChild(details);
  return row;
}

function createResultMessage(): HTMLElement {
  const row = document.createElement("article");
  row.className = "message assistant final result-message";

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = "Tutor";

  const content = document.createElement("div");
  content.className = "result-content";

  if (state.finalText) {
    const finalText = document.createElement("p");
    finalText.className = "final-text";
    finalText.textContent = state.finalText;
    content.appendChild(finalText);
  }

  for (const [index, source] of state.videos.entries()) {
    const wrapper = document.createElement("section");
    wrapper.className = "video-card";

    const title = document.createElement("h3");
    title.textContent = `视频 ${index + 1}`;

    const video = document.createElement("video");
    video.controls = true;
    video.playsInline = true;
    video.src = source;

    wrapper.append(title, video);
    content.appendChild(wrapper);
  }

  if (state.filenames.length && state.userId && state.sessionId) {
    const fileList = document.createElement("div");
    fileList.className = "filename-list";

    for (const filename of state.filenames) {
      const link = document.createElement("a");
      link.href = `${API_BASE_URL}/file/download?user_id=${encodeURIComponent(
        state.userId,
      )}&session_id=${encodeURIComponent(state.sessionId)}&filename=${encodeURIComponent(filename)}`;
      link.textContent = filename;
      link.target = "_blank";
      link.rel = "noreferrer";
      fileList.appendChild(link);
    }

    content.appendChild(fileList);
  }

  row.append(meta, content);
  return row;
}

function mustGet<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Missing element: ${id}`);
  }
  return element as T;
}

function normalizeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveMediaUrl(url: string): string {
  if (url.startsWith("data:") || /^https?:\/\//i.test(url)) {
    return url;
  }
  if (url.startsWith("/")) {
    return `${API_BASE_URL}${url}`;
  }
  return `${API_BASE_URL}/${url}`;
}
