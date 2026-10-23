#!/usr/bin/env python3
"""
Hey Yami - hands-free voice assistant loop (openWakeWord TRUE-phrase wake
models + Whisper transcription + TTS)

The wake ears are locally trained openWakeWord models that hear the REAL
phrases below - no dictionary soundalikes ("yummy") like the Vosk edition.
Vosk is still used for one job only: endpointing your spoken request while
recording (deciding when you stopped talking), which it does well.

Two voice commands, all on your PC:
    "Wake up Yami"  -> just opens Muse (the installed web app if present).
    "Hey Yami"      -> the talk command (replaces clicking the speak button):
        1. Replies out loud: "How can I help you?"   (Windows built-in voice)
        2. Listens to your spoken request  (records until you stop talking)
        3. Transcribes it accurately       (faster-whisper, once per request)
        4. Opens Muse, pastes your words into the chat and presses Enter.

A small always-on-top status pill (top-right corner) shows what the listener
is doing - Listening / Heard you / Sending - so silent mode is never a black
box. Right-click the pill to quit. Disable it with --no-overlay.

Requirements (one-time):
    py -3.12 -m pip install openwakeword vosk sounddevice faster-whisper pyttsx3 pyautogui pyperclip pygetwindow

Plus, next to this script:
    - hey_yami.onnx and wake_up_yami.onnx - your trained wake-word models
      (train them free in ~30-45 min each - see README-training.md)
    - the Vosk small model folder:  vosk-model-small-en-us-0.15
      (https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
      (kept only to endpoint the request recording - see above)
    The Whisper model downloads itself automatically on first run (~150 MB).

Run:
    py -3.12 hey_yami_assistant_oww.py
"""

import argparse
import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

import numpy as np

# Silent-mode safety: under pythonw.exe there is no console and sys.stdout is
# None, which makes print() crash and kills the listener without a trace.
# Redirect output to a log file next to this script instead.
if sys.stdout is None:
    sys.stdout = open(Path(__file__).with_name("hey_yami_log.txt"), "a", buffering=1)
if sys.stderr is None:
    sys.stderr = sys.stdout

WAKE_URL = "https://muse.ai"
SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280            # 80 ms at 16 kHz - the frame openWakeWord expects
HEY_MODEL_KEY = "hey_yami"        # trained model for "Hey Yami"      -> start a talk
WAKE_MODEL_KEY = "wake_up_yami"   # trained model for "Wake up Yami"  -> just open Muse

# Recording (for the spoken request) - speech detection uses Vosk itself,
# the exact same "ears" as the wake-word listener: NO loudness gate at all.
BLOCK = 4000                 # 0.25 s blocks
END_SILENCE_BLOCKS = 6       # ~1.5 s of Vosk-heard silence after speech = done
MAX_BLOCKS = 60              # hard cap: 15 s of request audio
NO_SPEECH_BLOCKS = 32        # give up after ~8 s with no speech heard

# Status pill states: (text, dot color)
ST_STARTING = ("Starting...", "#9e9e9e")
ST_LISTENING = ("Listening - say Hey Yami", "#4caf50")
ST_OPENING = ("Opening Muse...", "#42a5f5")
ST_HEARD = ("Heard you - speak now!", "#ff5252")
ST_WRITING = ("Writing it down...", "#ffc107")
ST_SENDING = ("Sending to Muse...", "#42a5f5")
ST_SENT = ("Sent", "#4caf50")
ST_ERROR = ("Error - check hey_yami_log.txt", "#ff5252")


class Status:
    """Shared listener state, read by the overlay pill, written by the worker."""

    def __init__(self):
        self.state = ST_STARTING

    def set(self, state):
        self.state = state


