import { useState, useCallback } from 'react';
import { tutorApi } from '../api/tutor';
import { ChatMessage, ChatState } from '../types/chat';
import { v4 as uuidv4 } from 'uuid';

export const useChat = () => {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
    sessionId: uuidv4(),
  });

  const sendMessage = useCallback(async (messageText: string) => {
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

    // Optimistically add user message
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      // Call backend
      const response = await tutorApi.sendMessage({
        question: messageText,
        session_id: state.sessionId,
      });

      // Create AI response message
      const aiMessage: ChatMessage = {
        message: response.answer,
        metadata: {
          timestamp: Date.now(),
          user_id: 'ai_tutor',
          user_role: 'ai_tutor',
          message_id: uuidv4(),
          session_id: state.sessionId,
        },
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
  }, [state.sessionId]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    sessionId: state.sessionId,
    sendMessage,
    clearError,
  };
};
