"""
Secrets management for NeedleAi.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.utils.logging import get_logger
from pydantic import SecretStr

logger = get_logger("secrets")


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret value by key."""

    @abstractmethod
    def list_secrets(self) -> Dict[str, str]:
        """List all available secrets."""


class EnvironmentSecretProvider(SecretProvider):
    """Get secrets from environment variables."""

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment variable."""
        return os.getenv(key)

    def list_secrets(self) -> Dict[str, str]:
        """List all environment variables (values masked)."""
        return {k: "***" for k in os.environ.keys()}


class FileSecretProvider(SecretProvider):
    """Get secrets from JSON files."""

    def __init__(self, secrets_file: Path):
        self.secrets_file = Path(secrets_file)
        self._secrets: Dict[str, str] = {}
        self._load_secrets()

    def _load_secrets(self):
        """Load secrets from file."""
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, 'r') as f:
                    self._secrets = json.load(f)
                logger.info(f"Loaded {len(self._secrets)} secrets from {self.secrets_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load secrets from {self.secrets_file}: {e}")
                self._secrets = {}
        else:
            logger.debug(f"Secrets file {self.secrets_file} not found")

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from loaded data."""
        return self._secrets.get(key)

    def list_secrets(self) -> Dict[str, str]:
        """List all secrets (values masked)."""
        return {k: "***" for k in self._secrets.keys()}


class DockerSecretProvider(SecretProvider):
    """Get secrets from Docker Swarm secrets directory."""

    def __init__(self, secrets_dir: Path = Path("/run/secrets")):
        self.secrets_dir = Path(secrets_dir)

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Docker secrets file."""
        secret_file = self.secrets_dir / key
        if secret_file.exists():
            try:
                return secret_file.read_text().strip()
            except IOError as e:
                logger.error(f"Failed to read Docker secret {key}: {e}")
        return None

    def list_secrets(self) -> Dict[str, str]:
        """List all available Docker secrets."""
        if not self.secrets_dir.exists():
            return {}

        secrets = {}
        for secret_file in self.secrets_dir.iterdir():
            if secret_file.is_file():
                secrets[secret_file.name] = "***"
        return secrets


class KubernetesSecretProvider(SecretProvider):
    """Get secrets from Kubernetes mounted secrets."""

    def __init__(self, secrets_dir: Path = Path("/etc/secrets")):
        self.secrets_dir = Path(secrets_dir)

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Kubernetes mounted file."""
        # Try direct file name first
        secret_file = self.secrets_dir / key
        if secret_file.exists():
            try:
                return secret_file.read_text().strip()
            except IOError as e:
                logger.error(f"Failed to read K8s secret {key}: {e}")

        # Try lowercase version
        secret_file_lower = self.secrets_dir / key.lower()
        if secret_file_lower.exists():
            try:
                return secret_file_lower.read_text().strip()
            except IOError as e:
                logger.error(f"Failed to read K8s secret {key}: {e}")

        return None

    def list_secrets(self) -> Dict[str, str]:
        """List all available Kubernetes secrets."""
        if not self.secrets_dir.exists():
            return {}

        secrets = {}
        for secret_file in self.secrets_dir.iterdir():
            if secret_file.is_file():
                secrets[secret_file.name] = "***"
        return secrets


