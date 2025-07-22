"""
Real LLM integration for the Hedwig system.

This module provides integration with OpenAI's API to replace the mock
implementation with real language model capabilities.
"""

import os
from typing import Optional, Callable, Dict, Any, List
from functools import lru_cache

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, try manual loading
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
from hedwig.core.exceptions import LLMIntegrationError


class LLMClient:
    """
    LLM client for interfacing with OpenAI API.
    
    Handles API calls, error handling, token management, and response processing.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenAI API key (if not provided, uses environment/config)
            model: Model to use for completions
        """
        self.logger = get_logger("hedwig.core.llm")
        self.model = model
        
        # Check if OpenAI is available
        if OpenAI is None:
            raise LLMIntegrationError(
                "OpenAI package not installed. Install with: pip install openai>=1.0.0",
                "LLMClient"
            )
        
        # Get API key from parameter, environment, or config
        self.api_key = api_key or self._get_api_key()
        
        if not self.api_key:
            raise LLMIntegrationError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or configure in settings.",
                "LLMClient"
            )
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.logger.info(f"Initialized OpenAI client with model: {self.model}")
        except Exception as e:
            raise LLMIntegrationError(f"Failed to initialize OpenAI client: {str(e)}", "LLMClient")
        
        # Track usage stats
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "errors": 0
        }
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables or config."""
        # Try environment variable first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Try config
        try:
            config = get_config()
            return getattr(config.llm, 'api_key', None)
        except Exception:
            return None
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate chat completion using OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Randomness in responses (0.0-1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters for OpenAI API
            
        Returns:
            Generated response text
            
        Raises:
            LLMIntegrationError: If API call fails
        """
        try:
            self.stats["total_requests"] += 1
            
            # Prepare parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Add any additional parameters
            params.update(kwargs)
            
            self.logger.debug(f"Making OpenAI API call with model {self.model}")
            
            # Make API call
            response = self.client.chat.completions.create(**params)
            
            # Extract response
            content = response.choices[0].message.content
            
            # Update stats
            if hasattr(response, 'usage') and response.usage:
                self.stats["total_tokens"] += response.usage.total_tokens
            
            self.logger.debug(f"Received response ({len(content)} characters)")
            return content
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"OpenAI API call failed: {str(e)}")
            raise LLMIntegrationError(f"OpenAI API call failed: {str(e)}", "LLMClient")
    
    def simple_completion(self, prompt: str, **kwargs) -> str:
        """
        Generate simple completion from a single prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated response
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.stats.copy()


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client(force_refresh: bool = False) -> LLMClient:
    """
    Get global LLM client instance.
    
    Args:
        force_refresh: Force creation of new client
        
    Returns:
        LLM client instance
    """
    global _llm_client
    
    if _llm_client is None or force_refresh:
        config = get_config()
        
        # Get model from config or use default
        model = getattr(config.llm, 'model', 'gpt-4-turbo-preview')
        
        _llm_client = LLMClient(model=model)
    
    return _llm_client


def get_llm_callback() -> Callable[[str], str]:
    """
    Get LLM callback function for use with agents and tools.
    
    Returns:
        Function that takes a prompt and returns LLM response
    """
    client = get_llm_client()
    
    def llm_callback(prompt: str) -> str:
        """
        LLM callback function.
        
        Args:
            prompt: Input prompt
            
        Returns:
            LLM response
        """
        try:
            return client.simple_completion(prompt)
        except Exception as e:
            logger = get_logger("hedwig.core.llm.callback")
            logger.error(f"LLM callback failed: {str(e)}")
            # Return a fallback response instead of failing completely
            return "I apologize, but I'm having trouble processing your request right now. Please try again."
    
    return llm_callback


def create_agent_llm_callback(system_prompt: Optional[str] = None) -> Callable[[str], str]:
    """
    Create an LLM callback with a system prompt for agent use.
    
    Args:
        system_prompt: System prompt to include with all requests
        
    Returns:
        LLM callback function with system prompt
    """
    client = get_llm_client()
    
    def agent_llm_callback(user_prompt: str) -> str:
        """
        Agent LLM callback with system prompt.
        
        Args:
            user_prompt: User/agent prompt
            
        Returns:
            LLM response
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": user_prompt})
            
            return client.chat_completion(messages)
            
        except Exception as e:
            logger = get_logger("hedwig.core.llm.agent_callback")
            logger.error(f"Agent LLM callback failed: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again."
    
    return agent_llm_callback


# Compatibility function to replace mock
def get_mock_llm_callback() -> Callable[[str], str]:
    """
    Compatibility function to replace mock implementation.
    
    Returns:
        Real LLM callback (no longer mock)
    """
    logger = get_logger("hedwig.core.llm.compatibility")
    logger.info("Using real OpenAI LLM integration (no longer mock)")
    
    return get_llm_callback()


@lru_cache(maxsize=128)
def cached_llm_call(prompt: str, temperature: float = 0.7) -> str:
    """
    Cached LLM call for repeated prompts.
    
    Args:
        prompt: Input prompt
        temperature: Response randomness
        
    Returns:
        LLM response (cached for identical prompts)
    """
    client = get_llm_client()
    return client.simple_completion(prompt, temperature=temperature)


def validate_llm_connection() -> bool:
    """
    Validate that LLM connection is working.
    
    Returns:
        True if connection is successful
    """
    try:
        client = get_llm_client()
        # Simple test call
        response = client.simple_completion("Test connection. Reply with 'OK'.", max_tokens=10)
        return "ok" in response.lower()
    except Exception as e:
        logger = get_logger("hedwig.core.llm.validation")
        logger.error(f"LLM connection validation failed: {str(e)}")
        return False