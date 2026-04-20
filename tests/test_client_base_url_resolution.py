import os
import unittest
from unittest.mock import patch

from tradingagents.llm_clients.azure_client import AzureOpenAIClient
from tradingagents.llm_clients.openai_client import OpenAIClient


class ClientBaseUrlResolutionTests(unittest.TestCase):
    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_openai_client_uses_responses_api_for_official_openai(self, mock_chat):
        client = OpenAIClient(
            "gpt-5.4",
            provider="openai",
            base_url="https://api.openai.com/v1",
        )
        client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertTrue(call_kwargs["use_responses_api"])

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_openai_client_uses_chat_completions_for_custom_gateway(self, mock_chat):
        client = OpenAIClient(
            "gpt-5.4",
            provider="openai",
            base_url="https://gateway.example/v1",
        )
        client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertFalse(call_kwargs["use_responses_api"])

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_openai_client_can_force_responses_api_with_env_override(self, mock_chat):
        with patch.dict(
            os.environ,
            {"OPENAI_API_MODE": "responses"},
            clear=False,
        ):
            client = OpenAIClient(
                "gpt-5.4",
                provider="openai",
                base_url="https://gateway.example/v1",
            )
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertTrue(call_kwargs["use_responses_api"])

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_openai_client_can_force_chat_completions_with_env_override(self, mock_chat):
        with patch.dict(
            os.environ,
            {"OPENAI_API_MODE": "chat_completions"},
            clear=False,
        ):
            client = OpenAIClient(
                "gpt-5.4",
                provider="openai",
                base_url="https://api.openai.com/v1",
            )
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertFalse(call_kwargs["use_responses_api"])

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_xai_client_uses_env_base_url_when_no_explicit_override(self, mock_chat):
        with patch.dict(
            os.environ,
            {
                "XAI_BASE_URL": "https://xai-gateway.example/v1",
                "XAI_API_KEY": "test-xai-key",
            },
            clear=False,
        ):
            client = OpenAIClient("grok-4", provider="xai")
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["base_url"], "https://xai-gateway.example/v1")
        self.assertEqual(call_kwargs["api_key"], "test-xai-key")

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_xai_client_prefers_explicit_base_url_over_env(self, mock_chat):
        with patch.dict(
            os.environ,
            {
                "XAI_BASE_URL": "https://xai-gateway.example/v1",
                "XAI_API_KEY": "test-xai-key",
            },
            clear=False,
        ):
            client = OpenAIClient(
                "grok-4",
                base_url="https://explicit.example/v1",
                provider="xai",
            )
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["base_url"], "https://explicit.example/v1")

    @patch("tradingagents.llm_clients.azure_client.NormalizedAzureChatOpenAI")
    def test_azure_client_uses_endpoint_env_when_no_explicit_override(self, mock_chat):
        with patch.dict(
            os.environ,
            {"AZURE_OPENAI_ENDPOINT": "https://azure.example.com/"},
            clear=False,
        ):
            client = AzureOpenAIClient("deployment-name")
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(
            call_kwargs["azure_endpoint"],
            "https://azure.example.com/",
        )

    @patch("tradingagents.llm_clients.azure_client.NormalizedAzureChatOpenAI")
    def test_azure_client_prefers_explicit_base_url_over_env(self, mock_chat):
        with patch.dict(
            os.environ,
            {"AZURE_OPENAI_ENDPOINT": "https://azure.example.com/"},
            clear=False,
        ):
            client = AzureOpenAIClient(
                "deployment-name",
                base_url="https://explicit-azure.example.com/",
            )
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(
            call_kwargs["azure_endpoint"],
            "https://explicit-azure.example.com/",
        )


if __name__ == "__main__":
    unittest.main()
