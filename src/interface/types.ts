export interface ChatMessage {
  message: string;
  metadata: {
    timestamp: number;     // 64-bit timestamp
    user_id: string;
    user_role: string;     // e.g. 'student' | 'ai_tutor'
    message_id: string;
    session_id: string;
  };
}