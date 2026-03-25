import { useState } from 'react';

export interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
}

export interface UseChatbotReturn {
  isOpen: boolean;
  messages: ChatMessage[];
  input: string;
  openChatbot: () => void;
  closeChatbot: () => void;
  setInput: (value: string) => void;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  sendMessage: () => void;
}

/**
 * Custom hook for managing chatbot state and logic
 * Separates chatbot concerns from layout components
 */
export const useChatbot = (): UseChatbotReturn => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 1, text: 'Hello! How can I assist you today?', sender: 'bot' },
  ]);

  const openChatbot = () => setIsOpen(true);
  const closeChatbot = () => setIsOpen(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const sendMessage = () => {
    if (input.trim() === '') return;
    
    const newMessage: ChatMessage = {
      id: messages.length + 1,
      text: input,
      sender: 'user',
    };
    
    setMessages(prevMessages => [...prevMessages, newMessage]);
    setInput('');
    
    // TODO: Add bot response logic here
    // For now, this is just a placeholder
    setTimeout(() => {
      const botResponse: ChatMessage = {
        id: messages.length + 2,
        text: 'Thank you for your message. This is an automated response.',
        sender: 'bot',
      };
      setMessages(prevMessages => [...prevMessages, botResponse]);
    }, 500);
  };

  return {
    isOpen,
    messages,
    input,
    openChatbot,
    closeChatbot,
    setInput,
    handleInputChange,
    sendMessage,
  };
};
