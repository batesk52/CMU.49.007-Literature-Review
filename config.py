"""
Configuration Management Module

This module provides centralized configuration management for the Knowledge Base system.
It handles environment variables, default values, and configuration validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for API providers."""
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.gemini_api_key:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            self.anthropic_api_key = self.claude_api_key


@dataclass
class ZoteroConfig:
    """Configuration for Zotero integration."""
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    library_type: str = "user"
    
    def __post_init__(self):
        """Load Zotero config from environment if not provided."""
        if not self.api_key:
            self.api_key = os.getenv("ZOTERO_API_KEY")
        if not self.user_id:
            self.user_id = os.getenv("ZOTERO_USER_ID")
        if not self.library_type:
            self.library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")


@dataclass
class NotionConfig:
    """Configuration for Notion integration."""
    token: Optional[str] = None
    database_id: Optional[str] = None
    
    def __post_init__(self):
        """Load Notion config from environment if not provided."""
        if not self.token:
            self.token = os.getenv("NOTION_TOKEN")
        if not self.database_id:
            self.database_id = os.getenv("NOTION_DATABASE_ID")


@dataclass
class PathConfig:
    """Configuration for file paths and directories."""
    base_directory: Path = Path(".")
    data_directory: Path = Path("data")
    knowledge_base_path: Path = Path("data/knowledge_base.json")
    embeddings_cache_path: Path = Path("data/embeddings_cache.json")
    audio_folder_path: Path = Path("./audio_files")
    audio_state_file: Path = Path("data/audio_processing_state.json")
    
    def __post_init__(self):
        """Convert string paths to Path objects and load from environment."""
        # Convert all attributes to Path objects
        for attr, value in self.__dict__.items():
            if isinstance(value, str):
                setattr(self, attr, Path(value))
        
        # Load from environment
        audio_env = os.getenv("AUDIO_FOLDER_PATH")
        if audio_env:
            self.audio_folder_path = Path(audio_env)
        
        # Ensure data directory exists
        self.data_directory.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessingConfig:
    """Configuration for processing behavior."""
    # API retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 30
    
    # Content processing
    max_content_length: int = 15000  # Characters for summarization
    chunk_size_mb: int = 25  # Max file size in MB for audio processing
    
    # Search settings
    default_top_k: int = 5
    default_similarity_threshold: float = 0.7
    
    # Logging
    verbose: bool = False
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration class that combines all config sections."""
    api: APIConfig = field(default_factory=APIConfig)
    zotero: ZoteroConfig = field(default_factory=ZoteroConfig)
    notion: NotionConfig = field(default_factory=NotionConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    def __post_init__(self):
        """Set up logging based on configuration."""
        log_level = getattr(logging, self.processing.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the configuration and return validation results.
        
        Returns:
            Dict[str, Any]: Validation results with errors and warnings
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "available_providers": []
        }
        
        # Check for at least one API key
        if not any([self.api.openai_api_key, self.api.gemini_api_key, self.api.claude_api_key]):
            results["errors"].append("No AI provider API key found. Set OPENAI_API_KEY, GEMINI_API_KEY, or CLAUDE_API_KEY.")
            results["valid"] = False
        else:
            if self.api.openai_api_key:
                results["available_providers"].append("openai")
            if self.api.gemini_api_key:
                results["available_providers"].append("gemini")
            if self.api.claude_api_key:
                results["available_providers"].append("claude")
        
        # Check optional integrations
        if not self.zotero.api_key or not self.zotero.user_id:
            results["warnings"].append("Zotero integration not configured. Set ZOTERO_API_KEY and ZOTERO_USER_ID to enable.")
        
        if not self.notion.token or not self.notion.database_id:
            results["warnings"].append("Notion integration not configured. Set NOTION_TOKEN and NOTION_DATABASE_ID to enable.")
        
        # Check paths
        if not self.paths.base_directory.exists():
            results["errors"].append(f"Base directory does not exist: {self.paths.base_directory}")
            results["valid"] = False
        
        return results
    
    def save_to_file(self, filepath: str = "config.json") -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            filepath (str): Path to save the configuration file
        """
        config_dict = {
            "api": {
                "openai_model": self.api.openai_model,
                "openai_embedding_model": self.api.openai_embedding_model,
            },
            "zotero": {
                "library_type": self.zotero.library_type
            },
            "paths": {
                "base_directory": str(self.paths.base_directory),
                "data_directory": str(self.paths.data_directory),
                "knowledge_base_path": str(self.paths.knowledge_base_path),
                "embeddings_cache_path": str(self.paths.embeddings_cache_path),
                "audio_folder_path": str(self.paths.audio_folder_path),
                "audio_state_file": str(self.paths.audio_state_file)
            },
            "processing": {
                "max_retries": self.processing.max_retries,
                "retry_delay": self.processing.retry_delay,
                "request_timeout": self.processing.request_timeout,
                "max_content_length": self.processing.max_content_length,
                "chunk_size_mb": self.processing.chunk_size_mb,
                "default_top_k": self.processing.default_top_k,
                "default_similarity_threshold": self.processing.default_similarity_threshold,
                "verbose": self.processing.verbose,
                "log_level": self.processing.log_level
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str = "config.json") -> "Config":
        """
        Load configuration from a JSON file.
        
        Args:
            filepath (str): Path to the configuration file
            
        Returns:
            Config: Loaded configuration object
        """
        if not os.path.exists(filepath):
            logger.warning(f"Configuration file {filepath} not found. Using defaults.")
            return cls()
        
        try:
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
            
            # Create config with loaded values
            config = cls()
            
            # Update API config
            if "api" in config_dict:
                for key, value in config_dict["api"].items():
                    if hasattr(config.api, key):
                        setattr(config.api, key, value)
            
            # Update Zotero config
            if "zotero" in config_dict:
                for key, value in config_dict["zotero"].items():
                    if hasattr(config.zotero, key):
                        setattr(config.zotero, key, value)
            
            # Update paths
            if "paths" in config_dict:
                for key, value in config_dict["paths"].items():
                    if hasattr(config.paths, key):
                        setattr(config.paths, key, Path(value))
            
            # Update processing config
            if "processing" in config_dict:
                for key, value in config_dict["processing"].items():
                    if hasattr(config.processing, key):
                        setattr(config.processing, key, value)
            
            logger.info(f"Configuration loaded from {filepath}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {e}")
            return cls()


# Global configuration instance
_config = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config: Global configuration object
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """
    Set the global configuration instance.
    
    Args:
        config (Config): Configuration object to set globally
    """
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration to default."""
    global _config
    _config = Config()


# Convenience functions for common config access
def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from configuration."""
    return get_config().api.openai_api_key


def get_available_providers() -> List[str]:
    """Get list of available AI providers based on configured API keys."""
    config = get_config()
    providers = []
    if config.api.openai_api_key:
        providers.append("openai")
    if config.api.gemini_api_key:
        providers.append("gemini")
    if config.api.claude_api_key:
        providers.append("claude")
    return providers


def main():
    """Command-line interface for configuration management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Base Configuration Manager")
    parser.add_argument("command", choices=["validate", "save", "show"], 
                       help="Command to execute")
    parser.add_argument("--config-file", default="config.json",
                       help="Configuration file path")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = Config.load_from_file(args.config_file)
    
    if args.command == "validate":
        results = config.validate()
        
        print("Configuration Validation Results")
        print("=" * 40)
        print(f"Valid: {'✅ Yes' if results['valid'] else '❌ No'}")
        
        if results['available_providers']:
            print(f"\nAvailable AI Providers:")
            for provider in results['available_providers']:
                print(f"  - {provider}")
        
        if results['errors']:
            print("\n❌ Errors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results['warnings']:
            print("\n⚠️  Warnings:")
            for warning in results['warnings']:
                print(f"  - {warning}")
        
        if results['valid'] and not results['warnings']:
            print("\n✅ Configuration is valid and complete!")
    
    elif args.command == "save":
        config.save_to_file(args.config_file)
        print(f"✅ Configuration saved to {args.config_file}")
    
    elif args.command == "show":
        print("Current Configuration")
        print("=" * 40)
        print(f"\nAPI Configuration:")
        print(f"  OpenAI API Key: {'✅ Set' if config.api.openai_api_key else '❌ Not set'}")
        print(f"  OpenAI Model: {config.api.openai_model}")
        print(f"  Embedding Model: {config.api.openai_embedding_model}")
        print(f"  Gemini API Key: {'✅ Set' if config.api.gemini_api_key else '❌ Not set'}")
        print(f"  Claude API Key: {'✅ Set' if config.api.claude_api_key else '❌ Not set'}")
        
        print(f"\nZotero Configuration:")
        print(f"  API Key: {'✅ Set' if config.zotero.api_key else '❌ Not set'}")
        print(f"  User ID: {'✅ Set' if config.zotero.user_id else '❌ Not set'}")
        print(f"  Library Type: {config.zotero.library_type}")
        
        print(f"\nNotion Configuration:")
        print(f"  Token: {'✅ Set' if config.notion.token else '❌ Not set'}")
        print(f"  Database ID: {'✅ Set' if config.notion.database_id else '❌ Not set'}")
        
        print(f"\nPath Configuration:")
        print(f"  Base Directory: {config.paths.base_directory}")
        print(f"  Data Directory: {config.paths.data_directory}")
        print(f"  Knowledge Base: {config.paths.knowledge_base_path}")
        print(f"  Embeddings Cache: {config.paths.embeddings_cache_path}")
        
        print(f"\nProcessing Configuration:")
        print(f"  Max Retries: {config.processing.max_retries}")
        print(f"  Default Top K: {config.processing.default_top_k}")
        print(f"  Similarity Threshold: {config.processing.default_similarity_threshold}")
        print(f"  Log Level: {config.processing.log_level}")


if __name__ == "__main__":
    main()