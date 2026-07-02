import { useState } from 'react';
import { sendChat, type ChatResponse } from './api/chat';
import ChatBox from './components/ChatBox';
import ExampleQuestions from './components/ExampleQuestions';
import MessageList, { type Message } from './components/MessageList';

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleAsk(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setError('');
    setLoading(true);
    setMessages((items) => [...items, { role: 'user', content: trimmed }]);

    try {
      const response: ChatResponse = await sendChat(trimmed, sessionId);
      setSessionId(response.session_id);
      setMessages((items) => [...items, { role: 'assistant', content: response.answer, response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : '请求失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>智能旅游 RAG Agent</h1>
            <p>本地知识库问答、天气工具、行程工具与来源解释</p>
          </div>
          <div className="session-pill">{sessionId ? `Session ${sessionId.slice(0, 8)}` : 'New Session'}</div>
        </header>

        <ExampleQuestions onPick={handleAsk} disabled={loading} />
        <MessageList messages={messages} loading={loading} />
        {error && <div className="error-banner">{error}</div>}
        <ChatBox onSubmit={handleAsk} loading={loading} />
      </section>
    </main>
  );
}
