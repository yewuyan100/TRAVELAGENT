import { MessageList } from "@/components/chat/MessageList";
import { InputArea } from "@/components/chat/InputArea";
import { AppLayout } from "@/components/layout/AppLayout";

export default function App() {
  return (
    <AppLayout>
      <MessageList />
      <InputArea />
    </AppLayout>
  );
}
