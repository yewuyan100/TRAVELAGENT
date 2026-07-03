const questions = [
  "成都适合喜欢美食和慢节奏旅行的人吗？",
  "北京三天怎么玩？",
  "成都明天适合去人民公园吗？",
  "上海适合购物还是历史文化游？",
  "东京迪士尼今天几点开门？",
  "大阪和京都怎么安排三日游？",
];

interface ExampleQuestionsProps {
  onPick: (question: string) => void;
  disabled?: boolean;
}

export default function ExampleQuestions({ onPick, disabled = false }: ExampleQuestionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {questions.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          onClick={() => onPick(question)}
        >
          {question}
        </button>
      ))}
    </div>
  );
}
