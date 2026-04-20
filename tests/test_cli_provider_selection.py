import unittest
import os
from unittest.mock import patch

from cli.utils import select_llm_provider


class _DummyPrompt:
    def __init__(self, response):
        self._response = response

    def ask(self):
        return self._response


class CliProviderSelectionTests(unittest.TestCase):
    def test_openai_provider_uses_env_gateway_url_when_present(self):
        captured = {}

        def fake_select(*args, **kwargs):
            captured["choices"] = kwargs["choices"]
            return _DummyPrompt(("openai", "unused"))

        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://gateway.example/v1"}, clear=False):
            with patch("cli.utils.questionary.select", side_effect=fake_select):
                select_llm_provider()

        openai_choice = next(
            choice for choice in captured["choices"] if choice.value[0] == "openai"
        )
        self.assertEqual(
            openai_choice.value[1],
            "https://gateway.example/v1",
        )

    def test_openai_provider_falls_back_to_official_url(self):
        captured = {}

        def fake_select(*args, **kwargs):
            captured["choices"] = kwargs["choices"]
            return _DummyPrompt(("openai", "unused"))

        with patch.dict(os.environ, {}, clear=True):
            with patch("cli.utils.questionary.select", side_effect=fake_select):
                select_llm_provider()

        openai_choice = next(
            choice for choice in captured["choices"] if choice.value[0] == "openai"
        )
        self.assertEqual(
            openai_choice.value[1],
            "https://api.openai.com/v1",
        )

if __name__ == "__main__":
    unittest.main()
