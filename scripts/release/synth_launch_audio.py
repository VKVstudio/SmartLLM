#!/usr/bin/env python3
"""Procedural multi-layer dark-cinema audio synthesizer for SmartLLM v0.0.2-beta launch videos.

Synthesizes frame-accurate stereo 48 kHz soundtracks using multi-layer additive/subtractive
synthesis and normalizes to broadcast EBU R128 / streaming standard (`loudnorm=I=-14:TP=-1.5:LRA=11`)
via `/usr/bin/ffmpeg` into `.wav` and `.m4a` (`AAC 192 kbps`):
- Layer 1: 48 Hz warm sub-bass pulse + 96 Hz harmonic body locked to composition beat grid.
- Layer 2: Dark-cinema obsidian harmonic pad (fifth + octave + minor-seventh Detuned stereo chorus).
- Layer 3: Frame-synced tactile UI micro-transients (damped 1.9 kHz / 2.6 kHz glass ticks) at scene cuts.
- Layer 4: Pre-transition harmonic risers (110 Hz -> 440 Hz smooth sweep over 0.9s before key scenes).
"""

from __future__ import annotations

import argparse
import array
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import wave

ROOT = Path(__file__).resolve().parents[2]
AUDIO_OUT_DIR = ROOT / "media" / "launch_videos" / "audio"
SAMPLE_RATE = 48000

COMPOSITIONS: dict[str, dict] = {
    "youtube_16x9": {
        "duration_sec": 75.0,
        "bpm": 96.0,
        "base_freq": 48.0,
        "scene_cuts_sec": [0.0, 3.0, 15.0, 33.0, 52.0, 65.0],
        "ui_ticks_sec": [3.2, 6.5, 9.8, 15.2, 19.0, 23.5, 28.0, 33.2, 39.0, 45.0, 52.2, 58.0, 65.2],
    },
    "reddit_16x9": {
        "duration_sec": 50.0,
        "bpm": 108.0,
        "base_freq": 48.0,
        "scene_cuts_sec": [0.0, 4.0, 16.0, 30.0, 42.0],
        "ui_ticks_sec": [0.5, 4.2, 8.0, 12.0, 16.2, 21.0, 25.5, 30.2, 35.5, 42.2],
    },
    "linkedin_4x5": {
        "duration_sec": 55.0,
        "bpm": 92.0,
        "base_freq": 48.0,
        "scene_cuts_sec": [0.0, 4.0, 16.0, 31.0, 45.0],
        "ui_ticks_sec": [4.2, 9.0, 16.2, 22.0, 27.0, 31.2, 37.5, 45.2],
    },
    "reels_9x16": {
        "duration_sec": 40.0,
        "bpm": 120.0,
        "base_freq": 48.0,
        "scene_cuts_sec": [float(t) for t in range(0, 40, 2)],
        "ui_ticks_sec": [float(t) + 0.15 for t in range(0, 40, 2)],
    },
    "smoke_test_4s": {
        "duration_sec": 4.0,
        "bpm": 120.0,
        "base_freq": 48.0,
        "scene_cuts_sec": [0.0, 2.0],
        "ui_ticks_sec": [0.25, 1.0, 2.0, 3.0],
    },
}


