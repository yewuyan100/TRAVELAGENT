const questions = [
  '成都适合喜欢美食和慢节奏旅行的人吗？',
  '北京三天怎么玩？',
  '成都明天适合去人民公园吗？',
  '上海适合购物还是历史文化游？',
  '东京迪士尼今天几点开门？',
  '大阪和京都怎么安排三日游？'
];

type Props = {
  onPick: (question: string) => void;
  disabled: boolean;
};

export default function ExampleQuestions({ onPick, disabled }: Props) {
  return (
    <div className="examples">
      {questions.map((question) => (
        <button key={question} disabled={disabled} onClick={() => onPick(question)}>
          {question}
        </button>
      ))}
    </div>
  );
}
