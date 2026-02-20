"""Tests for the config module."""

import pytest

from tuya_agent.config import TuyaConfig


class TestTuyaConfig:
    def test_base_url_for_valid_regions(self):
        for region, expected_host in [
            ("us", "tuyaus.com"),
            ("eu", "tuyaeu.com"),
            ("cn", "tuyacn.com"),
            ("in", "tuyain.com"),
        ]:
            cfg = TuyaConfig(access_id="id", access_secret="sec", api_region=region)
            assert expected_host in cfg.base_url

    def test_base_url_raises_for_invalid_region(self):
        cfg = TuyaConfig(access_id="id", access_secret="sec", api_region="mars")
        with pytest.raises(ValueError, match="Unknown region"):
            _ = cfg.base_url

    def test_pulsar_url_for_valid_region(self):
        cfg = TuyaConfig(access_id="id", access_secret="sec", api_region="us")
        assert "mqe.tuyaus.com" in cfg.pulsar_url

    def test_pulsar_url_raises_for_unsupported_region(self):
        cfg = TuyaConfig(access_id="id", access_secret="sec", api_region="us-e")
        with pytest.raises(ValueError, match="No Pulsar endpoint"):
            _ = cfg.pulsar_url
