/**
 * 文件：src/api/health.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import request from './request'

/** /api/v1/ 健康检查。根路径 / 仅用于后端部署探活，不由前端页面调用。 */
export const getApiHealth = () => request.get('/')
