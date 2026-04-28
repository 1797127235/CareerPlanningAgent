"""
backend2/core/errors.py — 统一错误类型。

所有 v2 service 通过这里抛出可预期的错误，
router 层统一捕获并转成标准 HTTP 响应。
"""
from __future__ import annotations


class AppError(Exception):
    """业务层基础错误。"""
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "", *, status_code: int | None = None, code: str | None = None):
        self.detail = detail or self.__class__.__doc__ or ""
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(self.detail)


class NotFoundError(AppError):
    """资源不存在。"""
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    """未登录。"""
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    """无权限。"""
    status_code = 403
    code = "FORBIDDEN"


class BadRequestError(AppError):
    """请求参数不合法。"""
    status_code = 400
    code = "BAD_REQUEST"


class ProfileNotFoundError(AppError):
    """用户画像不存在。"""
    status_code = 404
    code = "PROFILE_NOT_FOUND"

    def __init__(self):
        super().__init__("请先上传简历建立用户画像")


class LLMError(AppError):
    """LLM 调用失败。"""
    status_code = 502
    code = "LLM_ERROR"
