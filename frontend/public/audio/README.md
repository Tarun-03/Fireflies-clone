# Original sample audio

`welcome.m4a` contains 1,400 seconds of quiet synthesized tones at 220, 261.63, 329.63, and 293.66 Hz. It contains no meeting recording, third-party samples, speech, or personal data. The notebook labels it as sample audio.

The original waveform and encoding are dedicated to the public domain under CC0-1.0. Generate the waveform using `python3 scripts/generate_sample_audio.py` from the repository root, then encode on macOS:

```sh
afconvert -f m4af -d aac -b 16000 /tmp/welcome.wav frontend/public/audio/welcome.m4a
```

The bundled file is mono AAC, 8 kHz, approximately 2.2 MB. The generation script requires only Python's standard library; playback does not require a local encoder.
