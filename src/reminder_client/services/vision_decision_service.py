from __future__ import annotations

from datetime import datetime

from reminder_client.domain.enums import VisionDecisionResult
from reminder_client.domain.models import AppSettings, Reminder, VisionDecisionLog
from reminder_client.services.ark_vision_client import ArkVisionClient
from reminder_client.services.audio_service import AudioService
from reminder_client.services.camera_service import CameraService
from reminder_client.storage.vision_log_repository import VisionLogRepository


VISION_DECISION_PROMPT = (
    '请判断图片中的用户是否已经离开电脑前，只能返回以下三种结果之一：'
    '用户已离开电脑前、用户未离开电脑前、识别失败。'
)


def normalize_vision_result(text: str) -> VisionDecisionResult:
    normalized = text.strip()
    if '用户已离开电脑前' in normalized:
        return VisionDecisionResult.USER_LEFT_DESK
    if '用户未离开电脑前' in normalized:
        return VisionDecisionResult.USER_STAYING
    if '识别失败' in normalized:
        return VisionDecisionResult.FAILED
    return VisionDecisionResult.FAILED


class VisionDecisionService:
    def __init__(
        self,
        *,
        camera_service: CameraService,
        ark_client: ArkVisionClient,
        log_repository: VisionLogRepository,
        audio_service: AudioService | None = None,
    ) -> None:
        self.camera_service = camera_service
        self.ark_client = ark_client
        self.log_repository = log_repository
        self.audio_service = audio_service

    def evaluate(
        self,
        reminder: Reminder,
        settings: AppSettings,
        *,
        play_audio: bool = True,
    ) -> VisionDecisionResult:
        captured_at = datetime.now()
        requested_at = captured_at
        completed_at = captured_at
        raw_response_text: str | None = None
        error_message: str | None = None

        try:
            image_bytes = self.camera_service.capture_image_bytes()
            requested_at = datetime.now()
            raw_response_text = self.ark_client.analyze_image(
                image_bytes=image_bytes,
                prompt=VISION_DECISION_PROMPT,
                base_url=settings.ark_base_url,
                api_key=settings.ark_api_key,
                model_name=settings.ark_model_name,
            )
            result = normalize_vision_result(raw_response_text)
        except Exception as exc:
            error_message = str(exc)
            result = VisionDecisionResult.FAILED
        completed_at = datetime.now()

        self.log_repository.add(
            VisionDecisionLog(
                reminder_id=reminder.id,
                reminder_name=reminder.name,
                request_url=settings.ark_base_url,
                model_name=settings.ark_model_name,
                result=result,
                raw_response_text=raw_response_text,
                error_message=error_message,
                captured_at=captured_at,
                requested_at=requested_at,
                completed_at=completed_at,
            )
        )

        if play_audio and result == VisionDecisionResult.USER_STAYING and self.audio_service is not None:
            try:
                self.audio_service.play(reminder.visual_music_path)
            except Exception:
                pass

        return result
