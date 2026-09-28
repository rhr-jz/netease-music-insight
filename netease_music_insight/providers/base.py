"""Small provider contract shared by the CLI and exporters."""
from abc import ABC, abstractmethod


class CapabilityUnavailable(RuntimeError):
    """The platform cannot supply a reliable version of this data."""


class MusicProvider(ABC):
    name: str
    capabilities: dict[str, bool]

    @abstractmethod
    def login(self):
        """Authenticate the account and return its profile."""

    @abstractmethod
    def export(self, profile):
        """Write reports and return (output_folder, data)."""

    def logout(self):
        """Discard any in-memory credentials."""