def beep(freq=880, ms=110, enabled=True):
    if not enabled:
        return
    try:
        import winsound
        winsound.Beep(freq, ms)
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser(description="Hey Yami hands-free voice loop")
    p.add_argument("--model", default=None,
                   help="Path to the Vosk model folder (default: next to this "
                        "script). Vosk only endpoints the request recording.")
    p.add_argument("--hey-model", default=None,
                   help="Path to the trained 'Hey Yami' model "
                        "(default: hey_yami.onnx next to this script)")
    p.add_argument("--wake-model", default=None,
                   help="Path to the trained 'Wake up Yami' model "
                        "(default: wake_up_yami.onnx next to this script)")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="Wake-word detection threshold 0-1 (default 0.5). "
                        "Raise it if the TV triggers it, lower it if it "
                        "misses you.")
    p.add_argument("--whisper-model", default="base",
                   choices=["tiny", "base", "small", "medium"],
                   help="Whisper size for transcribing your request (default base; "
                        "small is more accurate but slower)")
    p.add_argument("--device", type=int, default=None, help="Microphone index")
    p.add_argument("--list-devices", action="store_true")
    p.add_argument("--cooldown", type=float, default=5.0,
                   help="Seconds to rest after each conversation (default 5)")
    p.add_argument("--load-wait", type=float, default=5.0,
                   help="Seconds to wait for Muse to load before pasting (default 5)")
    p.add_argument("--input-y", type=float, default=0.92,
                   help="Where the chat box sits, as a fraction of the Muse "
                        "window's height (default 0.92).")
    p.add_argument("--open-mode", choices=["app", "browser"], default="app",
                   help="'app' launches your installed Muse web app (default). "
                        "'browser' uses the old new-tab behavior.")
    p.add_argument("--app-name", default="Muse",
                   help="Name of the installed web app's Start Menu shortcut "
                        "(default: Muse).")
    p.add_argument("--no-overlay", action="store_true",
                   help="Don't show the floating status pill.")
    p.add_argument("--no-beep", action="store_true",
                   help="No sound cues on wake / sent.")
    p.add_argument("--mic-level", type=int, default=None,
                   help="(deprecated, ignored) The recorder no longer uses a "
                        "loudness gate - it hears speech the same way the "
                        "wake-word listener does.")
    return p.parse_args()


def speak(text):
    """Say something with the Windows voice. Never let TTS errors kill the loop."""
    print(f"Yami (voice): {text}")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"(voice unavailable: {e})")


def listen_for_wake(sd, oww_model, device, threshold):
    """Block until a command phrase is heard. Returns 'open' or 'talk'.

    openWakeWord scores every 80 ms frame against both trained models.
    A command fires the moment one model's score crosses the threshold;
    the model's buffers are reset immediately so the tail of the same
    phrase can't fire twice.
    """
    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                           blocksize=FRAME_SAMPLES, device=device) as stream:
        while True:
            data, _ = stream.read(FRAME_SAMPLES)
            frame = np.frombuffer(bytes(data), dtype=np.int16)
            scores = oww_model.predict(frame)
            if scores.get(WAKE_MODEL_KEY, 0.0) >= threshold:
                oww_model.reset()
                return "open"
            if scores.get(HEY_MODEL_KEY, 0.0) >= threshold:
                oww_model.reset()
                return "talk"


def record_request(sd, device, model):
    """Record the user's request; stop when they stop talking. Returns float32 audio.

    Speech detection uses a free-form Vosk recognizer - literally the same
    ears as the wake-word listener, which hears him reliably. There is NO
    loudness gate: Vosk's acoustic model decides what is speech, so a soft
    voice counts exactly like a loud one. We stop after ~1.5 s of Vosk-heard
    silence following speech; Whisper transcribes the collected audio after.
    """
    from vosk import KaldiRecognizer
    rec = KaldiRecognizer(model, SAMPLE_RATE)  # no grammar = free-form ears
    chunks = []
    heard_speech = False
    silence_blocks = 0
    total = 0
    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                           blocksize=BLOCK, device=device) as stream:
        while total < MAX_BLOCKS:
            data, _ = stream.read(BLOCK)
            raw = bytes(data)
            frame = np.frombuffer(raw, dtype=np.int16)
            chunks.append(frame)
            total += 1
            if rec.AcceptWaveform(raw):
                activity = bool(json.loads(rec.Result()).get("text", "").strip())
            else:
                activity = bool(json.loads(rec.PartialResult()).get("partial", "").strip())
            if activity:
                heard_speech = True
                silence_blocks = 0
            elif heard_speech:
                silence_blocks += 1
                if silence_blocks >= END_SILENCE_BLOCKS:
                    break
            elif total >= NO_SPEECH_BLOCKS:
                return None  # nobody said anything
    if not heard_speech:
        return None
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    return audio


_shortcut_cache = None


