"""Phase 1 manual test: presses a key combo on a timer, then stops."""
import sys
import time

from keypresser.core.presser import KeyPresser
from keypresser.core.key_parser import parse_combo, KeyParseError

COMBO = sys.argv[1] if len(sys.argv) > 1 else "a"
INTERVAL_MS = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
DURATION_S = int(sys.argv[3]) if len(sys.argv) > 3 else 10


def test_parser() -> None:
    cases = [
        ("a",             ([], "a")),
        ("ctrl+c",        (["ctrl"], "c")),
        ("ctrl+shift+f5", (["ctrl", "shift"], "f5")),
        ("enter",         ([], "enter")),
        ("alt+tab",       (["alt"], "tab")),
    ]
    print("--- key_parser tests ---")
    all_ok = True
    for combo, _ in cases:
        try:
            mods, key = parse_combo(combo)
            print(f"  OK  {combo!r:25s} → mods={[str(m) for m in mods]}, key={key}")
        except KeyParseError as e:
            print(f"  FAIL {combo!r}: {e}")
            all_ok = False

    bad_cases = ["", "ctrl+badkey", "a+b"]
    for combo in bad_cases:
        try:
            parse_combo(combo)
            print(f"  FAIL expected error for {combo!r} but got none")
            all_ok = False
        except KeyParseError:
            print(f"  OK  {combo!r:25s} → correctly raised KeyParseError")

    print("Parser:", "ALL PASSED" if all_ok else "SOME FAILURES")
    print()


def test_presser() -> None:
    print(f"--- presser test: pressing {COMBO!r} every {INTERVAL_MS} ms for {DURATION_S} s ---")
    print("Focus a text editor or terminal NOW — keystrokes will be sent there.\n")
    time.sleep(3)

    kp = KeyPresser()
    kp.add_action(COMBO, INTERVAL_MS)
    kp.start()
    print(f"Started. Running for {DURATION_S} seconds...")

    halfway = DURATION_S / 2
    time.sleep(halfway)
    print(f"Pausing for 2 seconds at t={halfway:.0f}s...")
    kp.pause()
    time.sleep(2)
    print("Resuming...")
    kp.resume()

    time.sleep(DURATION_S - halfway)
    kp.stop()
    print("Stopped.")


if __name__ == "__main__":
    test_parser()
    test_presser()