def _synthesize_raw_stereo_wav(spec: dict, raw_wav_path: Path) -> None:
    duration_sec = float(spec["duration_sec"])
    bpm = float(spec["bpm"])
    f0 = float(spec.get("base_freq", 48.0))
    scene_cuts = [float(x) for x in spec.get("scene_cuts_sec", [])]
    ui_ticks = [float(x) for x in spec.get("ui_ticks_sec", [])]

    total_samples = int(round(duration_sec * SAMPLE_RATE))
    pcm = array.array("h", [0] * (total_samples * 2))

    beat_hz = bpm / 60.0
    two_pi = 2.0 * math.pi
    inv_sr = 1.0 / SAMPLE_RATE

    # Pre-render basic wave cycle tables or fast per-sample loop
    w_f0 = two_pi * f0 * inv_sr
    w_f1 = two_pi * (f0 * 2.0) * inv_sr
    w_pad1_l = two_pi * (f0 * 3.0) * inv_sr
    w_pad1_r = two_pi * (f0 * 3.004) * inv_sr
    w_pad2_l = two_pi * (f0 * 4.0) * inv_sr
    w_pad2_r = two_pi * (f0 * 3.996) * inv_sr
    w_pad3 = two_pi * (f0 * 4.5) * inv_sr
    w_beat = two_pi * beat_hz * inv_sr
    w_lfo = two_pi * 0.18 * inv_sr

    fade_in_samples = min(int(0.35 * SAMPLE_RATE), total_samples // 4)
    fade_out_samples = min(int(0.85 * SAMPLE_RATE), total_samples // 4)

    sin = math.sin
    exp = math.exp

    for i in range(total_samples):
        # Master fade envelope
        env = 1.0
        if i < fade_in_samples:
            env = i / float(fade_in_samples)
        elif i > total_samples - fade_out_samples:
            env = (total_samples - i) / float(fade_out_samples)

        # Beat pulse (0.35 .. 1.0 smooth sub-bass throb)
        beat_mod = 0.62 + 0.38 * (0.5 * (1.0 + sin(i * w_beat - 1.2)))
        lfo = 0.75 + 0.25 * sin(i * w_lfo)

        # Layer 1: 48 Hz sub-bass + 96 Hz warm overtone
        sub = (0.42 * sin(i * w_f0) + 0.16 * sin(i * w_f1)) * beat_mod

        # Layer 2: Stereo dark-cinema pad
        pad_l = (0.11 * sin(i * w_pad1_l) + 0.07 * sin(i * w_pad2_l) + 0.04 * sin(i * w_pad3)) * lfo
        pad_r = (0.11 * sin(i * w_pad1_r) + 0.07 * sin(i * w_pad2_r) + 0.04 * sin(i * w_pad3 + 0.7)) * lfo

        val_l = (sub + pad_l) * env
        val_r = (sub + pad_r) * env

        pcm[2 * i] = max(-32000, min(32000, int(val_l * 24000.0)))
        pcm[2 * i + 1] = max(-32000, min(32000, int(val_r * 24000.0)))

    # Layer 3: Overlay frame-synced UI micro-transients (22 ms damped glass/relay click)
    tick_len = int(0.024 * SAMPLE_RATE)
    for t_sec in ui_ticks:
        start_idx = int(round(t_sec * SAMPLE_RATE))
        if start_idx < 0 or start_idx >= total_samples:
            continue
        end_idx = min(total_samples, start_idx + tick_len)
        for k in range(end_idx - start_idx):
            dt = k * inv_sr
            decay = exp(-dt * 190.0)
            click = (0.28 * sin(two_pi * 1880.0 * dt) + 0.16 * sin(two_pi * 2820.0 * dt)) * decay
            delta = int(click * 22000.0)
            idx = start_idx + k
            pcm[2 * idx] = max(-32760, min(32760, pcm[2 * idx] + delta))
            pcm[2 * idx + 1] = max(-32760, min(32760, pcm[2 * idx + 1] + int(delta * 0.92)))

    # Layer 4: Pre-transition harmonic risers (0.85s sweep into each scene cut > 0.9s)
    riser_len = int(0.85 * SAMPLE_RATE)
    for cut_sec in scene_cuts:
        if cut_sec < 0.9:
            continue
        end_idx = min(total_samples, int(round(cut_sec * SAMPLE_RATE)))
        start_idx = max(0, end_idx - riser_len)
        span = max(1, end_idx - start_idx)
        phase = 0.0
        for k in range(span):
            prog = k / float(span)
            freq = 96.0 * (1.0 + 2.5 * (prog * prog))
            phase += two_pi * freq * inv_sr
            amp = 0.18 * (prog * prog) * (1.0 - 0.15 * prog)
            r_val = int(sin(phase) * amp * 22000.0)
            idx = start_idx + k
            pcm[2 * idx] = max(-32760, min(32760, pcm[2 * idx] + r_val))
            pcm[2 * idx + 1] = max(-32760, min(32760, pcm[2 * idx + 1] + r_val))

    raw_wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(raw_wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())


def render_and_normalize_track(comp_id: str, out_dir: Path = AUDIO_OUT_DIR) -> dict:
    if comp_id not in COMPOSITIONS:
        raise ValueError(f"Unknown composition '{comp_id}'. Choices: {sorted(COMPOSITIONS)}")
    spec = COMPOSITIONS[comp_id]
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
    ffprobe_bin = shutil.which("ffprobe") or "/usr/bin/ffprobe"

    norm_wav = out_dir / f"{comp_id}.wav"
    norm_m4a = out_dir / f"{comp_id}.m4a"

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix=f"smartllm_audio_{comp_id}_") as tmp:
        raw_wav = Path(tmp) / f"{comp_id}_raw.wav"
        _synthesize_raw_stereo_wav(spec, raw_wav)

        # Normalize to -14 LUFS WAV
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(raw_wav),
                "-af",
                "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "2",
                str(norm_wav),
            ],
            check=True,
            timeout=60,
        )

        # Encode normalized WAV to AAC .m4a
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(norm_wav),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(norm_m4a),
            ],
            check=True,
            timeout=60,
        )

    probe = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(norm_m4a),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    probe_data = json.loads(probe.stdout)
    elapsed = round(time.perf_counter() - t0, 3)
    return {
        "composition": comp_id,
        "duration_target_sec": spec["duration_sec"],
        "wav_path": str(norm_wav),
        "wav_bytes": norm_wav.stat().st_size,
        "m4a_path": str(norm_m4a),
        "m4a_bytes": norm_m4a.stat().st_size,
        "ffprobe": probe_data,
        "elapsed_sec": elapsed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize procedural dark-cinema launch audio tracks.")
    parser.add_argument("--smoke", action="store_true", help="Synthesize and verify 4s smoke track (< 3s CPU)")
    parser.add_argument("--all", action="store_true", help="Synthesize all 4 production launch soundtracks")
    parser.add_argument("--composition", type=str, help="Synthesize a single composition track")
    parser.add_argument("--out-dir", type=Path, default=AUDIO_OUT_DIR)
    args = parser.parse_args(argv)

    if args.smoke:
        res = render_and_normalize_track("smoke_test_4s", out_dir=args.out_dir)
        print(json.dumps({"status": "PASS", "smoke": res}, indent=2))
        return 0

    if args.composition:
        res = render_and_normalize_track(args.composition, out_dir=args.out_dir)
        print(json.dumps({"status": "PASS", "track": res}, indent=2))
        return 0

    # Default or --all: render the 4 main tracks
    tracks = []
    for cid in ("youtube_16x9", "reddit_16x9", "linkedin_4x5", "reels_9x16"):
        tracks.append(render_and_normalize_track(cid, out_dir=args.out_dir))
    print(json.dumps({"status": "PASS", "tracks": tracks}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