def find_app_shortcut(name):
    """Locate the installed web app's Start Menu shortcut (e.g. 'Muse.lnk')."""
    global _shortcut_cache
    if _shortcut_cache is not None:
        return _shortcut_cache
    roots = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    found = None
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".lnk") and name.lower() in f.lower():
                    found = os.path.join(dirpath, f)
                    break
            if found:
                break
        if found:
            break
    _shortcut_cache = found
    return found


def launch_muse(args):
    """Bring up Muse: the installed web app if possible (its window gets
    focused/reused), otherwise the browser (which means a new tab)."""
    if args.open_mode == "app":
        shortcut = find_app_shortcut(args.app_name)
        if shortcut and hasattr(os, "startfile"):
            try:
                os.startfile(shortcut)
                return
            except Exception as e:
                print(f"(app launch failed: {e} - falling back to browser)")
        else:
            print("(installed Muse app shortcut not found - using browser)")
    webbrowser.open(WAKE_URL)


def find_muse_window():
    """Return the already-open Muse window (pygetwindow), or None.

    Ranked by title: an exact 'Muse' window title (the installed app)
    beats a title that merely contains 'Muse' (more likely a browser tab).
    """
    try:
        import pygetwindow as gw
        candidates = [w for w in gw.getAllWindows() if w.width > 100 and w.title]
        exact = [w for w in candidates if w.title.strip().lower() == "muse"]
        if exact:
            return exact[0]
        starts = [w for w in candidates if w.title.strip().lower().startswith("muse")]
        if starts:
            return starts[0]
        contains = [w for w in candidates
                    if "muse" in w.title.lower() or "muse.ai" in w.title.lower()]
        if contains:
            return contains[0]
    except Exception:
        pass
    return None


def ensure_muse(args):
    """Use the Muse window that is ALREADY open whenever there is one -
    just bring it to the front. Only launch the app/browser when no Muse
    window exists at all. Returns True if a launch happened (needs the
    full load wait), False if an existing window was focused."""
    win = find_muse_window()
    if win is not None:
        try:
            win.activate()
            print("(using the Muse window already open)")
            return False
        except Exception:
            pass
    launch_muse(args)
    return True


def deliver(text, args):
    """Open Muse, click the message box, paste the text, press Enter."""
    import pyautogui
    import pyperclip
    # Deliberate: our clicks are single computed points inside the Muse
    # window, fired by the user's own voice. PyAutoGUI's corner fail-safe
    # only misfires here - it aborts if the mouse happens to be PARKED in a
    # screen corner (common when you're hands-free), killing the delivery.
    pyautogui.FAILSAFE = False
    launched = ensure_muse(args)
    time.sleep(args.load_wait if launched else 1.0)
    win = find_muse_window()
    if win is not None:
        try:
            win.activate()
            time.sleep(0.3)
            x = win.left + win.width // 2
            y = win.top + int(win.height * args.input_y)
        except Exception:
            w, h = pyautogui.size()
            x, y = w // 2, int(h * args.input_y)
    else:
        w, h = pyautogui.size()
        x, y = w // 2, int(h * args.input_y)
    pyautogui.click(x, y)  # the chat message box
    time.sleep(0.4)
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")


