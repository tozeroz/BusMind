import request from './request'

export const askAiTravel = (data) => request.post('/ai/travel', data)

export const sendAiMessage = askAiTravel
