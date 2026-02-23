"""Tests for the TemplatesMixin."""

import pytest
import pytest_httpx

from tuya_agent.client import TuyaClient
from tuya_agent.config import TuyaConfig


def _config() -> TuyaConfig:
    return TuyaConfig(access_id="test_id", access_secret="test_secret", api_region="us")


def _token_response():
    return {
        "success": True,
        "result": {
            "access_token": "tok_abc",
            "refresh_token": "ref_xyz",
            "expire_time": 7200,
            "uid": "u123",
        },
    }


class TestTemplatesMixin:
    @pytest.mark.asyncio
    async def test_list_templates(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {
                    "total": 2,
                    "list": [
                        {"template_id": "tmpl1", "name": "Movie Night"},
                        {"template_id": "tmpl2", "name": "Good Morning"},
                    ],
                },
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.templates.list_templates(page_no=1, page_size=10)
        assert result["total"] == 2
        req = httpx_mock.get_requests()[-1]
        assert "page_no=1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_template(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {
                    "template_id": "tmpl1",
                    "name": "Movie Night",
                    "actions": [{"device_id": "d1", "code": "switch", "value": False}],
                },
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.templates.get_template("tmpl1")
        assert result["name"] == "Movie Night"
        req = httpx_mock.get_requests()[-1]
        assert "/scene-templates/tmpl1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_apply_template(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"scene_id": "s_new"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.templates.apply_template("tmpl1", "asset1")
        assert result["scene_id"] == "s_new"
        req = httpx_mock.get_requests()[-1]
        assert "/scene-templates/tmpl1/assets/asset1/actions/apply" in str(req.url)
        assert req.method == "POST"
        await client.close()
