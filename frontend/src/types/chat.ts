export interface ChatMessage {
  message: string;
  metadata: {
    timestamp: number;     // Unix timestamp in milliseconds
    user_id: string;
    user_role: 'student' | 'ai_tutor';
    message_id: string;
    session_id: string;
  };
}

export interface TutorRequest {
  question: string;
  context?: string;
  temperature?: number;
  session_id: string;      // Added to track conversation
}

export interface TutorResponse {
  answer: string;
  model_used: string;
  tokens_used?: number;
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string;
}
