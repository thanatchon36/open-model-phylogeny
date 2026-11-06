"""Shared constants for analysis and figures."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, RES, FIG = ROOT / "data/processed", ROOT / "results", ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
SNAP = pd.Timestamp("2026-11-05")
REL = ["finetune", "adapter", "quantized", "merge", "unknown"]

SUPER = [
    ("Qwen", r"^qwen"), ("Llama", r"^(llama|codellama)"), ("Gemma", r"^gemma"),
    ("Mistral", r"^(mistral|mixtral|ministral|magistral|devstral|codestral|pixtral)"),
    ("FLUX", r"^flux"), ("Stable Diffusion", r"^(stable-diffusion|sdxl|sd\d|sd$)"),
    ("BERT family", r"^(bert|distilbert|roberta|xlm-roberta|deberta|modernbert|electra|albert|camembert|multilingual-e5|e5)"),
    ("Whisper", r"^whisper"), ("SmolLM", r"^smol"), ("DeepSeek", r"^deepseek"), ("Phi", r"^phi"),
    ("T5", r"^(t5|flan-t5|mt5|byt5)"),
]
# order around the hero circle: text LLMs, encoders, speech, image generation, long tail
RING_ORDER = ["Qwen", "DeepSeek", "Llama", "Mistral", "Gemma", "Phi", "SmolLM", "T5", "BERT family",
              "Whisper", "Stable Diffusion", "FLUX", "Other"]
PALETTE = {
    "Qwen": "#9D7BFF", "Llama": "#2FD9F5", "Gemma": "#4C8DFF", "BERT family": "#3EE08F",
    "FLUX": "#FF5FB0", "Mistral": "#FF8C42", "Stable Diffusion": "#FFD447", "SmolLM": "#C7F464",
    "Whisper": "#5EEAD4", "DeepSeek": "#FFB4A2", "Phi": "#FF6B6B", "T5": "#E879F9", "Other": "#7C8799",
}
REL_COLORS = {"finetune": "#38E1FF", "adapter": "#A78BFA", "quantized": "#FFC857", "merge": "#FF5C8A",
              "unknown": "#9AA4B2"}
BG = "#070A12"
INK = "#E8ECF4"
MUTED = "#8A94A6"


def super_of(families):
    s = pd.Series(families)
    out = np.full(len(s), "Other", dtype=object)
    for name, rx in reversed(SUPER):
        out[s.str.contains(rx, regex=True).values] = name
    return out


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def font_setup():
    import matplotlib
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "Inter" in f:
            font_manager.fontManager.addfont(f)
    matplotlib.rcParams["font.family"] = ["Inter", "DejaVu Sans"]
    matplotlib.rcParams["svg.fonttype"] = "none"
