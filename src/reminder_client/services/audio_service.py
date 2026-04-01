from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl


class AudioService:
    def __init__(
        self,
        default_sound_path: str | None = None,
        player=None,
        audio_output=None,
        beep_callback=None,
    ) -> None:
        self.default_sound_path = default_sound_path
        self.player = player
        self.audio_output = audio_output
        self.beep_callback = beep_callback
        if self.player is not None and self.audio_output is not None:
            self.player.setAudioOutput(self.audio_output)

    def resolve_sound_path(self, custom_sound_path: str | None) -> str | None:
        if custom_sound_path:
            candidate = Path(custom_sound_path)
            if candidate.exists() and candidate.is_file():
                return str(candidate)
        if self.default_sound_path:
            candidate = Path(self.default_sound_path)
            if candidate.exists() and candidate.is_file():
                return str(candidate)
        return None

    def play(self, custom_sound_path: str | None) -> str | None:
        resolved = self.resolve_sound_path(custom_sound_path)
        if resolved is not None and self.player is not None:
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(resolved))
            self.player.play()
            return resolved

        if self.beep_callback is not None:
            self.beep_callback()
        return resolved

    def stop(self) -> None:
        if self.player is not None:
            self.player.stop()