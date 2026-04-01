from __future__ import annotations

from reminder_client.services.audio_service import AudioService
from reminder_client.services.autostart_service import AutostartService, RUN_KEY_PATH


class FakeRegistryProvider:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_value(self, key_path: str, name: str, value: str) -> None:
        self.values[(key_path, name)] = value

    def delete_value(self, key_path: str, name: str) -> None:
        self.values.pop((key_path, name), None)

    def get_value(self, key_path: str, name: str) -> str | None:
        return self.values.get((key_path, name))


class FakePlayer:
    def __init__(self) -> None:
        self.audio_output = None
        self.source = None
        self.play_calls = 0
        self.stop_calls = 0

    def setAudioOutput(self, audio_output) -> None:
        self.audio_output = audio_output

    def setSource(self, source) -> None:
        self.source = source

    def play(self) -> None:
        self.play_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


class FakeBeep:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def test_audio_service_falls_back_to_beep_when_no_sound_file(tmp_path) -> None:
    beep = FakeBeep()
    player = FakePlayer()
    audio_service = AudioService(player=player, audio_output=object(), beep_callback=beep)

    resolved = audio_service.play(str(tmp_path / 'missing.wav'))

    assert resolved is None
    assert beep.calls == 1
    assert player.play_calls == 0


def test_audio_service_plays_existing_file(tmp_path) -> None:
    beep = FakeBeep()
    player = FakePlayer()
    sound = tmp_path / 'sound.wav'
    sound.write_text('sound', encoding='utf-8')
    audio_service = AudioService(player=player, audio_output=object(), beep_callback=beep)

    resolved = audio_service.play(str(sound))

    assert resolved == str(sound)
    assert player.play_calls == 1
    assert player.stop_calls == 1
    assert beep.calls == 0


def test_enable_autostart_writes_registry_value() -> None:
    registry = FakeRegistryProvider()
    service = AutostartService(
        app_name='ReminderClient',
        executable_path=r'C:\Reminder\reminder-client.exe',
        registry=registry,
    )

    service.enable()

    assert registry.get_value(RUN_KEY_PATH, 'ReminderClient') == r'C:\Reminder\reminder-client.exe'
    assert service.is_enabled() is True


def test_disable_autostart_removes_registry_value() -> None:
    registry = FakeRegistryProvider()
    service = AutostartService(
        app_name='ReminderClient',
        executable_path=r'C:\Reminder\reminder-client.exe',
        registry=registry,
    )
    service.enable()

    service.disable()

    assert registry.get_value(RUN_KEY_PATH, 'ReminderClient') is None
    assert service.is_enabled() is False