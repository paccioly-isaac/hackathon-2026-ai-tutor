import { useState, useCallback, useMemo } from 'react';
import { tutorApi } from '../api/tutor';
import type { ChatMessage, ChatState, QuestionAnswer, Question } from '../types/chat';
import { v4 as uuidv4 } from 'uuid';

export const useChat = () => {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
    sessionId: uuidv4(),
    pendingAnswers: [],
    submittedAnswers: [],
  });

  // Collect all questions from all messages
  const allQuestions = useMemo(() => {
    const questions: Question[] = [];
    state.messages.forEach(msg => {
      if (msg.questions) {
        questions.push(...msg.questions);
      }
    });
    return questions;
  }, [state.messages]);

  const setPendingAnswers = useCallback((answers: QuestionAnswer[]) => {
    setState(prev => ({ ...prev, pendingAnswers: answers }));
  }, []);

  const sendMessage = useCallback(async (messageText: string) => {
    // Get current pending answers before clearing
    const answersToSend = state.pendingAnswers;
    
    // Create user message (hardcoded user for local dev)
    const userMessage: ChatMessage = {
      message: messageText,
      metadata: {
        timestamp: Date.now(),
        user_id: 'alex_student_001',
        user_role: 'student',
        message_id: uuidv4(),
        session_id: state.sessionId,
      },
    };

    // Optimistically add user message, move pending to submitted, and clear pending
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
      pendingAnswers: [], // Clear pending answers after sending
      submittedAnswers: [...prev.submittedAnswers, ...answersToSend], // Lock submitted answers
    }));

    try {
      // Call backend with message and any pending answers
      const response = await tutorApi.sendMessage({
        question: messageText,
        session_id: state.sessionId,
        question_answers: answersToSend.length > 0 ? answersToSend : undefined,
      });

      // Create AI response message with questions if present
      const aiMessage: ChatMessage = {
        message: response.answer,
        metadata: {
          timestamp: Date.now(),
          user_id: 'ai_tutor',
          user_role: 'ai_tutor',
          message_id: uuidv4(),
          session_id: state.sessionId,
        },
        questions: response.questions,
        questionsTitle: response.questions_title,
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, aiMessage],
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to send message',
      }));
    }
  }, [state.sessionId, state.pendingAnswers]);

  // Submit only answers without a message (silent, no user message shown)
  const submitAnswersOnly = useCallback(async () => {
    if (state.pendingAnswers.length === 0) return;
    
    const answersToSend = state.pendingAnswers;

    setState((prev) => ({
      ...prev,
      isLoading: true,
      error: null,
      pendingAnswers: [],
      submittedAnswers: [...prev.submittedAnswers, ...answersToSend], // Lock submitted answers
    }));

    try {
      // Send with answers, but empty message indicates just submitting answers
      const response = await tutorApi.sendMessage({
        question: '', // Empty message, just submitting answers
        session_id: state.sessionId,
        question_answers: answersToSend,
      });

      const aiMessage: ChatMessage = {
        message: response.answer,
        metadata: {
          timestamp: Date.now(),
          user_id: 'ai_tutor',
          user_role: 'ai_tutor',
          message_id: uuidv4(),
          session_id: state.sessionId,
        },
        questions: response.questions,
        questionsTitle: response.questions_title,
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, aiMessage],
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to submit answers',
      }));
    }
  }, [state.sessionId, state.pendingAnswers]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    sessionId: state.sessionId,
    pendingAnswers: state.pendingAnswers,
    submittedAnswers: state.submittedAnswers,
    allQuestions,
    sendMessage,
    submitAnswersOnly,
    setPendingAnswers,
    clearError,
  };
};
