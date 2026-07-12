import request from './request'

/** /api/v1/ 健康检查。根路径 / 仅用于后端部署探活，不由前端页面调用。 */
export const getApiHealth = () => request.get('/')
