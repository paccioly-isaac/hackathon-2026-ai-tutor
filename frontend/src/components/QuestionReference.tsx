import { useState } from 'react';
import type { Question } from '../types/chat';

interface QuestionReferenceProps {
  questionId: string;
  questions: Question[];
}

export const QuestionReference = ({ questionId, questions }: QuestionReferenceProps) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const questionIndex = questions.findIndex(q => q.id === questionId);
  const question = questionIndex >= 0 ? questions[questionIndex] : null;
  
  if (!question) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-sm font-mono">
        [{questionId}]
      </span>
    );
  }

  const displayNumber = questionIndex + 1;

  return (
    <span className="relative inline">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-primary/20 text-primary hover:bg-primary/30 text-xs font-semibold transition-colors cursor-pointer align-baseline whitespace-nowrap"
      >
        <span className="material-icons text-xs leading-none">quiz</span>
        Questão {displayNumber}
      </button>
      
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Popup */}
          <div className="absolute left-0 top-full mt-2 z-50 w-80 bg-surface-light dark:bg-surface-dark rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="bg-primary/10 dark:bg-primary/20 px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <span className="font-semibold text-gray-800 dark:text-gray-200 text-sm">
                Questão {displayNumber}
              </span>
              <button 
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <span className="material-icons text-lg">close</span>
              </button>
            </div>
            
            <div className="p-3">
              <p className="text-gray-800 dark:text-gray-200 text-sm mb-3">
                {question.question}
              </p>
              
              <div className="space-y-1.5">
                {question.options.map((option) => (
                  <div
                    key={option.id}
                    className={`flex items-start gap-2 p-2 rounded-lg text-sm
                      ${option.isCorrect 
                        ? 'bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700' 
                        : 'bg-gray-50 dark:bg-gray-800/50'
                      }`}
                  >
                    <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold shrink-0
                      ${option.isCorrect 
                        ? 'bg-green-500 text-white' 
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                      }`}>
                      {option.id}
                    </span>
                    <span className={option.isCorrect ? 'text-green-800 dark:text-green-200' : 'text-gray-700 dark:text-gray-300'}>
                      {option.text}
                    </span>
                    {option.isCorrect && (
                      <span className="material-icons text-green-500 text-sm ml-auto">check</span>
                    )}
                  </div>
                ))}
              </div>
              
              {question.explanation && (
                <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-blue-800 dark:text-blue-200">
                    <span className="font-semibold">Explicação:</span> {question.explanation}
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </span>
  );
};
