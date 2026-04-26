import threading
from dataclasses import dataclass, field

from .key_parser import split_combo, KeyParseError
from .backends import KeyboardBackend, create_backend


@dataclass
class Action:
    combo: str
    interval_ms: int
    enabled: bool = True
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)


class KeyPresser:
    def __init__(self) -> None:
        self._backend: KeyboardBackend = create_backend()
        self._actions: list[Action] = []
        self._running = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially

    def add_action(self, combo: str, interval_ms: int) -> Action:
        """Add a key action. Raises KeyParseError if combo is invalid."""
        split_combo(combo)  # validate eagerly (backend-agnostic)
        action = Action(combo=combo, interval_ms=interval_ms)
        self._actions.append(action)
        if self._running:
            self._start_action(action)
        return action

    def remove_action(self, action: Action) -> None:
        action._stop_event.set()
        if action._thread and action._thread.is_alive():
            action._thread.join(timeout=2)
        self._actions.remove(action)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._paused = False
        self._pause_event.set()
        for action in self._actions:
            if action.enabled:
                self._start_action(action)

    def stop(self) -> None:
        self._running = False
        self._paused = False
        self._pause_event.set()  # unblock any waiting threads so they can exit
        for action in self._actions:
            action._stop_event.set()
        for action in self._actions:
            if action._thread and action._thread.is_alive():
                action._thread.join(timeout=2)
            action._stop_event.clear()
            action._thread = None

    def close(self) -> None:
        """Stop all actions and release backend resources."""
        self.stop()
        self._backend.close()

    def pause(self) -> None:
        if not self._running or self._paused:
            return
        self._paused = True
        self._pause_event.clear()

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        self._pause_event.set()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def _start_action(self, action: Action) -> None:
        action._stop_event.clear()
        action._thread = threading.Thread(
            target=self._action_loop,
            args=(action,),
            daemon=True,
            name=f"keypresser-{action.combo}",
        )
        action._thread.start()

    def _action_loop(self, action: Action) -> None:
        interval_s = action.interval_ms / 1000.0
        while not action._stop_event.is_set():
            self._pause_event.wait()  # block here when paused
            if action._stop_event.is_set():
                break
            try:
                self._backend.press_combo(action.combo)
            except Exception as exc:
                print(f"[keypresser] Error pressing {action.combo!r}: {exc}")
            # Use wait instead of sleep so stop_event interrupts the interval
            action._stop_event.wait(timeout=interval_s)
