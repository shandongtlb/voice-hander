from intranet_assistant.core.config import settings_from_dict


def test_settings_from_minimal_dict():
    settings = settings_from_dict({"llm": {"model": "local-model"}})
    assert settings.llm.model == "local-model"
    assert settings.tools.shell.enabled is True
