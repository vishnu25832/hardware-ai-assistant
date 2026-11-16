
import sys
from types import ModuleType, SimpleNamespace

from ai import assistant
from hardware import inspector


def test_empty_question():
    assert assistant.ask_assistant("") == "Please enter a question."


def test_whitespace_question():
    assert assistant.ask_assistant("   ") == "Please enter a question."


def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "")
    monkeypatch.setattr(assistant, "initialization_error", None)

    result = assistant.ask_assistant("What CPU do I have?")

    assert "API key is missing" in result


def test_assistant_not_initialized(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "chat", None)
    monkeypatch.setattr(assistant, "initialization_error", None)

    result = assistant.ask_assistant("What CPU do I have?")

    assert result == "Gemini assistant is not initialized."


def test_initialization_error(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(
        assistant,
        "initialization_error",
        "Test initialization error"
    )

    result = assistant.ask_assistant("What CPU do I have?")

    assert result == "Test initialization error"


def test_successful_assistant_response(monkeypatch):
    class FakeChat:
        def send_message(self, question):
            return SimpleNamespace(
                text="Your CPU is an Intel processor."
            )

    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "initialization_error", None)
    monkeypatch.setattr(assistant, "chat", FakeChat())

    result = assistant.ask_assistant("What CPU do I have?")

    assert result == "Your CPU is an Intel processor."


def test_empty_assistant_response(monkeypatch):
    class FakeChat:
        def send_message(self, question):
            return SimpleNamespace(text=None)

    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "initialization_error", None)
    monkeypatch.setattr(assistant, "chat", FakeChat())

    result = assistant.ask_assistant("What CPU do I have?")

    assert result == "The AI assistant returned an empty response."


def test_quota_error():
    result = assistant.classify_api_error(
        Exception("RESOURCE_EXHAUSTED: quota exceeded, 429")
    )

    assert "quota exceeded" in result.lower()


def test_invalid_api_key_error():
    result = assistant.classify_api_error(
        Exception("API_KEY_INVALID: invalid API key")
    )

    assert "authentication failed" in result.lower()


def test_permission_error():
    result = assistant.classify_api_error(
        Exception("PERMISSION_DENIED: 403")
    )

    assert "access denied" in result.lower()


def test_network_error():
    result = assistant.classify_api_error(
        Exception("Connection error: network unavailable")
    )

    assert "unable to connect" in result.lower()


def test_timeout_error():
    result = assistant.classify_api_error(
        Exception("Request timed out")
    )

    assert "timed out" in result.lower()


def test_unknown_api_error():
    result = assistant.classify_api_error(
        Exception("Unexpected server response")
    )

    assert "Gemini API request failed" in result


def test_assistant_handles_api_exception(monkeypatch):
    class FakeChat:
        def send_message(self, question):
            raise Exception("RESOURCE_EXHAUSTED: quota exceeded")

    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "initialization_error", None)
    monkeypatch.setattr(assistant, "chat", FakeChat())

    result = assistant.ask_assistant("What CPU do I have?")

    assert "quota exceeded" in result.lower()


def test_model_not_found_error():
    result = assistant.classify_api_error(
        Exception("Model not found: 404")
    )

    assert "model or resource was not found" in result.lower()


def test_gemini_receives_only_approved_inspection_tools(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chats = self

        def create(self, **kwargs):
            captured["chat_config"] = kwargs["config"]
            return SimpleNamespace(
                send_message=lambda question: SimpleNamespace(
                    text="Test response"
                )
            )

    class FakeHttpOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    fake_genai = ModuleType("google.genai")
    fake_genai.Client = FakeClient

    fake_types = ModuleType("google.genai.types")
    fake_types.HttpOptions = FakeHttpOptions
    fake_types.GenerateContentConfig = FakeGenerateContentConfig

    fake_google = ModuleType("google")
    fake_google.__path__ = []
    fake_google.genai = fake_genai

    fake_genai.__path__ = []
    fake_genai.types = fake_types

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "MODEL", "test-model")

    assistant.initialize_assistant()

    assert assistant.initialization_error is None
    assert assistant.chat is not None

    configured_tools = captured["chat_config"].tools

    expected_tools = [
        inspector.get_cpu_info,
        inspector.get_memory_info,
        inspector.get_memory_slot_info,
        inspector.get_storage_info,
        inspector.get_gpu_info,
        inspector.get_os_info
    ]

    assert configured_tools == expected_tools
    assert inspector.get_hardware_report not in configured_tools
    assert inspector.run_command not in configured_tools