class HashiCorpVaultProvider(SecretProvider):
    """Get secrets from HashiCorp Vault (placeholder implementation)."""

    def __init__(self, vault_url: str, vault_token: str):
        self.vault_url = vault_url
        self.vault_token = vault_token
        # TODO: Implement actual Vault integration
        logger.warning("HashiCorp Vault provider not fully implemented")

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from Vault."""
        # Placeholder - implement actual Vault API calls
        logger.warning(f"Vault secret retrieval for {key} not implemented")
        return None

    def list_secrets(self) -> Dict[str, str]:
        """List secrets from Vault."""
        # Placeholder - implement actual Vault API calls
        return {}


class SecretManager:
    """
    Centralized secrets management with multiple providers.

    Supports environment variables, file-based secrets, Docker secrets,
    Kubernetes secrets, and HashiCorp Vault.
    """

    def __init__(self):
        self.providers: list[SecretProvider] = []
        self._setup_providers()

    def _setup_providers(self):
        """Setup secret providers in priority order."""
        # 1. Environment variables (highest priority)
        self.providers.append(EnvironmentSecretProvider())

        # 2. Docker secrets
        if Path("/run/secrets").exists():
            self.providers.append(DockerSecretProvider())
            logger.info("Docker secrets provider enabled")

        # 3. Kubernetes secrets
        if Path("/etc/secrets").exists():
            self.providers.append(KubernetesSecretProvider())
            logger.info("Kubernetes secrets provider enabled")

        # 4. Local secrets file
        secrets_file = Path(".secrets.json")
        if secrets_file.exists():
            self.providers.append(FileSecretProvider(secrets_file))
            logger.info("File secrets provider enabled")

        # 5. HashiCorp Vault (if configured)
        vault_url = os.getenv("VAULT_URL")
        vault_token = os.getenv("VAULT_TOKEN")
        if vault_url and vault_token:
            self.providers.append(HashiCorpVaultProvider(vault_url, vault_token))
            logger.info("HashiCorp Vault provider enabled")

        logger.info(f"Initialized {len(self.providers)} secret providers")

    def get_secret(self, key: str) -> Optional[str]:
        """
        Get secret value from the first provider that has it.

        Args:
            key: Secret key name

        Returns:
            Secret value or None if not found
        """
        # Convert key to uppercase for environment variables
        env_key = key.upper()

        for provider in self.providers:
            # Try original key first
            value = provider.get_secret(key)
            if value:
                logger.debug(f"Found secret '{key}' from {provider.__class__.__name__}")
                return value

            # Try uppercase version for env vars
            if key != env_key:
                value = provider.get_secret(env_key)
                if value:
                    logger.debug(f"Found secret '{env_key}' from {provider.__class__.__name__}")
                    return value

        logger.debug(f"Secret '{key}' not found in any provider")
        return None

    def get_secret_str(self, key: str) -> Optional[SecretStr]:
        """Get secret as SecretStr for Pydantic."""
        value = self.get_secret(key)
        return SecretStr(value) if value else None

    def list_all_secrets(self) -> Dict[str, Dict[str, str]]:
        """List secrets from all providers."""
        all_secrets = {}
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            all_secrets[provider_name] = provider.list_secrets()
        return all_secrets

    def validate_required_secrets(self, required_keys: list[str]) -> Dict[str, bool]:
        """
        Validate that required secrets are available.

        Args:
            required_keys: List of required secret keys

        Returns:
            Dictionary mapping key to availability status
        """
        validation_results = {}
        for key in required_keys:
            value = self.get_secret(key)
            validation_results[key] = value is not None
            if not value:
                logger.warning(f"Required secret '{key}' is missing")

        return validation_results

    @staticmethod
    def as_settings_source() -> Callable:
        """Create a Pydantic settings source from SecretManager."""
        def settings_source(settings: Any) -> Dict[str, Any]:
            """Pydantic settings source function."""
            manager = SecretManager()
            source_data = {}

            # Get all fields from the settings model
            if hasattr(settings, '__fields__'):
                for field_name, field in settings.__fields__.items():
                    secret_value = manager.get_secret(field_name)
                    if secret_value:
                        # Handle SecretStr fields
                        if field.type_ == SecretStr or (hasattr(field.type_, '__origin__') and
                                                      field.type_.__origin__ == Optional and
                                                      field.type_.__args__[0] == SecretStr):
                            source_data[field_name] = SecretStr(secret_value)
                        else:
                            source_data[field_name] = secret_value

            return source_data

        return settings_source


# Global secret manager instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Get or create global secret manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def get_secret(key: str) -> Optional[str]:
    """Convenience function to get secret value."""
    manager = get_secret_manager()
    return manager.get_secret(key)
