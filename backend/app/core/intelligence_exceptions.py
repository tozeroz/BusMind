from __future__ import annotations


class BusinessError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ResourceNotFoundError(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(40400, message, 404)


class ModelUnavailableError(BusinessError):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(code, message, 503)
