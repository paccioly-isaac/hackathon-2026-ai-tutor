import { useState } from 'react';
import type { KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled: boolean;
}

export const ChatInput = ({ onSendMessage, disabled }: ChatInputProps) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-4">
      <div className="bg-surface-light dark:bg-surface-dark p-2 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 flex items-end gap-2">
        <button
          disabled
          className="p-3 text-gray-400 cursor-not-allowed rounded-lg opacity-50"
          title="File attachments coming soon"
        >
          <span className="material-icons">attach_file</span>
        </button>
        <div className="flex-1 py-2">
          <textarea
            className="w-full bg-transparent border-0 focus:ring-0 text-gray-800 dark:text-gray-100 placeholder-gray-400 resize-none max-h-32 py-1 focus:outline-none"
            placeholder="Type your message..."
            rows={1}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            style={{ minHeight: '24px' }}
          />
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="p-3 bg-primary hover:bg-opacity-90 text-white rounded-lg shadow-sm transition-all transform hover:scale-105 active:scale-95 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          <span className="material-icons">send</span>
        </button>
      </div>
      <div className="text-center mt-2">
        <p className="text-xs text-gray-400 dark:text-gray-500">
          AI can make mistakes. Please verify important information.
        </p>
      </div>
    </div>
  );
};
