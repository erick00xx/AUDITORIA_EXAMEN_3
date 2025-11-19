import { useState, type FormEvent, type ReactNode } from 'react';

export interface Message {
  id: number;
  conversation_id?: number;
  content: string;  // ✅ coincide con el backend (FastAPI)
  sender: 'user' | 'bot';
}

interface ChatHandlerProps {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (input: string) => Promise<void>;
  children: (props: {
    messages: Message[];
    input: string;
    setInput: (value: string) => void;
    handleSubmit: (e: FormEvent) => void;
    isLoading: boolean;
  }) => ReactNode;
}

export function ChatHandler({ messages, isLoading, sendMessage, children }: ChatHandlerProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  return children({ messages, input, setInput, handleSubmit, isLoading });
}
