#!/usr/bin/env python3
"""TENSÃO — trilha original de suspense para Reels de guerra/ameaça (24/09/2026).

Pedido dele no Reels do Putin: "Coloca música de tensão". Mesmas pancadas nos cortes da IMPACTO, mas sem
batida de trap: drone grave em ré, cordas dissonantes em trêmulo (ré + mi bemol), coração que acelera a cada
cartão e tique de relógio. Tudo sintetizado aqui (sem direitos de terceiros); sai em -14 LUFS.

Uso: python3 trilha_tensao.py saida.wav DURACAO "0,4.8,..." [--grande "0,28.4"] [--final 50.6]
Trocar a trilha de um vídeo pronto:  python3 trilha_tensao.py --video reels.mp4 saida.mp4 (lê cortes do log)
"""
import sys, argparse, subprocess
import numpy as np
import trilha_impacto as TI
from trilha_impacto import SR, Mesa, _x, _fade, _filtro, _ruido, pancada, subida, kick, grava


def drone(m, a, b, g):
    x = _x(b - a)
    s = np.zeros(len(x))
    for f, amp in ((36.71, 1.0), (55.0, 0.6), (73.42, 0.45)):
        for det in (-0.18, 0.18):
            for k in range(1, 9):
                s += amp * np.sin(2 * np.pi * (f + det) * k * x) / k
    s = _filtro(s, "lowpass", 260)
    s *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.23 * x)
    env = np.minimum(1, x / 0.4)
    m.put("musica", _fade(s * env, 5, 300), a, g=g)


def cordas(m, a, b, intensidade):
    x = _x(b - a)
    trem = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 6.5 * x))
    s = np.zeros(len(x))
    notas = [293.66, 311.13, 440.0] + ([587.33, 622.25] if intensidade > 0.5 else [])
    for f in notas:
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * x)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        s += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    cresc = (0.35 + 0.65 * (x / max(x[-1], 1e-3)) ** 1.6)
    m.put("musica", _fade(s * trem * cresc, 200, 250), a, pan=-0.15, g=0.018 + 0.02 * intensidade)


def coracao(m, a, b, bpm, g=0.55):
    per = 60.0 / bpm
    t = a + 0.15
    while t < b - 0.35:
        kick(m, t, g=g)
        kick(m, t + 0.19, g=g * 0.6)
        t += per


def tique(m, a, b, g=0.10):
    t = a
    i = 0
    while t < b - 0.3:
        x = _x(0.03)
        s = _filtro(_ruido(len(x)), "bandpass", [2500, 6500]) * np.exp(-x * 260)
        m.put("fx", s, t, pan=0.35 if i % 2 else -0.35, g=g)
        t += 0.5; i += 1


def arranjo(dur, cortes, grandes, final):
    m = Mesa(dur)
    cortes = sorted(set(round(c, 3) for c in cortes if c < dur))
    if not cortes or cortes[0] > 0.001:
        cortes = [0.0] + cortes
    secoes = list(zip(cortes, cortes[1:] + [dur]))
    n = len(secoes)
    for si, (a, b) in enumerate(secoes):
        grande = any(abs(a - g) < 0.05 for g in grandes)
        pancada(m, a, grande=grande)
        if a > 0.05:
            subida(m, a, dur=min(0.8, max(0.3, (a - secoes[si - 1][0]) * 0.3)), g=0.22)
        frac = si / max(1, n - 1)
        drone(m, a, b + 0.3, g=0.05)
        if final is not None and a >= final - 0.01:
            continue                                   # fecho: só pancada e drone
        cordas(m, a, b, frac)
        coracao(m, a, b, bpm=66 + 34 * frac)
        tique(m, a, b, g=0.06 + 0.05 * frac)
    leito = m.bus["bateria"] * 0.9 + m.bus["musica"] * 1.0
    duck = np.ones(m.N)
    for a, _ in secoes:
        i0, k = int(a * SR), int(0.35 * SR)
        duck[i0:i0 + k] = np.minimum(duck[i0:i0 + k], 0.5 + 0.5 * np.linspace(0, 1, len(duck[i0:i0 + k])) ** 2)
    mix = leito * duck[:, None] + m.bus["fx"] * 1.2
    mix = mix[: int(dur * SR)]
    n_out = int(1.2 * SR)
    mix[-n_out:] *= np.linspace(1, 0, n_out)[:, None] ** 1.5
    mix /= max(1e-9, np.max(np.abs(mix)))
    return mix


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("saida"); ap.add_argument("duracao", type=float); ap.add_argument("cortes")
    ap.add_argument("--grande", default="0"); ap.add_argument("--final", type=float, default=None)
    a = ap.parse_args()
    cortes = [float(c) for c in a.cortes.split(",") if c.strip()]
    grandes = [float(c) for c in a.grande.split(",") if c.strip()]
    grava(arranjo(a.duracao, cortes, grandes, a.final), a.saida)
    print(f"OK {a.saida}  TENSÃO  {a.duracao:.1f}s")
