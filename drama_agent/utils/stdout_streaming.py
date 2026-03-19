"""
stdout 流式输出的线程局部标记，由「print 那一侧」设置，部署版 LogCapture 只读不记状态。
"""
import threading

_thread_local = threading.local()


def set_stdout_streaming(value: bool) -> None:
    _thread_local.stdout_streaming = value


def is_stdout_streaming() -> bool:
    return getattr(_thread_local, "stdout_streaming", False)


def set_stdout_stream_first(value: bool) -> None:
    """流式开始前设为 True，表示下一笔是流式段的第一块（打 [时间] [STREAM_START] 前缀）。"""
    _thread_local.stdout_stream_first = value


def consume_stdout_stream_first() -> bool:
    """取并清掉「下一笔是流式第一块」标记，供 LogCapture 单次使用。"""
    out = getattr(_thread_local, "stdout_stream_first", False)
    _thread_local.stdout_stream_first = False
    return out


def set_stdout_stream_end(value: bool) -> None:
    """流式结束后设为 True，表示需要在下一笔前或 flush 时补换行。"""
    _thread_local.stdout_stream_end = value


def consume_stdout_stream_end() -> bool:
    """取并清掉「需要补换行」标记。"""
    out = getattr(_thread_local, "stdout_stream_end", False)
    _thread_local.stdout_stream_end = False
    return out
