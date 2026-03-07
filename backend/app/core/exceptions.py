"""Application-specific exception types."""

from __future__ import annotations


class AppError(Exception):
	"""Base app exception."""

	def __init__(self, message: str, status_code: int = 400) -> None:
		super().__init__(message)
		self.message = message
		self.status_code = status_code


class NotFoundError(AppError):
	def __init__(self, message: str = "Resource not found") -> None:
		super().__init__(message=message, status_code=404)


class ConflictError(AppError):
	def __init__(self, message: str = "Resource conflict") -> None:
		super().__init__(message=message, status_code=409)


class UnauthorizedError(AppError):
	def __init__(self, message: str = "Unauthorized") -> None:
		super().__init__(message=message, status_code=401)

