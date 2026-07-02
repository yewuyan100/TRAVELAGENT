import type { ChatResponse } from '../api/chat';
import SourceCard from './SourceCard';

export type Message = {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
};

type Props = {
  messages: Message[];
  loading: boolean;
};

export default function MessageList({ messages, loading }: Props) {
  if (!messages.length && !loading) {
    return <div className="empty-state">选择示例问题，或直接输入你的旅行问题。</div>;
  }

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <article key={`${message.role}-${index}`} className={`message ${message.role}`}>
          <div className="message-content">{message.content}</div>
          {message.response && (
            <div className="agent-meta">
              <div className="meta-row">
                <span>intent: {message.response.intent}</span>
                <span>tool: {message.response.selected_tool}</span>
                <span>confidence: {message.response.confidence.toFixed(2)}</span>
                {message.response.refused && <strong>资料不足 / 无法确认</strong>}
              </div>
              {!!message.response.sources.length && (
                <div className="sources-grid">
                  {message.response.sources.map((source) => (
                    <SourceCard key={`${source.id}-${source.title}`} source={source} />
                  ))}
                </div>
              )}
            </div>
          )}
        </article>
      ))}
      {loading && <div className="message assistant loading">Agent 正在选择工具并生成回答...</div>}
    </div>
  );
}
