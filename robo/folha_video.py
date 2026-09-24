#!/usr/bin/env python3
"""Folha de contato do Reels pronto: 1 quadro a cada ~4 s, com as linhas da área segura (250 e 1520 px) marcadas.
Uso: python3 robo/folha_video.py reels.mp4 folha.jpg"""
import subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

video, saida = sys.argv[1], sys.argv[2]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                           capture_output=True, text=True).stdout.strip() or 0)
n = max(4, min(16, int(dur // 4)))
quadros = []
with tempfile.TemporaryDirectory() as tmp:
    for i in range(n):
        t = dur * (i + 0.5) / n
        f = Path(tmp) / f"q{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-y", str(f)])
        if f.exists():
            im = Image.open(f).convert("RGB")
            d = ImageDraw.Draw(im)
            for y in (250, 1520):
                d.line([(0, y), (im.width, y)], fill=(255, 0, 0), width=4)
            d.text((20, 20), f"{t:.1f}s", fill=(255, 255, 0))
            quadros.append(im.resize((270, 480)))
cols = 4
linhas = (len(quadros) + cols - 1) // cols
folha = Image.new("RGB", (cols * 270, linhas * 480), "black")
for i, q in enumerate(quadros):
    folha.paste(q, ((i % cols) * 270, (i // cols) * 480))
folha.save(saida, "JPEG", quality=85)
print("folha:", saida, len(quadros), "quadros")
