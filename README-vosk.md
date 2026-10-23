# Hey Yami — Vosk edition (instant, no training)

The zero-setup listener: works the minute you install it — no Colab training.
Trade-off vs. the openWakeWord edition (see README.md): Vosk's dictionary has
no "yami", so it listens for the soundalike **"wake up yummy"** and fires when
you say "Wake up Yami" (one vowel apart; the grammar forces the match).
Occasionally it may miss if you lean hard on the "Yah" sound, and the real
word "yummy" in conversation could fire it — the cooldown keeps that a
nuisance, not a problem.

## Setup (~5 minutes)

1. Python 3.10–3.12 installed (tick "Add python.exe to PATH").
2. In Command Prompt:

```
pip install vosk sounddevice
```

3. Download the small model (40 MB) and unzip it **next to `hey_yami_vosk.py`**:
   https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   (You should end up with a folder named `vosk-model-small-en-us-0.15`.)

## Run

```
python hey_yami_vosk.py
```

Say **"Wake up Yami"** → Muse opens. `Ctrl+C` stops it.

Wrong mic? `python hey_yami_vosk.py --list-devices` then `--device N`.
Too eager / too deaf in practice? That's exactly what the openWakeWord
edition (true trained phrase, tunable threshold) is for — see README.md.
