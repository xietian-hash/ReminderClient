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
        endpoint = base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': model_name,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': self._build_image_data_url(image_bytes),
                            },
                        },
                        {
                            'type': 'text',
                            'text': prompt,
                        },
                    ],
                }
            ],
        }

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
        if isinstance(payload, dict):
            # OpenAI format: choices[0].message.content
            choices = payload.get('choices')
            if isinstance(choices, list) and choices:
                message = choices[0].get('message', {})
                content = message.get('content')
                if isinstance(content, str) and content.strip():
                    return content.strip()

        return raw_body
