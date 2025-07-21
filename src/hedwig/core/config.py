"""
Configuration management for the Hedwig system.

Handles loading and managing application settings from environment
variables and configuration files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class SecurityConfig(BaseModel):
    """Security-related configuration."""
    
    confirmation_timeout: int = Field(default=10, description="Timeout for security confirmations in seconds")
    max_retries: int = Field(default=3, description="Maximum number of task retry attempts")
    enable_sandbox: bool = Field(default=False, description="Enable sandboxing for execution tools")
    high_risk_patterns: List[str] = Field(
        default_factory=lambda: ["rm", "mv", "dd", "mkfs", "format", "del", "deltree"],
        description="Command patterns that trigger high-risk warnings"
    )


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    
    provider: str = Field(default="openai", description="LLM provider (openai, anthropic)")
    model: str = Field(default="gpt-4", description="Model name to use")
    api_key: Optional[str] = Field(default=None, description="API key for the provider")
    base_url: Optional[str] = Field(default=None, description="Custom base URL for API")
    temperature: float = Field(default=0.1, description="Temperature for LLM generation")
    max_tokens: int = Field(default=2000, description="Maximum tokens for LLM responses")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v
    
    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        if v <= 0:
            raise ValueError("max_tokens must be positive")
        return v


class ArtifactConfig(BaseModel):
    """Artifact handling configuration."""
    
    artifacts_dir: str = Field(default="artifacts", description="Directory for storing artifacts")
    auto_open_enabled: bool = Field(default=True, description="Enable automatic artifact opening")
    max_artifact_size: int = Field(default=50 * 1024 * 1024, description="Maximum artifact size in bytes (50MB)")
    cleanup_days: int = Field(default=30, description="Days to keep old artifacts")


class HedwigConfig(BaseSettings):
    """Main configuration class for Hedwig application."""
    
    # Application settings
    data_dir: Path = Field(default_factory=lambda: Path.home() / '.hedwig', description="Base data directory")
    log_level: str = Field(default="INFO", description="Logging level")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    
    # Component configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    
    # GUI settings
    gui_enabled: bool = Field(default=True, description="Enable GUI interface")
    theme: str = Field(default="default", description="GUI theme")
    
    class Config:
        env_prefix = "HEDWIG_"
        env_nested_delimiter = "__"
        case_sensitive = False
    
    @classmethod
    def load_from_env(cls) -> "HedwigConfig":
        """Load configuration from environment variables."""
        return cls()
    
    @classmethod
    def load_from_file(cls, config_file: Path) -> "HedwigConfig":
        """Load configuration from a JSON/YAML file."""
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        if config_file.suffix.lower() == '.json':
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif config_file.suffix.lower() in ['.yaml', '.yml']:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
        
        return cls(**data)
    
    def save_to_file(self, config_file: Path) -> None:
        """Save configuration to a JSON file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(self.dict(), f, indent=2, default=str, ensure_ascii=False)
    
    def get_data_dir(self) -> Path:
        """Get the resolved data directory path."""
        return Path(self.data_dir).expanduser().resolve()
    
    def get_artifacts_dir(self) -> Path:
        """Get the artifacts directory path."""
        return self.get_data_dir() / self.artifacts.artifacts_dir
    
    def get_threads_dir(self) -> Path:
        """Get the threads directory path."""
        return self.get_data_dir() / 'threads'
    
    def get_logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self.get_data_dir() / 'logs'
    
    def setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        dirs = [
            self.get_data_dir(),
            self.get_artifacts_dir(),
            self.get_threads_dir(),
            self.get_logs_dir()
        ]
        
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Singleton configuration manager."""
    
    _instance: Optional[HedwigConfig] = None
    
    @classmethod
    def get_config(cls) -> HedwigConfig:
        """Get the current configuration instance."""
        if cls._instance is None:
            cls._instance = cls._load_default_config()
        return cls._instance
    
    @classmethod
    def set_config(cls, config: HedwigConfig) -> None:
        """Set a new configuration instance."""
        cls._instance = config
        config.setup_directories()
    
    @classmethod
    def load_config(cls, config_file: Optional[Path] = None) -> HedwigConfig:
        """Load configuration from file or environment."""
        if config_file and config_file.exists():
            config = HedwigConfig.load_from_file(config_file)
        else:
            config = HedwigConfig.load_from_env()
        
        cls.set_config(config)
        return config
    
    @classmethod
    def _load_default_config(cls) -> HedwigConfig:
        """Load default configuration."""
        # Try to load from standard locations
        possible_configs = [
            Path.cwd() / 'hedwig.json',
            Path.cwd() / 'config' / 'hedwig.json',
            Path.home() / '.hedwig' / 'config.json'
        ]
        
        for config_file in possible_configs:
            if config_file.exists():
                try:
                    return HedwigConfig.load_from_file(config_file)
                except Exception:
                    continue  # Try next file
        
        # Fall back to environment variables
        return HedwigConfig.load_from_env()
    
    @classmethod
    def create_default_config_file(cls, config_file: Path) -> None:
        """Create a default configuration file."""
        config = HedwigConfig()
        config.save_to_file(config_file)


def get_config() -> HedwigConfig:
    """Get the current Hedwig configuration."""
    return ConfigManager.get_config()


def load_config(config_file: Optional[Path] = None) -> HedwigConfig:
    """Load Hedwig configuration from file or environment."""
    return ConfigManager.load_config(config_file)