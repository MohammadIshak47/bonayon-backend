"""Domain errors. Services/repositories raise these; main.py maps them to HTTP responses."""


class AppErrorBase(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppErrorBase):
    status_code = 404


class ForbiddenError(AppErrorBase):
    status_code = 403


class ConflictError(AppErrorBase):
    status_code = 409


class BadRequestError(AppErrorBase):
    status_code = 400


class InsufficientDataError(AppErrorBase):
    """Not enough climate data to give an honest answer (never guessed)."""
    status_code = 503

    def __init__(self, detail: str) -> None:
        super().__init__(f"INSUFFICIENT_DATA: {detail}")
