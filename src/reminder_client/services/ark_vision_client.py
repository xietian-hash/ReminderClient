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

        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = request.Request(
            base_url,
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
            raise RuntimeError(f'Ark 调用失败: {exc.code} {message}'.strip()) from exc
        except Exception as exc:
            raise RuntimeError(f'Ark 调用失败: {exc}') from exc

        parsed = json.loads(response_body)
        return self._extract_text(parsed, response_body)

    def _build_image_data_url(self, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode('ascii')
        return f'data:image/png;base64,{encoded}'

    def _extract_text(self, payload: Any, raw_body: str) -> str:
        if isinstance(payload, dict):
            output_text = payload.get('output_text')
            if isinstance(output_text, str) and output_text.strip():
                return output_text.strip()

            message_text = self._extract_output_message_text(payload.get('output'))
            if message_text:
                return message_text.strip()

            text = self._search_text(payload)
            if text:
                return text.strip()

        return raw_body

    def _extract_output_message_text(self, value: Any) -> str | None:
        if not isinstance(value, list):
            return None

        for item in value:
            if not isinstance(item, dict):
                continue
            if item.get('type') != 'message':
                continue
            text = self._extract_content_text(item.get('content'))
            if text:
                return text
        return None

    def _extract_content_text(self, value: Any) -> str | None:
        if isinstance(value, list):
            for item in value:
                text = self._extract_content_text(item)
                if text:
                    return text
        elif isinstance(value, dict):
            for key in ('text', 'output_text'):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate
        elif isinstance(value, str) and value.strip():
            return value
        return None

    def _search_text(self, value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ('text', 'output_text'):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate
            for nested_key in ('output', 'content', 'choices', 'message', 'messages'):
                nested_value = value.get(nested_key)
                candidate = self._search_text(nested_value)
                if candidate:
                    return candidate
            for nested_value in value.values():
                candidate = self._search_text(nested_value)
                if candidate:
                    return candidate
        elif isinstance(value, list):
            for item in value:
                candidate = self._search_text(item)
                if candidate:
                    return candidate
        elif isinstance(value, str) and value.strip():
            return value
        return None
