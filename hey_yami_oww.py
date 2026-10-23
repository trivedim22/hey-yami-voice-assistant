#!/usr/bin/env python3
"""
Hey Yami - wake-word listener (openWakeWord edition)

Listens on your microphone for the phrase "Hey Yami" using a locally trained
openWakeWord model (hey_yami.onnx) and opens Muse in your browser when it
hears it. 100% on-device: no account, no cloud, no audio ever leaves the PC.

Requirements (one-time):
    pip install openwakeword sounddevice

You also need the trained model file hey_yami.onnx next to this script
(see README.md - Part A - for the free ~30-45 min training walkthrough).

Quick smoke test before training (uses the built-in "hey jarvis" model):
    python hey_yami_oww.py --test-builtin

Normal run:
    python hey_yami_oww.py
"""

import argparse
import sys
import time
import webbrowser
from pathlib import Path

import numpy as np

WAKE_URL = "https://muse.ai"
SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80 ms at 16 kHz - the frame size openWakeWord expects


def parse_args():
    p = argparse.ArgumentParser(description="Hey Yami wake-word listener (openWakeWord)")
    p.add_argument("--model", default=None,
                   help="Path to your trained .onnx model (default: hey_yami.onnx "
                        "next to this script)")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="Detection threshold 0-1 (default 0.5). Raise it if you get "
                        "false triggers, lower it if it misses you.")
    p.add_argument("--cooldown", type=float, default=10.0,
                   help="Seconds to ignore repeat detections after a trigger "
                        "(default 10).")
    p.add_argument("--device", type=int, default=None,
                   help="Microphone index (see --list-devices). Default: system default.")
    p.add_argument("--list-devices", action="store_true",
                   help="List available audio input devices and exit.")
    p.add_argument("--test-builtin", action="store_true",
                   help="Smoke-test mode: listen for the built-in phrase "
                        "'hey jarvis' instead of your custom model.")
    return p.parse_args()


def main():
    args = parse_args()

    try:
        import sounddevice as sd
    except ImportError:
        print("Missing dependency. Run:  pip install sounddevice")
        return 1

    if args.list_devices:
        print(sd.query_devices())
        return 0

    try:
        from openwakeword.model import Model
    except ImportError:
        print("Missing dependency. Run:  pip install openwakeword")
        return 1

    # --- Load the wake-word model ---
    if args.test_builtin:
        print('Smoke-test mode: say "Hey Jarvis" to test the pipeline.')
        model = Model(["hey_jarvis"], vad_threshold=0.5)
        label = "hey jarvis"
    else:
        model_path = Path(args.model) if args.model else Path(__file__).with_name("hey_yami.onnx")
        if not model_path.exists():
            print(f"Model file not found: {model_path}")
            print("Train it first (free, see README.md Part A), then save the")
            print("downloaded hey_yami.onnx next to this script.")
            return 1
        model = Model([str(model_path)], vad_threshold=0.5)
        label = model_path.stem.replace("_", " ")

    print(f'Listening for "{label}" (threshold {args.threshold})... Ctrl+C to stop.')

    last_trigger = 0.0
    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                               blocksize=FRAME_SAMPLES, device=args.device) as stream:
            while True:
                data, overflowed = stream.read(FRAME_SAMPLES)
                frame = np.frombuffer(data, dtype=np.int16)
                scores = model.predict(frame)
                score = max(scores.values()) if scores else 0.0
                now = time.time()
                if score >= args.threshold and now - last_trigger >= args.cooldown:
                    last_trigger = now
                    print(f'[{time.strftime("%H:%M:%S")}] Heard "{label}" '
                          f"(score {score:.2f}) - opening Muse...")
                    webbrowser.open(WAKE_URL)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        print("Tip: check Windows Settings > Privacy & security > Microphone,")
        print("and use --list-devices / --device N to pick the right mic.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
