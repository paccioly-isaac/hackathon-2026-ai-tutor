import { format } from 'date-fns';
import { ChatMessage as ChatMessageType } from '../types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.metadata.user_role === 'student';
  const formattedTime = format(message.metadata.timestamp, 'h:mm a');

  if (isUser) {
    return (
      <div className="flex gap-4 flex-row-reverse">
        <img
          alt="User Avatar"
          className="w-10 h-10 rounded-full object-cover flex-shrink-0 border-2 border-white dark:border-gray-700"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBDms81vCm1mscKQTrrz3cagUl6e8-LOC6ES_IJm141SSmfor2SLt9VnSO1qY-fFiCde_9cRHUs40rugDB8qVQU0uiTJ4HfPUL91qJBeE_Xk2OrHCdSPAFHngd6miIy1mcbRs0ZAUcPCNJRoxrCa6CIKTJBpYtLLqiDq4WZ1zV-D_3U2PHq2LoHOx_tfJ9CfbX9l9V5K22psqdggNjYtwK0R_5ZN5zwNlMiTengZ5h8PrTjioM8NCcq0hsief0cFb8Oaec1mM5khw"
        />
        <div className="flex flex-col gap-1 items-end max-w-[80%]">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">You</span>
          <div className="bg-primary text-white p-4 rounded-2xl rounded-tr-none shadow-sm leading-relaxed">
            <p>{message.message}</p>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">{formattedTime}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center flex-shrink-0 text-indigo-600 dark:text-indigo-300">
        <span className="material-icons text-xl">smart_toy</span>
      </div>
      <div className="flex flex-col gap-1 max-w-[80%]">
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">EduBot</span>
        <div className="bg-surface-light dark:bg-surface-dark p-4 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-200 leading-relaxed">
          <p>{message.message}</p>
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">{formattedTime}</span>
      </div>
    </div>
  );
};
