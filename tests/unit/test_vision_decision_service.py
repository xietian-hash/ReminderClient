from __future__ import annotations

import json

import pytest

from reminder_client.domain.enums import VisionDecisionResult
from reminder_client.domain.models import AppSettings, Reminder
from reminder_client.services.ark_vision_client import ArkVisionClient
from reminder_client.services.vision_decision_service import (
    VISION_DECISION_PROMPT,
    VisionDecisionService,
    normalize_vision_result,
)


class FakeCameraService:
    def __init__(self, image_bytes: bytes = b'png-bytes', should_fail: bool = False) -> None:
        self.image_bytes = image_bytes
        self.should_fail = should_fail
        self.calls = 0

    def capture_image_bytes(self) -> bytes:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError('摄像头不可用')
        return self.image_bytes


class FakeArkClient:
    def __init__(self, response_text: str = '用户未离开电脑前') -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def analyze_image(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.response_text


class FakeAudioService:
    def __init__(self) -> None:
        self.played: list[str | None] = []

    def play(self, custom_sound_path: str | None) -> str | None:
        self.played.append(custom_sound_path)
        return custom_sound_path


class FakeVisionLogRepository:
    def __init__(self) -> None:
        self.logs = []

    def add(self, log) -> object:
        self.logs.append(log)
        return log


def build_settings() -> AppSettings:
    return AppSettings(
        ark_base_url='https://ark.cn-beijing.volces.com/api/v3/responses',
        ark_api_key='test-key',
        ark_model_name='doubao-seed-2-0-mini-260215',
    )


def build_reminder() -> Reminder:
    return Reminder(
        name='久坐提醒',
        reminder_interval_minutes=45,
        break_interval_minutes=5,
        visual_reminder_enabled=True,
        visual_music_path=r'C:\audio\visual.mp3',
    )


def test_normalize_vision_result_maps_three_outputs() -> None:
    assert normalize_vision_result('用户已离开电脑前') == VisionDecisionResult.USER_LEFT_DESK
    assert normalize_vision_result('用户未离开电脑前') == VisionDecisionResult.USER_STAYING
    assert normalize_vision_result('其他内容') == VisionDecisionResult.FAILED


def test_ark_client_builds_image_request_payload(monkeypatch) -> None:
    client = ArkVisionClient()
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps({'output_text': '用户未离开电脑前'}, ensure_ascii=False).encode('utf-8')

    def fake_urlopen(request, timeout=None):
        captured['request'] = request
        captured['timeout'] = timeout
        return FakeResponse()

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = client.analyze_image(
        image_bytes=b'abc',
        prompt=VISION_DECISION_PROMPT,
        base_url='https://ark.cn-beijing.volces.com/api/v3/responses',
        api_key='test-key',
        model_name='doubao-seed-2-0-mini-260215',
    )

    request = captured['request']
    body = json.loads(request.data.decode('utf-8'))

    assert result == '用户未离开电脑前'
    assert request.full_url == 'https://ark.cn-beijing.volces.com/api/v3/responses'
    assert request.get_header('Authorization') == 'Bearer test-key'
    assert body['model'] == 'doubao-seed-2-0-mini-260215'
    assert body['input'][0]['content'][0]['type'] == 'input_image'
    assert body['input'][0]['content'][0]['image_url'].startswith('data:image/png;base64,')
    assert body['input'][0]['content'][1]['text'] == VISION_DECISION_PROMPT


def test_ark_client_prefers_message_text_over_reasoning_summary(monkeypatch) -> None:
    client = ArkVisionClient()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    'created_at': 1776405204,
                    'id': 'resp_123',
                    'output': [
                        {
                            'id': 'rs_123',
                            'type': 'reasoning',
                            'summary': [
                                {
                                    'type': 'summary_text',
                                    'text': '这是一段推理摘要',
                                }
                            ],
                            'status': 'completed',
                        },
                        {
                            'id': 'msg_123',
                            'type': 'message',
                            'role': 'assistant',
                            'content': [
                                {
                                    'type': 'output_text',
                                    'text': '用户未离开电脑前',
                                }
                            ],
                            'status': 'completed',
                        },
                    ],
                    'status': 'completed',
                },
                ensure_ascii=False,
            ).encode('utf-8')

    def fake_urlopen(request, timeout=None):
        return FakeResponse()

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)

    result = client.analyze_image(
        image_bytes=b'abc',
        prompt=VISION_DECISION_PROMPT,
        base_url='https://ark.cn-beijing.volces.com/api/v3/responses',
        api_key='test-key',
        model_name='doubao-seed-2-0-mini-260215',
    )

    assert result == '用户未离开电脑前'


def test_vision_decision_service_logs_and_plays_audio_when_user_stays() -> None:
    camera_service = FakeCameraService()
    ark_client = FakeArkClient('用户未离开电脑前')
    log_repository = FakeVisionLogRepository()
    audio_service = FakeAudioService()
    service = VisionDecisionService(
        camera_service=camera_service,
        ark_client=ark_client,
        log_repository=log_repository,
        audio_service=audio_service,
    )

    result = service.evaluate(build_reminder(), build_settings())

    assert result == VisionDecisionResult.USER_STAYING
    assert camera_service.calls == 1
    assert len(ark_client.calls) == 1
    assert len(log_repository.logs) == 1
    assert log_repository.logs[0].result == VisionDecisionResult.USER_STAYING
    assert audio_service.played == [r'C:\audio\visual.mp3']


def test_vision_decision_service_logs_failure_when_camera_fails() -> None:
    camera_service = FakeCameraService(should_fail=True)
    ark_client = FakeArkClient('用户未离开电脑前')
    log_repository = FakeVisionLogRepository()
    audio_service = FakeAudioService()
    service = VisionDecisionService(
        camera_service=camera_service,
        ark_client=ark_client,
        log_repository=log_repository,
        audio_service=audio_service,
    )

    result = service.evaluate(build_reminder(), build_settings())

    assert result == VisionDecisionResult.FAILED
    assert camera_service.calls == 1
    assert len(ark_client.calls) == 0
    assert len(log_repository.logs) == 1
    assert log_repository.logs[0].result == VisionDecisionResult.FAILED
    assert audio_service.played == []
