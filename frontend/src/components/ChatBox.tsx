import { useState } from 'react';

type Props = {
  onSubmit: (question: string) => void;
  loading: boolean;
};

export default function ChatBox({ onSubmit, loading }: Props) {
  const [value, setValue] = useState('');

  function submit() {
    const question = value.trim();
    if (!question) return;
    onSubmit(question);
    setValue('');
  }

  return (
    <div className="chat-box">
      <textarea
        value={value}
        disabled={loading}
        placeholder="输入旅行问题，例如：北京三天怎么玩？"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button disabled={loading || !value.trim()} onClick={submit}>
        {loading ? '思考中...' : '发送'}
      </button>
    </div>
  );
}
