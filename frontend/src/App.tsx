import { useChat } from './hooks/useChat';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { TypingIndicator } from './components/TypingIndicator';
import { useEffect, useRef } from 'react';

function App() {
  const { 
    messages, 
    isLoading, 
    error, 
    sendMessage, 
    submitAnswersOnly,
    setPendingAnswers,
    pendingAnswers,
    submittedAnswers,
    allQuestions,
    clearError 
  } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex h-screen bg-background-light dark:bg-background-dark">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full bg-background-light dark:bg-background-dark relative">
        <ChatHeader />

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 m-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="material-icons text-red-500 mr-2">error</span>
                <p className="text-red-700 dark:text-red-200">{error}</p>
              </div>
              <button
                onClick={clearError}
                className="text-red-500 hover:text-red-700 dark:hover:text-red-300"
              >
                <span className="material-icons">close</span>
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 md:p-6 max-w-5xl mx-auto w-full">
          <div className="space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <span className="material-icons text-6xl text-secondary/30 mb-4">
                  chat_bubble_outline
                </span>
                <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Start a conversation
                </h2>
                <p className="text-gray-500 dark:text-gray-400">
                  Ask me anything about your studies!
                </p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <ChatMessage 
                key={msg.metadata.message_id} 
                message={msg} 
                allQuestions={allQuestions}
                onAnswersChange={msg.questions && msg.questions.length > 0 ? setPendingAnswers : undefined}
                onSubmitAnswers={msg.questions && msg.questions.length > 0 ? submitAnswersOnly : undefined}
                existingAnswers={pendingAnswers}
                lockedAnswers={submittedAnswers}
                isLoading={isLoading}
              />
            ))}

            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatInput 
          onSendMessage={sendMessage} 
          disabled={isLoading} 
          pendingAnswersCount={pendingAnswers.length}
        />
      </main>
    </div>
  );
}

export default App;
