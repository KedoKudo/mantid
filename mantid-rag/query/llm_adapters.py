"""
LLM adapter interface for RAG integration.

Provides a unified interface for different LLMs (Qwen, Llama, GPT, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """Base class for LLM adapters."""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024, 
                temperature: float = 0.7, **kwargs) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        pass


class QwenAdapter(LLMAdapter):
    """Adapter for Qwen models (Qwen2.5, Qwen3, etc.)."""
    
    def __init__(self, model_path: str, device_map: str = "auto", 
                 torch_dtype: str = "auto"):
        """
        Initialize Qwen adapter.
        
        Args:
            model_path: Path to model or Hugging Face model ID
            device_map: Device mapping strategy
            torch_dtype: Torch dtype for model
        """
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            logger.info(f"Loading Qwen model: {model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map=device_map,
                torch_dtype=torch_dtype
            )
            self.model_path = model_path
            logger.info("Qwen model loaded successfully")
            
        except ImportError:
            raise ImportError("transformers library required for Qwen adapter. "
                            "Install with: pixi add transformers pytorch")
    
    def generate(self, prompt: str, max_tokens: int = 1024, 
                temperature: float = 0.7, **kwargs) -> str:
        """Generate text using Qwen model."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=kwargs.get('top_p', 0.9),
            do_sample=temperature > 0,
            **kwargs
        )
        
        # Decode and remove input prompt
        full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Try to extract only the generated part
        if prompt in full_text:
            generated = full_text.split(prompt)[-1]
        else:
            generated = full_text
        
        return generated.strip()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Qwen model information."""
        return {
            'model_type': 'qwen',
            'model_path': self.model_path,
            'device': str(self.model.device),
            'dtype': str(self.model.dtype)
        }
    
    @staticmethod
    def format_mantid_prompt(context: str, question: str, system_message: Optional[str] = None) -> str:
        """
        Format prompt for Qwen with Mantid context.
        
        Args:
            context: Retrieved algorithm documentation
            question: User's question
            system_message: Optional system message
            
        Returns:
            Formatted prompt
        """
        if system_message is None:
            system_message = (
                "You are a helpful assistant for Mantid, a framework for neutron and muon data analysis. "
                "Use the provided algorithm documentation to answer questions accurately. "
                "When generating code, ensure you use correct algorithm names and properties."
            )
        
        prompt = f"""<|im_start|>system
{system_message}
<|im_end|>
<|im_start|>user
Algorithm Documentation:
{context}

Question: {question}
<|im_end|>
<|im_start|>assistant
"""
        return prompt


class OllamaAdapter(LLMAdapter):
    """Adapter for Ollama-served models."""
    
    def __init__(self, model_name: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama adapter.
        
        Args:
            model_name: Name of Ollama model
            base_url: Ollama server URL
        """
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests library required for Ollama adapter")
        
        self.model_name = model_name
        self.base_url = base_url
        logger.info(f"Ollama adapter initialized: {model_name} at {base_url}")
    
    def generate(self, prompt: str, max_tokens: int = 1024, 
                temperature: float = 0.7, **kwargs) -> str:
        """Generate text using Ollama API."""
        response = self.requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    **kwargs
                }
            }
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama request failed: {response.text}")
        
        return response.json()['response']
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information."""
        return {
            'model_type': 'ollama',
            'model_name': self.model_name,
            'base_url': self.base_url
        }


class VLLMAdapter(LLMAdapter):
    """Adapter for vLLM-served models (for high-performance inference)."""
    
    def __init__(self, base_url: str = "http://localhost:8000", model_name: Optional[str] = None):
        """
        Initialize vLLM adapter.
        
        Args:
            base_url: vLLM server URL
            model_name: Model name (optional)
        """
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests library required for vLLM adapter")
        
        self.base_url = base_url
        self.model_name = model_name
        logger.info(f"vLLM adapter initialized at {base_url}")
    
    def generate(self, prompt: str, max_tokens: int = 1024, 
                temperature: float = 0.7, **kwargs) -> str:
        """Generate text using vLLM API."""
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": kwargs.get('top_p', 0.9),
            **kwargs
        }
        
        if self.model_name:
            payload["model"] = self.model_name
        
        response = self.requests.post(
            f"{self.base_url}/generate",
            json=payload
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"vLLM request failed: {response.text}")
        
        return response.json()['text'][0]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get vLLM model information."""
        return {
            'model_type': 'vllm',
            'base_url': self.base_url,
            'model_name': self.model_name
        }


# Example usage function
def create_mantid_rag_pipeline(retriever, llm_adapter: LLMAdapter):
    """
    Create a complete RAG pipeline for Mantid.
    
    Args:
        retriever: MantidRAGRetriever instance
        llm_adapter: LLM adapter instance
        
    Returns:
        Function that takes a question and returns an answer
    """
    from .context_builder import ContextBuilder
    
    context_builder = ContextBuilder()
    
    def query(question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Query the Mantid RAG system.
        
        Args:
            question: User's question
            top_k: Number of algorithms to retrieve
            
        Returns:
            Dictionary with answer and sources
        """
        # Retrieve relevant algorithms
        algorithms = retriever.search(question, top_k=top_k)
        
        # Build context
        context = context_builder.build_context(algorithms)
        
        # Format prompt (using Qwen format as default)
        if isinstance(llm_adapter, QwenAdapter):
            prompt = llm_adapter.format_mantid_prompt(context, question)
        else:
            # Generic format
            prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        
        # Generate answer
        answer = llm_adapter.generate(prompt)
        
        return {
            'answer': answer,
            'sources': algorithms,
            'context': context
        }
    
    return query
