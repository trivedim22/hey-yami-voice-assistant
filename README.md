# Hey Yami — Wake-Word Listener for Windows (openWakeWord edition)

Say **"Hey Yami"** and your PC opens Muse (https://muse.ai) in your browser.

This version uses **openWakeWord** — free, open-source, and fully on-device.
No account, no email gate, no AccessKey, nothing leaves your PC.
(The earlier Picovoice plan died at signup: it only accepts company emails.)

There is **one extra step** vs. Picovoice: the "Hey Yami" model doesn't exist
yet, so you train it once — free, in your browser, using synthetic voices
(no recordings of your own voice). ~30–45 minutes, mostly waiting.

---

## Part A — Train the "Hey Yami" model (one time, in your browser)

1. Open the official training notebook:
   https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb
   and click **"Open in Colab"** (sign in with any Google account).
2. In Colab: **Runtime → Change runtime type → select GPU (T4)** → Save.
3. Find the cell with `target_phrase` and set it to:
   `target_phrase = ["hey yami"]`
4. **Runtime → Run all.** The notebook generates thousands of synthetic
   "hey yami" clips with Piper TTS, then trains the model.
   - If it plays sample clips, listen: if the voice pronounces it wrong
     (e.g. "hey yammy"), stop, respell phonetically — try `"hey yah mee"` —
     and re-run. The phrase spelling only affects training, not what you say.
5. When it finishes (~30–45 min), download the exported model file
   **`hey_yami.onnx`** and save it **in the same folder as `hey_yami_oww.py`**
   from this package.

> If the notebook errors out (it is community-maintained), tell Yami — there is
> a fallback local trainer, but Colab works for most people.

---

## Part B — One-time PC setup (~5 minutes)

1. Install **Python 3.10–3.12** from https://www.python.org/downloads/
   — tick **"Add python.exe to PATH"** during setup.
   (Avoid 3.13 for now; some audio libraries lag behind it.)
2. Open Command Prompt and run:

```
pip install openwakeword sounddevice
```

That's everything — no keys, no accounts.

---

## Part C — Test it

Smoke-test the mic + pipeline first, using a built-in model (say "Hey Jarvis"):

```
python hey_yami_oww.py --test-builtin
```

If that opens your browser when you say "Hey Jarvis", everything works.
Then run the real thing (needs `hey_yami.onnx` from Part A beside the script):

```
python hey_yami_oww.py
```

Say **"Hey Yami"** → Muse opens. `Ctrl+C` stops it.

Run it silently (no console window) by double-clicking **`start_hey_yami.bat`**.

---

## Part D — Tuning

| Problem | Fix |
|---|---|
| False triggers (TV, other speech) | `python hey_yami_oww.py --threshold 0.65` |
| It misses you | Lower it: `--threshold 0.4`, and speak at normal volume near the mic |
| Opens Muse multiple times | It's already debounced (10 s) — raise with `--cooldown 20` |
| Wrong microphone | `python hey_yami_oww.py --list-devices`, then `--device N` |

A fresh custom model usually needs a little threshold tuning in your real
room — that's normal, not a failure.

---

## Autostart with Windows (optional)

1. Press `Win + R`, type `shell:startup`, Enter.
2. Copy a **shortcut** to `start_hey_yami.bat` into that folder.

## Troubleshooting

- **"Model file not found"** — `hey_yami.onnx` must sit next to the script
  (or pass `--model C:\path\to\hey_yami.onnx`).
- **Microphone blocked / silent errors** — Windows Settings → Privacy &
  security → Microphone → let desktop apps access it.
- **Privacy note:** the mic is processed locally by the model frame by frame;
  no audio is recorded, stored, or sent anywhere.

## Files in this package

- `hey_yami_oww.py` — the listener (openWakeWord + sounddevice)
- `start_hey_yami.bat` — silent launcher
- `README.md` — this guide
- *(you add)* `hey_yami.onnx` — your trained model from Part A
