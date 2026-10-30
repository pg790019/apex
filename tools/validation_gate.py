
import threading

_gate_lock = threading.Lock()
_validation_status = {}


def _get_thread_id(runtime_config):
    configurable = (runtime_config or {}).get("configurable", {})
    thread_id = configurable.get("thread_id")

    if not thread_id:
        raise RuntimeError(
            "Cannot determine execution thread_id. "
            "GitHub publishing is blocked."
        )

    return str(thread_id)


def reset_validation_gate(runtime_config):
    thread_id = _get_thread_id(runtime_config)

    with _gate_lock:
        _validation_status[thread_id] = False


def record_validation_verdict(runtime_config, passed: bool):
    thread_id = _get_thread_id(runtime_config)

    with _gate_lock:
        _validation_status[thread_id] = bool(passed)


def is_github_publishing_allowed(runtime_config):
    thread_id = _get_thread_id(runtime_config)

    with _gate_lock:
        return _validation_status.get(thread_id, False)
