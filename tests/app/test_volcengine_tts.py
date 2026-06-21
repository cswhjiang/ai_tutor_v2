import pytest

from src.local_manim_voiceover_services.volcengine_tts import (
    VolcengineTTSService,
    _remove_voiceover_bookmarks,
)


def test_remove_voiceover_bookmarks():
    assert _remove_voiceover_bookmarks('你好<bookmark mark="a"/>世界') == "你好世界"


def test_has_credentials_reads_environment(monkeypatch):
    monkeypatch.delenv("VOLCENGINE_APPID", raising=False)
    monkeypatch.delenv("VOLCENGINE_ACCESS_TOKEN", raising=False)
    assert VolcengineTTSService.has_credentials() is False

    monkeypatch.setenv("VOLCENGINE_APPID", "app")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "token")
    assert VolcengineTTSService.has_credentials() is True


def test_init_requires_credentials(monkeypatch):
    monkeypatch.delenv("VOLCENGINE_APPID", raising=False)
    monkeypatch.delenv("VOLCENGINE_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError):
        VolcengineTTSService()