def voice_loop(args, status):
    """The whole listen -> greet -> record -> transcribe -> send cycle."""
    try:
        import sounddevice as sd
        from vosk import Model, SetLogLevel
        from faster_whisper import WhisperModel
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run:  py -3.12 -m pip install openwakeword vosk sounddevice "
              "faster-whisper pyttsx3 pyautogui pyperclip pygetwindow")
        status.set(ST_ERROR)
        return

    model_dir = (Path(args.model) if args.model
                 else Path(__file__).with_name("vosk-model-small-en-us-0.15"))
    if not model_dir.exists():
        print(f"Vosk model folder not found: {model_dir}")
        print("Download + unzip: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        status.set(ST_ERROR)
        return

    SetLogLevel(-1)
    print("Loading wake-word model...")
    wake_model = Model(str(model_dir))
    print(f"Loading Whisper '{args.whisper_model}' (first run downloads it, one time)...")
    whisper = WhisperModel(args.whisper_model, device="cpu", compute_type="int8")
    hey_path = (Path(args.hey_model) if args.hey_model
                else Path(__file__).with_name("hey_yami.onnx"))
    wake_path = (Path(args.wake_model) if args.wake_model
                 else Path(__file__).with_name("wake_up_yami.onnx"))
    missing = [p.name for p in (hey_path, wake_path) if not p.exists()]
    if missing:
        print("Trained wake-word model(s) not found: " + ", ".join(missing))
        print("Train them first (free - see README-training.md), then drop")
        print("the .onnx files next to this script.")
        status.set(ST_ERROR)
        return
    from openwakeword.model import Model as OwwModel
    print("Loading openWakeWord models (true phrases: Hey Yami / Wake up Yami)...")
    oww_model = OwwModel([str(hey_path), str(wake_path)], vad_threshold=0.5)
    print('Ready. "Wake up Yami" opens Muse; "Hey Yami" starts a talk. Ctrl+C to stop.')
    status.set(ST_LISTENING)

    while True:
        try:
            command = listen_for_wake(sd, oww_model, args.device, args.threshold)
            if command == "open":
                print(f'[{time.strftime("%H:%M:%S")}] "Wake up Yami" - opening Muse.')
                status.set(ST_OPENING)
                beep(660, 80, not args.no_beep)
                ensure_muse(args)
                time.sleep(args.cooldown)
                status.set(ST_LISTENING)
                continue
            print(f'[{time.strftime("%H:%M:%S")}] "Hey Yami" - talk mode.')
            status.set(ST_HEARD)
            beep(880, 120, not args.no_beep)
            speak("How can I help you?")
            audio = record_request(sd, args.device, wake_model)
            if audio is None:
                speak("I did not catch that.")
                status.set(ST_LISTENING)
                continue
            status.set(ST_WRITING)
            segments, _info = whisper.transcribe(audio, language="en", beam_size=1)
            text = "".join(s.text for s in segments).strip()
            if not text:
                speak("I did not catch that.")
                status.set(ST_LISTENING)
                continue
            print(f"You said: {text}")
            speak("Got it.")
            status.set(ST_SENDING)
            deliver(text, args)
            print("Sent to Muse. Back to listening...")
            status.set(ST_SENT)
            beep(1320, 90, not args.no_beep)
            time.sleep(args.cooldown)
            status.set(ST_LISTENING)
        except Exception as e:
            print(f"Error in voice loop: {e}")
            status.set(ST_ERROR)
            time.sleep(2)
            status.set(ST_LISTENING)


def run_overlay(status):
    """Floating always-on-top status pill (tkinter, ships with Python)."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Hey Yami")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.92)
    except Exception:
        pass
    root.configure(bg="#111111")

    frame = tk.Frame(root, bg="#111111", padx=10, pady=6)
    frame.pack()
    dot = tk.Label(frame, text="\u25cf", font=("Segoe UI", 11),
                   fg=ST_STARTING[1], bg="#111111")
    dot.pack(side="left")
    label = tk.Label(frame, text=ST_STARTING[0], font=("Segoe UI", 10),
                     fg="#f0f0f0", bg="#111111")
    label.pack(side="left", padx=(6, 0))

    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    x = root.winfo_screenwidth() - w - 16
    root.geometry(f"{w}x{h}+{x}+16")

    def quit_app(_event=None):
        os._exit(0)

    root.bind("<Button-3>", quit_app)  # right-click the pill to quit
    label.bind("<Button-3>", quit_app)
    dot.bind("<Button-3>", quit_app)

    current = [None]

    def tick():
        text, color = status.state
        if current[0] != (text, color):
            current[0] = (text, color)
            label.config(text=text)
            dot.config(fg=color)
            root.update_idletasks()
            nw = root.winfo_reqwidth()
            root.geometry(f"{nw}x{h}+{root.winfo_screenwidth() - nw - 16}+16")
        root.after(150, tick)

    tick()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


def main():
    args = parse_args()
    try:
        import sounddevice as sd
    except ImportError:
        print("Missing dependency. Run:  py -3.12 -m pip install sounddevice")
        return 1
    if args.list_devices:
        print(sd.query_devices())
        return 0

    status = Status()
    if args.no_overlay:
        try:
            voice_loop(args, status)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    try:
        import tkinter  # noqa: F401 - availability check only
        have_tk = True
    except ImportError:
        have_tk = False
        print("(tkinter unavailable - running without the status pill)")

    if not have_tk:
        try:
            voice_loop(args, status)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    worker = threading.Thread(target=voice_loop, args=(args, status), daemon=True)
    worker.start()
    run_overlay(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
