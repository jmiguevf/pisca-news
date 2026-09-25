#!/usr/bin/env python3
"""Trilha dos Reels a partir das músicas que o José Miguel escolheu (pasta musicas/, 25/09/2026:
"use as músicas novas que coloquei na pasta").

- Revezamento: cada edição usa uma música diferente (dia do ano x edição), sem precisar guardar estado.
- Entra direto na parte forte da música (pula a introdução calma), para o gancho já abrir com peso.
- Soma as pancadas nos cortes (as mesmas da IMPACTO, "a do ET"), mais baixas, para marcar cada cartão.
- Volume final em -14 LUFS (grava da trilha_impacto).

Uso: python3 trilha_biblioteca.py saida.wav DURACAO "0,5.5,11" [--grandes "0,20"] [--musica nome.mp3]
"""
import argparse, datetime as dt, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trilha_impacto as TI   # noqa: E402

PASTA = Path(__file__).resolve().parent / "musicas"


def lista():
    return sorted(PASTA.glob("*.mp3"))


def escolhe(quando=None):
    fs = lista() + ["IMPACTO"]        # a "do ET" (gerada sob medida) entra no revezamento
    agora = quando or (dt.datetime.utcnow() - dt.timedelta(hours=3))
    slot = 0 if agora.hour < 10 else (1 if agora.hour < 15 else 2)
    return fs[(agora.toordinal() * 3 + slot) % len(fs)]


def le(arq):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-f", "f32le", "-ac", "2", "-ar", str(TI.SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(np.float64)


def ponto_forte(x, dur):
    """Primeiro trecho em que a música chega a 60% da energia máxima (janelas de 0,5 s), recuado 0,5 s."""
    w = TI.SR // 2
    n = len(x) // w
    rms = np.sqrt((x[: n * w] ** 2).mean(axis=1).reshape(n, w).mean(axis=1))
    alvo = np.argmax(rms >= 0.6 * rms.max()) if n else 0
    ini = max(0.0, alvo * 0.5 - 0.5)
    fim_max = len(x) / TI.SR - dur - 0.5
    return max(0.0, min(ini, fim_max))


def arranjo(dur, cortes, grandes=(), musica=None):
    arq = Path(musica) if musica else escolhe()
    if not arq.is_absolute() and not arq.exists():
        arq = PASTA / arq
    x = le(arq)
    ini = ponto_forte(x, dur)
    a = int(ini * TI.SR)
    trecho = x[a: a + int(dur * TI.SR)]
    if len(trecho) < int(dur * TI.SR):                      # música mais curta que o vídeo: repete
        reps = int(np.ceil(dur * TI.SR / max(1, len(x))))
        trecho = np.tile(x, (reps + 1, 1))[a: a + int(dur * TI.SR)]
    trecho = trecho / max(1e-9, np.max(np.abs(trecho)))
    m = TI.Mesa(dur)
    for c in sorted(set([0.0] + [c for c in cortes if c < dur])):
        TI.pancada(m, c, grande=any(abs(c - g) < 0.05 for g in grandes) or c == 0.0)
    hits = m.bus["bateria"] + m.bus["baixo"] + m.bus["musica"] + m.bus["fx"]
    hits = hits[: len(trecho)]
    hits = hits / max(1e-9, np.max(np.abs(hits)))
    mix = trecho * 0.85 + hits * 0.45
    n = int(1.2 * TI.SR)
    mix[-n:] *= np.linspace(1, 0, n)[:, None] ** 1.5
    print(f"trilha biblioteca: {arq.name} a partir de {ini:.1f}s")
    return mix / max(1e-9, np.max(np.abs(mix))), arq.name


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("saida"); ap.add_argument("duracao", type=float); ap.add_argument("cortes")
    ap.add_argument("--grandes", default=""); ap.add_argument("--musica", default=None)
    a = ap.parse_args()
    f = lambda s: [float(v) for v in s.split(",") if v.strip()]
    mix, nome = arranjo(a.duracao, f(a.cortes), f(a.grandes), a.musica)
    TI.grava(mix, a.saida)
    print("OK", a.saida, nome)
