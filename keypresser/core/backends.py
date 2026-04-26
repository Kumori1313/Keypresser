import os
from abc import ABC, abstractmethod

from .key_parser import split_combo, parse_combo, KeyParseError

# evdev key names for modifiers and special keys (resolved lazily against ecodes)
_EVDEV_MODIFIER_NAMES: dict[str, str] = {
    "ctrl":  "KEY_LEFTCTRL",
    "alt":   "KEY_LEFTALT",
    "shift": "KEY_LEFTSHIFT",
    "win":   "KEY_LEFTMETA",
    "super": "KEY_LEFTMETA",
    "cmd":   "KEY_LEFTMETA",
    "meta":  "KEY_LEFTMETA",
}

_EVDEV_SPECIAL_NAMES: dict[str, str] = {
    "enter":        "KEY_ENTER",
    "return":       "KEY_ENTER",
    "space":        "KEY_SPACE",
    "tab":          "KEY_TAB",
    "backspace":    "KEY_BACKSPACE",
    "delete":       "KEY_DELETE",
    "del":          "KEY_DELETE",
    "escape":       "KEY_ESC",
    "esc":          "KEY_ESC",
    "up":           "KEY_UP",
    "down":         "KEY_DOWN",
    "left":         "KEY_LEFT",
    "right":        "KEY_RIGHT",
    "home":         "KEY_HOME",
    "end":          "KEY_END",
    "page_up":      "KEY_PAGEUP",
    "pageup":       "KEY_PAGEUP",
    "page_down":    "KEY_PAGEDOWN",
    "pagedown":     "KEY_PAGEDOWN",
    "insert":       "KEY_INSERT",
    "ins":          "KEY_INSERT",
    "caps_lock":    "KEY_CAPSLOCK",
    "capslock":     "KEY_CAPSLOCK",
    "num_lock":     "KEY_NUMLOCK",
    "print_screen": "KEY_SYSRQ",
    **{f"f{i}": f"KEY_F{i}" for i in range(1, 21)},
}


class KeyboardBackend(ABC):
    @abstractmethod
    def press_combo(self, combo: str) -> None: ...

    def close(self) -> None:
        pass


class PynputBackend(KeyboardBackend):
    def __init__(self) -> None:
        from pynput.keyboard import Controller
        self._kb = Controller()

    def press_combo(self, combo: str) -> None:
        modifiers, main_key = parse_combo(combo)
        for mod in modifiers:
            self._kb.press(mod)
        self._kb.press(main_key)
        self._kb.release(main_key)
        for mod in reversed(modifiers):
            self._kb.release(mod)


class UInputBackend(KeyboardBackend):
    def __init__(self) -> None:
        try:
            from evdev import UInput, ecodes
        except ImportError:
            raise RuntimeError(
                "evdev is required for Wayland support.\n"
                "  Arch: sudo pacman -S python-evdev  (or pip install evdev in your venv)\n"
                "  Other Linux: pip install evdev"
            )

        self._ecodes = ecodes
        self._mod_map: dict[str, int] = {
            name: getattr(ecodes, evdev_name)
            for name, evdev_name in _EVDEV_MODIFIER_NAMES.items()
        }
        self._special_map: dict[str, int] = {
            name: getattr(ecodes, evdev_name)
            for name, evdev_name in _EVDEV_SPECIAL_NAMES.items()
        }

        # Enable only the keys we actually know how to press.
        # (Including every KEY_* in ecodes hits sentinels like KEY_CNT and
        # the kernel rejects them with EINVAL.)
        cap_codes: set[int] = set(self._mod_map.values()) | set(self._special_map.values())
        for c in "abcdefghijklmnopqrstuvwxyz":
            cap_codes.add(getattr(ecodes, f"KEY_{c.upper()}"))
        for d in "0123456789":
            cap_codes.add(getattr(ecodes, f"KEY_{d}"))

        try:
            self._ui = UInput({ecodes.EV_KEY: sorted(cap_codes)}, name="keypresser")
        except PermissionError:
            raise PermissionError(
                "Cannot access /dev/uinput. Add your user to the 'input' group:\n"
                "  sudo usermod -aG input $USER\n"
                "Then run 'newgrp input' or log out and back in."
            )

    def press_combo(self, combo: str) -> None:
        ecodes = self._ecodes
        mod_names, key_name = split_combo(combo)
        mod_codes = [self._mod_map[m] for m in mod_names]
        key_code = self._resolve_key(key_name)

        for code in mod_codes:
            self._ui.write(ecodes.EV_KEY, code, 1)
        self._ui.write(ecodes.EV_KEY, key_code, 1)
        self._ui.syn()
        self._ui.write(ecodes.EV_KEY, key_code, 0)
        for code in reversed(mod_codes):
            self._ui.write(ecodes.EV_KEY, code, 0)
        self._ui.syn()

    def _resolve_key(self, key_name: str) -> int:
        if key_name in self._special_map:
            return self._special_map[key_name]
        if key_name in self._mod_map:
            return self._mod_map[key_name]
        if len(key_name) == 1:
            if key_name.isalpha():
                return getattr(self._ecodes, f"KEY_{key_name.upper()}")
            if key_name.isdigit():
                return getattr(self._ecodes, f"KEY_{key_name}")
            raise KeyParseError(f"No evdev code for character: {key_name!r}")
        raise KeyParseError(f"Unknown key: {key_name!r}")

    def close(self) -> None:
        self._ui.close()


def create_backend() -> KeyboardBackend:
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        print("[keypresser] Wayland session detected — using uinput backend")
        return UInputBackend()
    return PynputBackend()
