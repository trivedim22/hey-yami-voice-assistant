#!/usr/bin/env python3
"""
Hey Yami - wake-word listener (Vosk edition - NO training needed)

Listens on your microphone for "Wake up Yami" using the Vosk offline speech
recognizer in grammar mode, and opens Muse in your browser when it hears it.
100% on-device: no account, no cloud, no audio ever leaves the PC.

How it works (the honest trick): "yami" is not in Vosk's English dictionary,
so the recognizer is constrained to the soundalike phrase "wake up yummy" -
one vowel away. When you say "Wake up Yami", the grammar forces the decoder
to pick "wake up yummy" over "[unk]", and it fires. You say the real phrase.

Requirements (one-time):
    pip install vosk sounddevice

Plus the small Vosk model (40 MB), unzipped next to this script:
    https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    -> creates a folder named  vosk-model-small-en-us-0.15

Run:
    python hey_yami_vosk.py
"""

import argparse
import json
import sys
import time
import webbrowser
from pathlib import Path

# Silent-mode safety: under pythonw.exe sys.stdout is None and print() crashes,
# killing the listener without a trace. Log to a file instead.
if sys.stdout is None:
    sys.stdout = open(Path(__file__).with_name("hey_yami_log.txt"), "a", buffering=1)
if sys.stderr is None:
    sys.stderr = sys.stdout

WAKE_URL = "https://muse.ai"
SAMPLE_RATE = 16000
BLOCK = 8000  # 0.5 s blocks; partial results keep trigger latency low

# The grammar: the soundalike we listen for + the "anything else" bucket.
GRAMMAR = json.dumps(["wake up yummy", "[unk]"])
TRIGGER_TEXT = "wake up yummy"


def parse_args():
    p = argparse.ArgumentParser(description="Hey Yami wake-word listener (Vosk)")
    p.add_argument("--model", default=None,
                   help="Path to the unzipped vosk model folder (default: "
                        "vosk-model-small-en-us-0.15 next to this script)")
    p.add_argument("--cooldown", type=float, default=10.0,
                   help="Seconds to ignore repeat detections after a trigger "
                        "(default 10).")
    p.add_argument("--device", type=int, default=None,
                   help="Microphone index (see --list-devices). Default: system default.")
    p.add_argument("--list-devices", action="store_true",
                   help="List available audio input devices and exit.")
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
        from vosk import Model, KaldiRecognizer, SetLogLevel
    except ImportError:
        print("Missing dependency. Run:  pip install vosk")
        return 1

    model_dir = (Path(args.model) if args.model
                 else Path(__file__).with_name("vosk-model-small-en-us-0.15"))
    if not model_dir.exists():
        print(f"Vosk model folder not found: {model_dir}")
        print("Download the 40 MB small model and unzip it next to this script:")
        print("  https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        return 1

    SetLogLevel(-1)  # silence Vosk's own logging
    print("Loading model...")
    model = Model(str(model_dir))
    rec = KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)
    print('Listening for "Wake up Yami"... Ctrl+C to stop.')

    last_trigger = 0.0
    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                               blocksize=BLOCK, device=args.device) as stream:
            while True:
                data, overflowed = stream.read(BLOCK)
                # Final results only: partial guesses false-trigger on
                # anything that merely sounds close (TV, nearby speech).
                if not rec.AcceptWaveform(bytes(data)):
                    continue
                text = json.loads(rec.Result()).get("text", "")
                now = time.time()
                if TRIGGER_TEXT in text and now - last_trigger >= args.cooldown:
                    last_trigger = now
                    print(f'[{time.strftime("%H:%M:%S")}] Heard "Wake up Yami" - opening Muse...')
                    webbrowser.open(WAKE_URL)
                    rec = KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)  # reset decoder
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
