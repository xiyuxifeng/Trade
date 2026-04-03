from __future__ import annotations


class AppError(Exception):
	"""Base application error."""


class ConfigError(AppError):
	"""Raised when config cannot be loaded or validated."""


class CapabilityMissingError(AppError):
	"""Raised when a requested capability is not available."""

	def __init__(self, capabilities: list[str]):
		super().__init__("Capability missing: " + ", ".join(capabilities))
		self.capabilities = capabilities
