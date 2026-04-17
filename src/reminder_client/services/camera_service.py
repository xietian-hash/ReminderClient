from __future__ import annotations

from PySide6.QtCore import QBuffer, QEventLoop, QIODevice, QTimer
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoSink


class CameraService:
    def capture_image_bytes(self, timeout_ms: int = 5000) -> bytes:
        devices = QMediaDevices.videoInputs()
        if not devices:
            raise RuntimeError('未检测到可用摄像头')

        camera = QCamera(devices[0])
        capture_session = QMediaCaptureSession()
        video_sink = QVideoSink()
        capture_session.setCamera(camera)
        capture_session.setVideoSink(video_sink)

        loop = QEventLoop()
        state: dict[str, object] = {}

        def on_frame_changed(frame) -> None:
            if not frame.isValid():
                return
            image = frame.toImage()
            if image.isNull():
                return
            state['image'] = image
            loop.quit()

        video_sink.videoFrameChanged.connect(on_frame_changed)

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)

        try:
            camera.start()
            timer.start(timeout_ms)
            loop.exec()
        finally:
            timer.stop()
            camera.stop()
            try:
                video_sink.videoFrameChanged.disconnect(on_frame_changed)
            except Exception:
                pass

        image = state.get('image')
        if image is None:
            raise RuntimeError('摄像头抓拍超时')

        buffer = QBuffer()
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            raise RuntimeError('无法写入抓拍缓冲区')
        try:
            if not image.save(buffer, 'PNG'):
                raise RuntimeError('抓拍图片保存失败')
            return bytes(buffer.data())
        finally:
            buffer.close()
