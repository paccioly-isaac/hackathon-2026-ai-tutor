import { format } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ReactNode } from 'react';
import type { ChatMessage as ChatMessageType, Question, QuestionAnswer } from '../types/chat';
import { QuestionCard } from './QuestionCard';
import { QuestionReference } from './QuestionReference';

interface ChatMessageProps {
  message: ChatMessageType;
  allQuestions: Question[];
  onAnswersChange?: (answers: QuestionAnswer[]) => void;
  onSubmitAnswers?: () => void;
  existingAnswers?: QuestionAnswer[];
  lockedAnswers?: QuestionAnswer[];
  isLoading?: boolean;
}

// Parse text and replace [qN] references with QuestionReference components
const renderTextWithReferences = (text: string, questions: Question[]): ReactNode => {
  const regex = /\[([qQ]\d+)\]/g;
  
  // Check if there are any references
  if (!regex.test(text)) {
    return text;
  }
  
  // Reset regex after test
  regex.lastIndex = 0;
  
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match;
  let keyCounter = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={`text-${keyCounter}`}>{text.slice(lastIndex, match.index)}</span>);
    }
    parts.push(
      <QuestionReference 
        key={`qref-${keyCounter}`}
        questionId={match[1].toLowerCase()} 
        questions={questions} 
      />
    );
    keyCounter++;
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(<span key={`text-${keyCounter}`}>{text.slice(lastIndex)}</span>);
  }

  return <>{parts}</>;
};

export const ChatMessage = ({ message, allQuestions, onAnswersChange, onSubmitAnswers, existingAnswers = [], lockedAnswers = [], isLoading = false }: ChatMessageProps) => {
  const isUser = message.metadata.user_role === 'student';
  const formattedTime = format(message.metadata.timestamp, 'h:mm a');
  const hasQuestions = message.questions && message.questions.length > 0;

  // Custom components for ReactMarkdown to handle [qN] references inline
  const processChildren = (child: ReactNode): ReactNode => {
    if (typeof child === 'string') {
      return renderTextWithReferences(child, allQuestions);
    }
    return child;
  };

  const processAllChildren = (children: ReactNode): ReactNode => {
    if (Array.isArray(children)) {
      return children.map((child, idx) => (
        <span key={idx}>{processChildren(child)}</span>
      ));
    }
    return processChildren(children);
  };

  const markdownComponents = {
    p: ({ children, ...props }: { children?: ReactNode }) => (
      <p {...props}>{processAllChildren(children)}</p>
    ),
    strong: ({ children, ...props }: { children?: ReactNode }) => (
      <strong {...props}>{processAllChildren(children)}</strong>
    ),
    em: ({ children, ...props }: { children?: ReactNode }) => (
      <em {...props}>{processAllChildren(children)}</em>
    ),
    li: ({ children, ...props }: { children?: ReactNode }) => (
      <li {...props}>{processAllChildren(children)}</li>
    ),
    td: ({ children, ...props }: { children?: ReactNode }) => (
      <td {...props}>{processAllChildren(children)}</td>
    ),
    th: ({ children, ...props }: { children?: ReactNode }) => (
      <th {...props}>{processAllChildren(children)}</th>
    ),
  };

  const renderMessage = () => (
    <ReactMarkdown 
      remarkPlugins={[remarkGfm]}
      components={markdownComponents}
    >
      {message.message}
    </ReactMarkdown>
  );

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
          <div className="bg-primary text-white p-4 rounded-2xl rounded-tr-none shadow-sm leading-relaxed prose prose-sm max-w-none prose-invert prose-p:text-white prose-headings:text-white prose-strong:text-white prose-a:text-white">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.message}
            </ReactMarkdown>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">{formattedTime}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center flex-shrink-0 text-secondary">
        <span className="material-icons text-xl">smart_toy</span>
      </div>
      <div className="flex flex-col gap-3 max-w-[85%]">
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">EduBot</span>
        
        {/* Message Content */}
        {message.message && (
          <div className="bg-surface-light dark:bg-surface-dark p-4 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-200 leading-relaxed prose prose-sm max-w-none dark:prose-invert">
            {renderMessage()}
            
            {/* Citations */}
            {message.cited_paragraphs && message.cited_paragraphs.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100/50 dark:border-gray-800 flex flex-wrap gap-0.5">
                {message.cited_paragraphs.map((citationId, index) => (
                  <a 
                    key={index}
                    href="https://www.saseducacao.com.br/" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300 transition-all no-underline group border border-gray-200/50 dark:border-gray-700/50"
                    title={citationId}
                    style={{ height: 28, lineHeight: '28px', padding: '0 8px' }}
                  >
                    <img src="/sasicon.ico" alt="" className="w-3.5 h-3.5 opacity-80 group-hover:opacity-100 transition-opacity" />
                    <span className="truncate max-w-[20ch]">{citationId}</span>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Questions Card */}
        {hasQuestions && onAnswersChange && (
          <QuestionCard 
            questions={message.questions!}
            title={message.questionsTitle}
            onAnswersChange={onAnswersChange}
            onSubmit={onSubmitAnswers}
            existingAnswers={existingAnswers}
            lockedAnswers={lockedAnswers}
            disabled={isLoading}
          />
        )}
        
        <span className="text-xs text-gray-400 dark:text-gray-500">{formattedTime}</span>
      </div>
    </div>
  );
};
