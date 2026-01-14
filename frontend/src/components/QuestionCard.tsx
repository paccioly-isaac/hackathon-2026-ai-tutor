import { useState, useEffect, useMemo } from 'react';
import type { Question, QuestionAnswer } from '../types/chat';

interface QuestionCardProps {
  questions: Question[];
  title?: string;
  onAnswersChange: (answers: QuestionAnswer[]) => void;
  onSubmit?: () => void;
  existingAnswers?: QuestionAnswer[];
  lockedAnswers?: QuestionAnswer[];
  disabled?: boolean;
}

export const QuestionCard = ({ questions, title, onAnswersChange, onSubmit, existingAnswers = [], lockedAnswers = [], disabled = false }: QuestionCardProps) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, string>>(new Map());

  // Create a set of locked question IDs for quick lookup
  const lockedQuestionIds = useMemo(() => {
    return new Set(lockedAnswers.map(a => a.questionId));
  }, [lockedAnswers]);

  // Create a map of locked answers
  const lockedAnswersMap = useMemo(() => {
    const map = new Map<string, string>();
    lockedAnswers.forEach(a => map.set(a.questionId, a.selectedOptionId));
    return map;
  }, [lockedAnswers]);

  // Initialize answers from existing answers (not locked ones)
  useEffect(() => {
    if (existingAnswers.length > 0) {
      const answerMap = new Map<string, string>();
      existingAnswers.forEach(a => {
        // Only add non-locked answers to the editable state
        if (!lockedQuestionIds.has(a.questionId)) {
          answerMap.set(a.questionId, a.selectedOptionId);
        }
      });
      setAnswers(answerMap);
    }
  }, [existingAnswers, lockedQuestionIds]);

  const currentQuestion = questions[currentIndex];
  const totalQuestions = questions.length;
  const isCurrentLocked = lockedQuestionIds.has(currentQuestion.id);
  
  // Count only non-locked answered questions for submit
  const pendingAnswerCount = answers.size;

  const handleOptionSelect = (optionId: string) => {
    if (disabled || isCurrentLocked) return;
    const newAnswers = new Map(answers);
    newAnswers.set(currentQuestion.id, optionId);
    setAnswers(newAnswers);
    
    // Convert to array and notify parent (only non-locked answers)
    const answersArray: QuestionAnswer[] = Array.from(newAnswers.entries()).map(([questionId, selectedOptionId]) => ({
      questionId,
      selectedOptionId,
    }));
    onAnswersChange(answersArray);
  };

  const goToQuestion = (index: number) => {
    if (index >= 0 && index < totalQuestions) {
      setCurrentIndex(index);
    }
  };

  const handleSubmit = () => {
    if (onSubmit && pendingAnswerCount > 0 && !disabled) {
      onSubmit();
    }
  };

  // Get selected option: check locked first, then pending answers
  const selectedOption = isCurrentLocked 
    ? lockedAnswersMap.get(currentQuestion.id) 
    : answers.get(currentQuestion.id);

  return (
    <div className="bg-surface-light dark:bg-surface-dark rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-lg">
      {/* Header */}
      <div className="bg-primary/10 dark:bg-primary/20 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className="material-icons text-primary text-xl">quiz</span>
          <span className="font-semibold text-gray-800 dark:text-gray-200">
            {title || 'Questions'}
          </span>
        </div>
      </div>

      {/* Question Navigation Dots */}
      <div className="flex items-center justify-center gap-2 py-3 border-b border-gray-100 dark:border-gray-700">
        {questions.map((q, idx) => {
          const isLocked = lockedQuestionIds.has(q.id);
          const isAnswered = answers.has(q.id);
          const isCurrent = idx === currentIndex;
          return (
            <button
              key={q.id}
              onClick={() => goToQuestion(idx)}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all
                ${isCurrent 
                  ? isLocked
                    ? 'bg-gray-500 text-white scale-110 shadow-md'
                    : 'bg-primary text-white scale-110 shadow-md' 
                  : isLocked
                    ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400'
                    : isAnswered 
                      ? 'bg-accent/20 text-accent hover:bg-accent/30' 
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              title={`Questão ${idx + 1}${isLocked ? ' (enviada)' : isAnswered ? ' (pendente)' : ''}`}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>

      {/* Question Content */}
      <div className="p-5">
        <div className="mb-4">
          <p className="text-gray-800 dark:text-gray-200 font-medium leading-relaxed">
            {currentQuestion.question}
          </p>
        </div>

        {/* Options */}
        <div className="space-y-2.5">
          {currentQuestion.options.map((option) => {
            const isSelected = selectedOption === option.id;
            const isCorrect = isCurrentLocked && option.isCorrect;
            const isWrong = isCurrentLocked && isSelected && !option.isCorrect;
            
            return (
              <button
                key={option.id}
                onClick={() => handleOptionSelect(option.id)}
                disabled={isCurrentLocked}
                className={`w-full p-3.5 rounded-xl text-left transition-all flex items-start gap-3 group
                  ${isCurrentLocked
                    ? isCorrect
                      ? 'bg-green-100 dark:bg-green-900/30 border-2 border-green-500 cursor-default'
                      : isWrong
                        ? 'bg-red-100 dark:bg-red-900/30 border-2 border-red-500 cursor-default'
                        : 'bg-gray-100 dark:bg-gray-800/50 border-2 border-transparent cursor-default opacity-60'
                    : isSelected
                      ? 'bg-primary/10 border-2 border-primary'
                      : 'bg-gray-50 dark:bg-gray-800/50 border-2 border-transparent hover:border-primary/50 hover:bg-primary/5'
                  }`}
              >
                <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 transition-colors
                  ${isCurrentLocked
                    ? isCorrect
                      ? 'bg-green-500 text-white'
                      : isWrong
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400'
                    : isSelected 
                      ? 'bg-primary text-white' 
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 group-hover:bg-primary/20 group-hover:text-primary'
                  }`}>
                  {option.id}
                </span>
                <span className={`flex-1 
                  ${isCurrentLocked
                    ? isCorrect
                      ? 'text-green-800 dark:text-green-200'
                      : isWrong
                        ? 'text-red-800 dark:text-red-200'
                        : 'text-gray-500 dark:text-gray-500'
                    : isSelected 
                      ? 'text-gray-900 dark:text-gray-100' 
                      : 'text-gray-700 dark:text-gray-300'
                  }`}>
                  {option.text}
                </span>
                {isCurrentLocked ? (
                  isCorrect ? (
                    <span className="material-icons text-green-500">check_circle</span>
                  ) : isWrong ? (
                    <span className="material-icons text-red-500">cancel</span>
                  ) : null
                ) : isSelected ? (
                  <span className="material-icons text-primary">check_circle</span>
                ) : null}
              </button>
            );
          })}
        </div>
        
        {/* Show explanation for locked questions */}
        {isCurrentLocked && currentQuestion.explanation && (
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <span className="font-semibold">Explicação:</span> {currentQuestion.explanation}
            </p>
          </div>
        )}
      </div>

      {/* Navigation Footer */}
      <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <button
            onClick={() => goToQuestion(currentIndex - 1)}
            disabled={currentIndex === 0}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <span className="material-icons text-lg">chevron_left</span>
            Anterior
          </button>
          
          <span className="text-sm text-gray-500 dark:text-gray-500">
            {currentIndex + 1} de {totalQuestions}
          </span>
          
          <button
            onClick={() => goToQuestion(currentIndex + 1)}
            disabled={currentIndex === totalQuestions - 1}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Próxima
            <span className="material-icons text-lg">chevron_right</span>
          </button>
        </div>
        
        {/* Submit Button - only show for pending (non-locked) answers */}
        {onSubmit && pendingAnswerCount > 0 && (
          <div className="mt-2 flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={disabled}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-primary dark:hover:text-primary hover:bg-primary/5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-icons text-sm">send</span>
              Enviar
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
