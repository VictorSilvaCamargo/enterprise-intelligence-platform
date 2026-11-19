export interface ApiErrorPayload {
  error_code: string;
  message: string;
  request_id: string;
  timestamp: string;
  details?: Record<string, unknown> | null;
}

export interface HttpResponse<T> {
  status: number;
  data: T;
  requestId: string | null;
}
