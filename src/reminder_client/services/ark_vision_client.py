from __future__ import annotations

import base64
import json
from typing import Any
from urllib import error, request


class ArkVisionClient:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def analyze_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str,
        base_url: str,
        api_key: str,
        model_name: str,
    ) -> str:
        endpoint = base_url.rstrip('/') + '/responses'
        payload = {
            'model': model_name,
            'input': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_image',
                            'image_url': self._build_image_data_url(image_bytes),
                        },
                        {
                            'type': 'input_text',
                            'text': prompt,
                        },
                    ],
                }
            ],
        }
        return self._post(endpoint, payload, api_key)

    def test_connection(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
    ) -> str:
        """发送一条纯文本消息，验证 API 地址、API Key 和模型名称是否正确。"""
        endpoint = base_url.rstrip('/') + '/responses'
        payload = {
            'model': model_name,
            'input': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_text',
                            'text': '请回复"OK"。',
                        }
                    ],
                }
            ],
        }
        return self._post(endpoint, payload, api_key)

    def _post(self, endpoint: str, payload: dict, api_key: str) -> str:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = request.Request(
            endpoint,
            data=body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode('utf-8')
        except error.HTTPError as exc:
            message = exc.read().decode('utf-8', errors='ignore') if exc.fp else ''
            raise RuntimeError(f'调用失败: {exc.code} {message}'.strip()) from exc
        except Exception as exc:
            raise RuntimeError(f'调用失败: {exc}') from exc

        parsed = json.loads(response_body)
        return self._extract_text(parsed, response_body)

    def _build_image_data_url(self, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode('ascii')
        return f'data:image/png;base64,{encoded}'

    def _extract_text(self, payload: Any, raw_body: str) -> str:
        # Ark /responses 格式：output[].type=="message".content[].type=="output_text".text
        if isinstance(payload, dict):
            output = payload.get('output')
            if isinstance(output, list):
                for item in output:
                    if not isinstance(item, dict) or item.get('type') != 'message':
                        continue
                    content = item.get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'output_text':
                                text = block.get('text', '')
                                if isinstance(text, str) and text.strip():
                                    return text.strip()

        return raw_body
