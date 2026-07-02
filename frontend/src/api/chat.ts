export type SourceRef = {
  id: string;
  title: string;
  city: string;
  category: string;
  score: number;
  tags?: string[];
};

export type ChatResponse = {
  answer: string;
  session_id: string;
  intent: string;
  selected_tool: string;
  confidence: number;
  sources: SourceRef[];
  refused: boolean;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function sendChat(question: string, sessionId?: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId || null })
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || '请求失败，请稍后重试。');
  }

  return response.json();
}
