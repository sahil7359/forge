def test_agent_imports():
    from forge_agent import config, push  # noqa: F401

    assert config.settings.model
