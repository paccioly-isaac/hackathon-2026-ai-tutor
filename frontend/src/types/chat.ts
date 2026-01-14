export interface QuestionOption {
  id: string;
  text: string;
  isCorrect: boolean;
}

export interface Question {
  id: string;
  question: string;
  options: QuestionOption[];
  explanation: string;
}

export interface QuestionAnswer {
  questionId: string;
  selectedOptionId: string;
}

export interface ChatMessage {
  message: string;
  metadata: {
    timestamp: number;     // Unix timestamp in milliseconds
    user_id: string;
    user_role: 'student' | 'ai_tutor';
    message_id: string;
    session_id: string;
  };
  questions?: Question[];  // Questions to display with this message
  questionsTitle?: string; // Title for the questions set
  cited_paragraphs?: string[]; // Cited paragraphs from retrieved content
}

export interface TutorRequest {
  question: string;
  context?: string;
  temperature?: number;
  session_id: string;      // Added to track conversation
  question_answers?: QuestionAnswer[];  // Answers to questions
}

export interface TutorResponse {
  answer: string;
  model_used: string;
  tokens_used?: number;
  questions?: Question[];  // Questions from the response
  questions_title?: string; // Title for the questions set
  cited_paragraphs?: string[]; // Cited paragraphs from retrieved content
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string;
  pendingAnswers: QuestionAnswer[];  // Answers waiting to be sent
  submittedAnswers: QuestionAnswer[];  // Answers already submitted (locked)
}
