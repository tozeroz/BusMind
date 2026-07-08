import request from './request'

export const sendAiMessage = (data) => request.post('/ai/chat', data)
