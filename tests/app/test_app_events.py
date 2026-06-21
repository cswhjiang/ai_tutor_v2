from src.streaming.app_events import (
    publish_app_event,
    register_app_event_queue,
    unregister_app_event_queue,
)


def test_app_event_queue_publish_and_unregister():
    queue = register_app_event_queue("trace-1")
    event = {"type": "video_preview", "content": {"url": "/outputs/video.mp4"}}

    assert publish_app_event("trace-1", event) is True
    assert queue.get_nowait() == event

    unregister_app_event_queue("trace-1")
    assert publish_app_event("trace-1", event) is False
