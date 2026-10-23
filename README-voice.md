# Hey Yami — hands-free voice loop (assistant edition)

Two voice commands, no clicking anything:

- **"Wake up Yami"** — just opens Muse in your browser.
- **"Hey Yami"** — the talk command (your replacement for the speak button):
  1. Your PC answers out loud: **"How can I help you?"** (Windows built-in voice)
  2. You speak your request — it stops recording when you stop talking
  3. **Whisper** transcribes it (accurate, runs only for the request)
  4. Muse opens, your words are pasted into the chat and sent automatically

Muse's own app has no hands-free voice mode on your plan, so your PC does
the ears and the mouth; Muse stays the brain in the chat.

## Setup (one extra install)

You already have Vosk + the model from the Vosk edition. Add:

```
py -3.12 -m pip install faster-whisper pyttsx3 pyautogui pyperclip pygetwindow
```

First run downloads the Whisper "base" model (~150 MB) — one time only.

## Run

```
py -3.12 hey_yami_assistant.py
```

Wait for the `Ready` line. Then just talk — either command works any time.
Keep the console window visible on the first runs — it prints exactly what it
heard you say, so you can see transcription quality.

## Opens in the installed Muse app, not a new tab

By default (`--open-mode app`) the script is **focus-first**: it looks for a
Muse window that is *already open* and simply brings it to the front — no
new window, no new tab. Only when no Muse window exists at all does it
launch your **installed Muse web app** via its Start Menu shortcut. (An
earlier version launched the shortcut every time, and each launch spawned a
fresh app window instead of reusing the open one.) The paste click is aimed
inside the Muse window itself, wherever it sits on screen. If the app
shortcut isn't found, it falls back to the browser. To force the old
launch-every-time behavior: `--open-mode browser`.
Note: in app mode your spoken message goes to the chat that's open in the
app window.

## Tuning

| Problem | Fix |
|---|---|
| It pastes before the page loads | `--load-wait 8` |
| Log shows "PyAutoGUI fail-safe triggered" | Old-version issue: pyautogui aborts if your mouse is parked in a screen corner. The script now disables that fail-safe for its own two clicks — update the script file |
| The click misses the chat box | `--input-y 0.88` (higher number = lower on screen) |
| Transcription is rough | `--whisper-model small` (slower, smarter) |
| It cuts you off mid-sentence | You paused > ~1.75 s — speak in one flow, or ask Yami to lengthen the pause |
| It misses your soft voice | Fixed by design: the recorder has **no loudness gate at all** — it detects speech with Vosk itself, the same ears as the wake-word listener (which hears you fine), and Whisper transcribes afterwards. Speak as softly as you like |
| Wrong mic | `--list-devices`, then `--device N` |
| Fires on its own (TV, nearby talk) | Already mitigated: it triggers only on Vosk's **final** phrase result, not mid-speech guesses — so it reacts after a short pause following the phrase. For even fewer false fires, the trained openWakeWord edition (README.md) is the thorough cure |

## The status pill (so you can SEE it working)

Silent mode has no console, so the script shows a small always-on-top **pill**
in the top-right corner of your screen:

- Grey **"Starting..."** → models loading
- Green **"Listening - say Hey Yami"** → it's hearing the room, waiting
- Red **"Heard you - speak now!"** → wake word caught, it's recording you
- Amber **"Writing it down..."** → transcribing
- Blue **"Sending to Muse..."** → delivering, then green **"Sent"**

Short beeps also mark the wake catch and the send (mute with `--no-beep`).
**Right-click the pill to quit the listener.** Disable the pill entirely with
`--no-overlay`. (The little mic icon in your taskbar only says *some* app is
using the microphone — it can't tell you any of this.)

## Silent mode (.bat) and the log file

`start_hey_yami_assistant.bat` runs the loop with no console via pythonw.
In silent mode the script writes everything it would print into
**`hey_yami_log.txt`** in the same folder — if it ever seems unresponsive,
open that file: it shows the loading lines, every command it heard, and any
error. (An earlier silent version died invisibly because pythonw has no
console for print() to write to; the scripts now redirect to the log.)

## Honest notes

- The greeting voice is the Windows system voice (a bit robotic). Natural
  neural voices are possible later via edge-tts if you want them.
- Muse's reply still appears as **text in the chat** — reading it aloud
  automatically is a possible phase 2 (the script would watch the page and
  speak the reply). Ask Yami if you want it.
- Everything (wake word, recording, transcription) happens on your PC.
  Your words only go to Muse as the chat message you asked to send.
