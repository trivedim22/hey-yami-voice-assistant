# Train Yami properly — real wake-word models for the real phrases

Right now the working assistant (Vosk edition) can't hear the word "yami" at
all — it's not in Vosk's dictionary, so it listens for the soundalikes
"hey yummy" / "wake up yummy". It works, but it's a hack.

This upgrade trains two small neural-net models with **openWakeWord** that
hear the **actual phrases**:

- `hey_yami.onnx` — "Hey Yami" → start a talk
- `wake_up_yami.onnx` — "Wake up Yami" → just open Muse

Training is **free** (Google Colab), takes ~30–45 min per phrase, and is
almost entirely waiting — the notebook generates thousands of synthetic
voices saying your phrase (Piper TTS), mixes them against hours of
background speech/noise, and trains a tiny classifier. No recording,
no account signups beyond a Google account, no API keys.

This is openWakeWord's official automatic training notebook — the same
method behind its bundled models.

---

## Part 1 — Train "Hey Yami"

1. Open the openWakeWord repo: https://github.com/dscripka/openWakeWord
   Go into the **notebooks** folder and open **automatic_model_training.ipynb**,
   then click the **Open in Colab** button at the top of the file.
2. In Colab: **Runtime → Change runtime type → GPU (T4)** → Save.
   (Free tier is fine.)
3. Find the configuration cell near the top and set the target phrase to:

   ```
   target_phrase = "hey yami"
   ```

4. **Runtime → Run all.** Now wait. It installs tools, synthesizes the
   training voices, downloads negative/background data, trains, and runs
   an evaluation. Keep the tab open; ~30–45 min is normal.
5. When it finishes, download the trained model — the notebook saves it
   as a file named after your phrase (**hey_yami.onnx**). If the download
   has any other name, rename it to exactly `hey_yami.onnx`.

## Part 2 — Train "Wake up Yami"

Same notebook, second run:

1. **Runtime → Restart session** (fresh start).
2. Set the target phrase to:

   ```
   target_phrase = "wake up yami"
   ```

3. **Runtime → Run all**, wait again, download the model and make sure
   it is named exactly `wake_up_yami.onnx`.

## Part 3 — Install on the PC

1. Stop the old listener (right-click the status pill → quit, or run
   `taskkill /IM pythonw.exe /F`).
2. One-time install:
   ```
   py -3.12 -m pip install openwakeword
   ```
3. Copy these into `C:\Users\mahar\Desktop\yami voice` (replace if asked):
   - `hey_yami.onnx`
   - `wake_up_yami.onnx`
   - `hey_yami_assistant_oww.py`
   - `start_hey_yami_assistant_oww.bat`
4. Swap the startup shortcut: in `shell:startup`, remove the OLD
   assistant bat's shortcut and add one for `start_hey_yami_assistant_oww.bat`.
   Exactly **one** listener in startup — two would fight over the mic.
5. Double-click `start_hey_yami_assistant_oww.bat`. The pill appears.
   Test both phrases.

The Vosk model folder stays where it is — the new assistant still uses
Vosk for one small job (deciding when you stopped talking while it
records your request). The wake-word ears are 100% the new models.

## Tuning, if needed

Default threshold is 0.5 — the same value openWakeWord's own models use.

- **TV / other people trigger it** → raise the threshold. Test from a
  console in the folder:
  ```
  py -3.12 hey_yami_assistant_oww.py --threshold 0.65
  ```
- **It misses you** → lower it: `--threshold 0.4`.
- Once you find your number, add it to the .bat's last line, e.g.
  `... hey_yami_assistant_oww.py" --threshold 0.65`.

## Honest expectations

A synthetic-only model is good, not magic: expect it to clearly beat the
"yummy" soundalike hack — real phrase, far fewer weird fires — but your
room, mic, and voice are unique. If accuracy still isn't where you want
it, Phase 2 is adding ~30 short recordings of YOUR voice saying the
phrase into the training mix (the project's detailed notebook supports
this). Ask Yami (the assistant, not the wake word) to set that up.
