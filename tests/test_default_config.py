import importlib
import os
import unittest
from unittest.mock import patch

import tradingagents.default_config as default_config


class DefaultConfigTests(unittest.TestCase):
    def test_resolve_provider_base_url_uses_openai_env_override(self):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://gateway.example/v1"}, clear=False):
            reloaded = importlib.reload(default_config)
            self.assertEqual(
                reloaded.resolve_provider_base_url("openai"),
                "https://gateway.example/v1",
            )

    def test_resolve_provider_base_url_falls_back_to_official_openai(self):
        with patch.dict(os.environ, {}, clear=True):
            reloaded = importlib.reload(default_config)
            self.assertEqual(
                reloaded.resolve_provider_base_url("openai"),
                "https://api.openai.com/v1",
            )

    def test_provider_base_url_uses_provider_specific_override(self):
        with patch.dict(os.environ, {"XAI_BASE_URL": "https://xai-gateway.example/v1"}, clear=False):
            reloaded = importlib.reload(default_config)
            self.assertEqual(
                reloaded.get_provider_base_url("xai"),
                "https://xai-gateway.example/v1",
            )

    def test_provider_base_url_falls_back_to_provider_default(self):
        with patch.dict(os.environ, {}, clear=True):
            reloaded = importlib.reload(default_config)
            self.assertEqual(
                reloaded.get_provider_base_url("deepseek"),
                "https://api.deepseek.com",
            )

    def test_provider_base_url_can_be_none_when_provider_has_no_default(self):
        with patch.dict(os.environ, {}, clear=True):
            reloaded = importlib.reload(default_config)
            self.assertIsNone(reloaded.get_provider_base_url("google"))

    def test_resolve_provider_base_url_prefers_explicit_config_value(self):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://gateway.example/v1"}, clear=False):
            reloaded = importlib.reload(default_config)
            self.assertEqual(
                reloaded.resolve_provider_base_url(
                    "openai",
                    "https://explicit.example/v1",
                ),
                "https://explicit.example/v1",
            )


if __name__ == "__main__":
    unittest.main()
