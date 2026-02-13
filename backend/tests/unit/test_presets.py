import pytest

from app.data.presets import get_preset, list_presets


class TestGetPreset:
    def test_get_kospi10(self):
        preset = get_preset("kospi10")
        assert preset.name == "kospi10"
        assert preset.market == "KR"
        assert len(preset.symbols) == 10
        assert "005930" in preset.symbols

    def test_get_mag7(self):
        preset = get_preset("mag7")
        assert preset.name == "mag7"
        assert preset.market == "US"
        assert len(preset.symbols) == 7
        assert "AAPL" in preset.symbols

    def test_case_insensitive(self):
        p1 = get_preset("KOSPI10")
        p2 = get_preset("Kospi10")
        p3 = get_preset("kospi10")
        assert p1.name == p2.name == p3.name

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent")


class TestListPresets:
    def test_returns_all_presets(self):
        presets = list_presets()
        assert len(presets) >= 3
        names = [p.name for p in presets]
        assert "kospi10" in names
        assert "kospi20" in names
        assert "mag7" in names

    def test_kospi20_contains_kospi10(self):
        k10 = get_preset("kospi10")
        k20 = get_preset("kospi20")
        for symbol in k10.symbols:
            assert symbol in k20.symbols
