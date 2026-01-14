import { apiClient } from './client';
import type { TutorRequest, TutorResponse, Question } from '../types/chat';

interface ApiTutorResponse {
  answer: string;
  model_used: string;
  tokens_used?: number;
  questions?: Question[];
  questions_title?: string;
}

export const tutorApi = {
  async sendMessage(request: TutorRequest): Promise<TutorResponse> {
    const response = await apiClient.post<ApiTutorResponse>('/tutor/ask', request);
    return {
      answer: response.data.answer,
      model_used: response.data.model_used,
      tokens_used: response.data.tokens_used,
      questions: response.data.questions || [],
      questions_title: response.data.questions_title,
    };
  },

  async checkHealth(): Promise<{ status: string; model_loaded: boolean }> {
    const response = await apiClient.get('/health');
    return response.data;
  },
};
