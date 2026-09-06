"""LLM client for Nebius Token Factory (OpenAI-compatible)."""

import os
from typing import Optional, List, Dict, Any
from openai import OpenAI


class NebiusClient:
    """Client for Nebius Token Factory API (OpenAI-compatible)."""
    
    SYSTEM_PROMPT = """You are a personal habit tracking assistant. You help users understand their habits, 
provide insights, and offer encouragement.

IMPORTANT: You are NOT a medical professional. You do NOT provide medical advice, diagnose conditions, 
or prescribe treatments. For any health concerns, users should consult qualified healthcare professionals.

Your role is to:
- Help users log and track their habits
- Provide data-based observations about patterns
- Offer general motivation and support
- Answer questions about their habit data

Always maintain a supportive, non-judgmental tone."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    ):
        """Initialize Nebius Token Factory client.
        
        Args:
            api_key: Nebius API key (defaults to NEBIUS_API_KEY env var)
            model: Model name (defaults to NEMOTRON_MODEL env var or nvidia/nemotron-3-super-120b-a12b)
            base_url: API base URL
        """
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        self.model = model or os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-super-120b-a12b")
        self.base_url = base_url
        
        if not self.api_key:
            raise ValueError(
                "Nebius API key required. Set NEBIUS_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def ping(self) -> Dict[str, Any]:
        """Test the connection and model availability."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'pong' if you can hear me."}
                ],
                max_tokens=10
            )
            
            return {
                "status": "success",
                "model": self.model,
                "response": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def ask(
        self,
        question: str,
        context: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """Ask a question with optional memory context.
        
        Args:
            question: User question
            context: Optional memory context to include
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Model response text
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        if context:
            messages.append({
                "role": "system",
                "content": f"Memory context:\n{context}"
            })
        
        messages.append({"role": "user", "content": question})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
