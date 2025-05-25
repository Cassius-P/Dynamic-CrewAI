"""Tests for LLM wrapper functionality."""
import pytest
from unittest.mock import Mock, patch
from app.core.llm_wrapper import LLMWrapper, create_llm_from_provider
from app.models.llm_provider import LLMProvider


class TestLLMWrapper:
    """Test cases for LLM wrapper functionality."""

    @pytest.fixture
    def openai_provider(self):
        """Create a test OpenAI provider."""
        return LLMProvider(
            id=1,
            name="openai-test",
            provider_type="openai",
            model_name="gpt-3.5-turbo",
            api_key="test-key",
            temperature="0.7",
            max_tokens=1000,
            is_active=True
        )

    @pytest.fixture
    def anthropic_provider(self):
        """Create a test Anthropic provider."""
        return LLMProvider(
            id=2,
            name="anthropic-test",
            provider_type="anthropic",
            model_name="claude-3-haiku",
            api_key="test-key",
            temperature="0.5",
            max_tokens=2000,
            is_active=True
        )

    @pytest.fixture
    def ollama_provider(self):
        """Create a test Ollama provider."""
        return LLMProvider(
            id=3,
            name="ollama-test",
            provider_type="ollama",
            model_name="llama2",
            api_base="http://localhost:11434",
            temperature="0.3",
            is_active=True
        )

    @patch('app.core.llm_wrapper.LLM')
    def test_create_openai_llm(self, mock_llm, openai_provider):
        """Test creating OpenAI LLM from provider."""
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        llm = create_llm_from_provider(openai_provider)
        
        assert llm == mock_llm_instance
        mock_llm.assert_called_once_with(
            model="openai/gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000,
            api_key="test-key"
        )

    @patch('app.core.llm_wrapper.LLM')
    def test_create_anthropic_llm(self, mock_llm, anthropic_provider):
        """Test creating Anthropic LLM from provider."""
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        llm = create_llm_from_provider(anthropic_provider)
        
        assert llm == mock_llm_instance
        mock_llm.assert_called_once_with(
            model="anthropic/claude-3-haiku",
            temperature=0.5,
            max_tokens=2000,
            api_key="test-key"
        )

    @patch('app.core.llm_wrapper.LLM')
    def test_create_ollama_llm(self, mock_llm, ollama_provider):
        """Test creating Ollama LLM from provider."""
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        llm = create_llm_from_provider(ollama_provider)
        
        assert llm == mock_llm_instance
        mock_llm.assert_called_once_with(
            model="ollama/llama2",
            temperature=0.3,
            base_url="http://localhost:11434"
        )

    def test_create_llm_inactive_provider(self, openai_provider):
        """Test creating LLM with inactive provider."""
        openai_provider.is_active = False
        
        with pytest.raises(ValueError, match="Provider openai-test is not active"):
            create_llm_from_provider(openai_provider)

    def test_llm_wrapper_initialization(self):
        """Test LLMWrapper initialization."""
        wrapper = LLMWrapper()
        assert wrapper is not None

    def test_llm_wrapper_get_available_providers(self):
        """Test getting available LLM providers."""
        wrapper = LLMWrapper()
        providers = wrapper.get_available_providers()
        
        expected_providers = ["openai", "anthropic", "ollama"]
        assert providers == expected_providers

    @patch('app.core.llm_wrapper.create_llm_from_provider')
    def test_llm_wrapper_create_llm(self, mock_create_llm, openai_provider):
        """Test LLMWrapper create_llm method."""
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        
        wrapper = LLMWrapper()
        result = wrapper.create_llm(openai_provider)
        
        assert result == mock_llm
        mock_create_llm.assert_called_once_with(openai_provider)

    def test_temperature_conversion_string_to_float(self, openai_provider):
        """Test temperature conversion from string to float."""
        openai_provider.temperature = "0.8"
        
        with patch('app.core.llm_wrapper.LLM') as mock_llm:
            create_llm_from_provider(openai_provider)
            
            # Check that temperature was converted to float
            call_args = mock_llm.call_args[1]
            assert call_args['temperature'] == 0.8
            assert isinstance(call_args['temperature'], float)

    def test_temperature_none_handling(self, openai_provider):
        """Test handling of None temperature."""
        openai_provider.temperature = None
        
        with patch('app.core.llm_wrapper.LLM') as mock_llm:
            create_llm_from_provider(openai_provider)
            
            # Check that temperature defaults to 0.7
            call_args = mock_llm.call_args[1]
            assert call_args['temperature'] == 0.7

    def test_api_base_handling(self, anthropic_provider):
        """Test API base URL handling."""
        anthropic_provider.api_base = "https://custom.api.com"
        
        with patch('app.core.llm_wrapper.LLM') as mock_llm:
            create_llm_from_provider(anthropic_provider)
            
            # Check that base_url was set
            call_args = mock_llm.call_args[1]
            assert call_args['base_url'] == "https://custom.api.com"

    def test_config_parameters_handling(self, openai_provider):
        """Test handling of additional config parameters."""
        openai_provider.config = {
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            "stop": ["END"],
            "seed": 42,
            "invalid_param": "should_be_ignored"
        }
        
        with patch('app.core.llm_wrapper.LLM') as mock_llm:
            create_llm_from_provider(openai_provider)
            
            call_args = mock_llm.call_args[1]
            assert call_args['top_p'] == 0.9
            assert call_args['frequency_penalty'] == 0.1
            assert call_args['presence_penalty'] == 0.1
            assert call_args['stop'] == ["END"]
            assert call_args['seed'] == 42
            # Invalid param should not be included
            assert 'invalid_param' not in call_args

    def test_api_version_handling(self, openai_provider):
        """Test API version handling."""
        openai_provider.api_version = "v1"
        
        with patch('app.core.llm_wrapper.LLM') as mock_llm:
            create_llm_from_provider(openai_provider)
            
            call_args = mock_llm.call_args[1]
            assert call_args['api_version'] == "v1"
