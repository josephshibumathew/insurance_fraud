"""Groq API client wrapper for report generation with resiliency controls."""

from __future__ import annotations

import importlib
import os
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


SUPPORTED_GROQ_MODELS = {
	"mixtral-8x7b-32768",
	"llama3-70b-8192",
	"llama3-8b-8192",
	"gemma2-9b-it",
}


class GroqClientError(RuntimeError):
	"""Raised when Groq calls fail after all retries."""


class RateLimiter:
	"""Token-bucket-like limiter using a rolling one-minute window."""

	def __init__(self, requests_per_minute: int = 30) -> None:
		if requests_per_minute <= 0:
			raise ValueError("requests_per_minute must be > 0")
		self.requests_per_minute = requests_per_minute
		self._timestamps: deque[float] = deque()
		self._lock = threading.Lock()

	def acquire(self) -> None:
		while True:
			wait_time = 0.0
			with self._lock:
				now = time.time()
				cutoff = now - 60.0
				while self._timestamps and self._timestamps[0] <= cutoff:
					self._timestamps.popleft()

				if len(self._timestamps) < self.requests_per_minute:
					self._timestamps.append(now)
					return

				wait_time = max(0.01, 60.0 - (now - self._timestamps[0]))

			time.sleep(wait_time)


@dataclass(slots=True)
class GroqClientConfig:
	"""Runtime configuration for Groq access."""

	model: str = "llama3-70b-8192"
	requests_per_minute: int = 30
	max_retries: int = 3
	backoff_base_seconds: float = 0.5
	timeout_seconds: float = 15.0


class GroqClient:
	"""Safe Groq chat-completions client with retry and rate limiting."""

	def __init__(self, api_key: str | None = None, config: GroqClientConfig | None = None) -> None:
		self.config = config or GroqClientConfig()
		self.api_key = api_key or os.getenv("GROQ_API_KEY")
		if not self.api_key:
			raise GroqClientError("Missing GROQ_API_KEY environment variable.")

		if self.config.model not in SUPPORTED_GROQ_MODELS:
			raise GroqClientError(
				f"Unsupported model '{self.config.model}'. Supported: {sorted(SUPPORTED_GROQ_MODELS)}"
			)

		try:
			groq_module = importlib.import_module("groq")
		except Exception as exc:
			raise GroqClientError("groq package is required. Install with `pip install groq`.") from exc

		groq_cls = getattr(groq_module, "Groq", None)
		if groq_cls is None:
			raise GroqClientError("Could not resolve Groq client class from groq package.")

		self._client = groq_cls(api_key=self.api_key)
		self._limiter = RateLimiter(self.config.requests_per_minute)

	def _call_chat_completion(
		self,
		*,
		system_prompt: str,
		user_prompt: str,
		model: str,
		temperature: float,
		max_tokens: int,
	) -> str:
		response = self._client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			temperature=temperature,
			max_tokens=max_tokens,
			timeout=self.config.timeout_seconds,
		)

		choices = getattr(response, "choices", None)
		if not choices:
			raise GroqClientError("Empty response from Groq API.")

		message = getattr(choices[0], "message", None)
		content = getattr(message, "content", "") if message is not None else ""
		if not isinstance(content, str) or not content.strip():
			raise GroqClientError("Groq response did not contain text content.")
		return content.strip()

	def generate(
		self,
		*,
		system_prompt: str,
		user_prompt: str,
		model: str | None = None,
		temperature: float = 0.2,
		max_tokens: int = 1500,
	) -> str:
		"""Generate completion text from Groq with retries and backoff."""
		selected_model = model or self.config.model
		if selected_model not in SUPPORTED_GROQ_MODELS:
			raise GroqClientError(f"Unsupported model '{selected_model}'.")

		last_error: Exception | None = None
		for attempt in range(self.config.max_retries + 1):
			try:
				self._limiter.acquire()
				return self._call_chat_completion(
					system_prompt=system_prompt,
					user_prompt=user_prompt,
					model=selected_model,
					temperature=temperature,
					max_tokens=max_tokens,
				)
			except Exception as exc:
				last_error = exc
				if attempt >= self.config.max_retries:
					break

				jitter = random.uniform(0.0, 0.3)
				delay = self.config.backoff_base_seconds * (2**attempt) + jitter
				time.sleep(delay)

		raise GroqClientError(f"Groq API request failed after retries: {last_error}")


def build_groq_client(**kwargs: Any) -> GroqClient:
	"""Convenience factory for app integrations."""
	config = GroqClientConfig(
		model=kwargs.get("model", "llama3-70b-8192"),
		requests_per_minute=int(kwargs.get("requests_per_minute", 30)),
		max_retries=int(kwargs.get("max_retries", 3)),
		backoff_base_seconds=float(kwargs.get("backoff_base_seconds", 0.5)),
		timeout_seconds=float(kwargs.get("timeout_seconds", 15.0)),
	)
	return GroqClient(api_key=kwargs.get("api_key"), config=config)

