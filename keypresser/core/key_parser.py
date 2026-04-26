from pynput.keyboard import Key, KeyCode

_MODIFIER_MAP: dict[str, Key] = {
    "ctrl":  Key.ctrl,
    "alt":   Key.alt,
    "shift": Key.shift,
    "win":   Key.cmd,
    "super": Key.cmd,
    "cmd":   Key.cmd,
    "meta":  Key.cmd,
}

_SPECIAL_KEY_MAP: dict[str, Key] = {
    "enter":        Key.enter,
    "return":       Key.enter,
    "space":        Key.space,
    "tab":          Key.tab,
    "backspace":    Key.backspace,
    "delete":       Key.delete,
    "del":          Key.delete,
    "escape":       Key.esc,
    "esc":          Key.esc,
    "up":           Key.up,
    "down":         Key.down,
    "left":         Key.left,
    "right":        Key.right,
    "home":         Key.home,
    "end":          Key.end,
    "page_up":      Key.page_up,
    "pageup":       Key.page_up,
    "page_down":    Key.page_down,
    "pagedown":     Key.page_down,
    "insert":       Key.insert,
    "ins":          Key.insert,
    "caps_lock":    Key.caps_lock,
    "capslock":     Key.caps_lock,
    "num_lock":     Key.num_lock,
    "print_screen": Key.print_screen,
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 21)},
}


class KeyParseError(ValueError):
    pass


def split_combo(combo: str) -> tuple[list[str], str]:
    """Parse a combo string into (modifier_names, key_name) as lowercase strings.

    Backend-agnostic — used by both pynput and uinput backends.
    Raises KeyParseError if the string is invalid.
    """
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        raise KeyParseError(f"Empty key combo: {combo!r}")

    modifier_names: list[str] = []
    main_key: str | None = None

    for part in parts:
        if part in _MODIFIER_MAP:
            if part not in modifier_names:
                modifier_names.append(part)
        elif part in _SPECIAL_KEY_MAP or len(part) == 1:
            if main_key is not None:
                raise KeyParseError(f"Multiple non-modifier keys in combo: {combo!r}")
            main_key = part
        else:
            raise KeyParseError(f"Unknown key {part!r} in combo: {combo!r}")

    if main_key is None:
        if not modifier_names:
            raise KeyParseError(f"No keys found in combo: {combo!r}")
        main_key = modifier_names.pop()

    return modifier_names, main_key


def parse_combo(combo: str) -> tuple[list[Key], Key | KeyCode]:
    """Parse a combo string like 'ctrl+shift+f5' into (modifiers, key).

    Returns (modifier Key list, main Key or KeyCode).
    Raises KeyParseError if the string is invalid.
    """
    modifier_names, key_name = split_combo(combo)
    modifiers = [_MODIFIER_MAP[m] for m in modifier_names]

    if key_name in _MODIFIER_MAP:
        return modifiers, _MODIFIER_MAP[key_name]
    if key_name in _SPECIAL_KEY_MAP:
        return modifiers, _SPECIAL_KEY_MAP[key_name]
    return modifiers, KeyCode.from_char(key_name)
