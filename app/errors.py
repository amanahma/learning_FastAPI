class AppError(Exception):
    """Base error converted to the public JSON error shape."""

    error: str = "app_error"
    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    error = "not_found"
    status_code = 404


class RateTimeoutError(AppError):
    error = "rate_timeout"
    status_code = 504


class RateAPIError(AppError):
    error = "rate_provider_error"
    status_code = 502


class UnknownCurrencyError(AppError):
    error = "unknown_currency"
    status_code = 400
