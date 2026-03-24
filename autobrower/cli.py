import argparse
import sys

from autobrower.config import PLAYBACK_SPEED, SAMPLE_INTERVAL, get_profile_path, list_profiles
from autobrower.player import Player, load_profile
from autobrower.recorder import Recorder


def cmd_record(args: argparse.Namespace) -> None:
    interval = args.interval
    name = args.profile

    path = get_profile_path(name)
    if path.exists() and not args.force:
        answer = input(f"Profile '{name}' already exists. Overwrite? (y/N): ").strip().lower()
        if answer != "y":
            print("Cancelled.")
            return

    print(f"Recording profile '{name}' (interval={interval}s)")
    print("Press 'h' to scan screen for target text (OCR).")
    print("Press Ctrl+C to stop recording...")

    recorder = Recorder(interval=interval)
    recorder.start()

    if not recorder.events:
        print("\nNo events recorded.")
        return

    path = recorder.save(name)
    print(f"\nSaved {len(recorder.events)} events ({recorder.events[-1]['t']:.1f}s) to {path}")


def cmd_play(args: argparse.Namespace) -> None:
    from autobrower.player import DEFAULT_NO_CITAS_PHRASES

    name = args.profile
    try:
        profile = load_profile(name)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    loop = not args.no_loop
    speed = args.speed

    # Build scan targets list
    scan_targets: list[str] | None = None
    if args.scan:
        scan_targets = args.scan_target if args.scan_target else DEFAULT_NO_CITAS_PHRASES

    n = profile["event_count"]
    dur = profile["duration"]
    print(f"Playing profile '{name}' ({n} events, {dur}s, speed={speed}x, loop={loop})")
    if scan_targets:
        print(f"Scanning for: {scan_targets}")
        print("Loop stops + alert when text disappears (appointments available).")
    print("Press 'j', Ctrl+C, or move mouse to top-left corner to stop.")

    player = Player(profile, speed=speed, loop=loop, loop_delay=args.loop_delay,
                    scan_targets=scan_targets, scroll_factor=args.scroll_factor)
    player.play()
    print("\nPlayback stopped.")


def cmd_list(args: argparse.Namespace) -> None:
    profiles = list_profiles()
    if not profiles:
        print("No profiles found.")
        return

    print(f"{'Name':<25} {'Created':<22} {'Duration':>10} {'Events':>8}")
    print("-" * 67)
    for p in profiles:
        created = p["created"][:19].replace("T", " ") if p["created"] != "unknown" else "unknown"
        print(f"{p['name']:<25} {created:<22} {p['duration']:>9.1f}s {p['event_count']:>8}")


def cmd_scan(args: argparse.Namespace) -> None:
    import threading
    from pynput import keyboard
    from autobrower.scanner import scan_for_text, _get_cursor_pos

    from autobrower.config import SCAN_TARGETS

    targets = args.scan_target or list(SCAN_TARGETS)
    scanning = threading.Event()

    print("=== OCR debug mode ===")
    print(f"Targets: {targets}")
    print("Press 'h' to capture and OCR the area around the cursor.")
    print("Press Ctrl+C to exit.\n")

    def _do_scan(pos):
        try:
            for target in targets:
                found, ocr_text = scan_for_text(target, pos=pos)
                print(f"\n--- OCR result ---")
                print(ocr_text.strip() if ocr_text.strip() else "(empty)")
                print(f"--- Target: \"{target}\" → {'FOUND' if found else 'NOT FOUND'} ---\n")
                if found:
                    return
        except Exception as exc:
            print(f"\n[ERROR] {exc}\n")
        finally:
            scanning.clear()

    def on_press(key):
        try:
            char = key.char
        except AttributeError:
            return
        if char != "h":
            return
        if scanning.is_set():
            return
        scanning.set()
        pos = _get_cursor_pos()
        threading.Thread(target=_do_scan, args=(pos,), daemon=True).start()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    try:
        while listener.is_alive():
            listener.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
    print("\nScan mode stopped.")


def cmd_delete(args: argparse.Namespace) -> None:
    name = args.profile
    path = get_profile_path(name)
    if not path.exists():
        print(f"Error: Profile '{name}' not found.", file=sys.stderr)
        sys.exit(1)

    answer = input(f"Delete profile '{name}'? (y/N): ").strip().lower()
    if answer != "y":
        print("Cancelled.")
        return

    path.unlink()
    print(f"Deleted profile '{name}'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="autobrower",
        description="Record and replay mouse actions at OS level.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # record
    p_rec = subparsers.add_parser("record", help="Record mouse events to a profile")
    p_rec.add_argument("profile", help="Profile name")
    p_rec.add_argument("-i", "--interval", type=float, default=SAMPLE_INTERVAL,
                       help=f"Sampling interval in seconds (default: {SAMPLE_INTERVAL})")
    p_rec.add_argument("--force", action="store_true", help="Overwrite existing profile without asking")
    p_rec.set_defaults(func=cmd_record)

    # play
    p_play = subparsers.add_parser("play", help="Replay a recorded profile")
    p_play.add_argument("profile", help="Profile name")
    p_play.add_argument("--speed", type=float, default=PLAYBACK_SPEED,
                        help=f"Playback speed multiplier (default: {PLAYBACK_SPEED})")
    p_play.add_argument("--no-loop", action="store_true", help="Play once instead of looping")
    p_play.add_argument("--loop-delay", type=float, default=0.5,
                        help="Seconds to wait between loop cycles (default: 0.5)")
    p_play.add_argument("--scroll-factor", type=int, default=1,
                        help="Multiply scroll amounts by this factor (default: 1)")
    p_play.add_argument("--scan", action="store_true",
                        help="Enable OCR scan after each loop cycle to detect appointment availability")
    p_play.add_argument("--scan-target", type=str, action="append", default=None,
                        help="Text to scan for (can be repeated). Defaults to 'no hay citas disponibles' phrases")
    p_play.set_defaults(func=cmd_play)

    # scan (OCR debug)
    p_scan = subparsers.add_parser("scan", help="OCR debug mode: press 'h' to see what the OCR reads")
    p_scan.add_argument("--scan-target", type=str, action="append", default=None,
                        help="Text to search for (can be repeated). Defaults to SCAN_TARGETS from .env")
    p_scan.set_defaults(func=cmd_scan)

    # list
    p_list = subparsers.add_parser("list", help="List available profiles")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_del = subparsers.add_parser("delete", help="Delete a profile")
    p_del.add_argument("profile", help="Profile name to delete")
    p_del.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
