import { apiClient } from './client';
import type { TutorRequest, TutorResponse } from '../types/chat';

export const tutorApi = {
  async sendMessage(request: TutorRequest): Promise<TutorResponse> {
    const response = await apiClient.post<TutorResponse>('/tutor/ask', request);
    return response.data;
  },

  async checkHealth(): Promise<{ status: string; model_loaded: boolean }> {
    const response = await apiClient.get('/health');
    return response.data;
  },
};
