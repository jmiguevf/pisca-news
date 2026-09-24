#!/usr/bin/env python3
"""Trilhas originais do Pisca (sintetizadas aqui, sem direitos de terceiros).

Uso: python3 trilha.py [saida.mp3] [segundos] [NOME]
NOME: PULSO (padrao), CORRIDA, NOTURNO ou TENSAO. Sem NOME, escolhe pelo nome do arquivo.

PULSO   - leito de noticia: pulso constante, tique de relogio, baixo grave, la menor.
CORRIDA - mais rapida e clara, baixo sincopado, sem tique, re menor. Cara de mercado.
NOTURNO - mais lenta e quente, pad sustentado, bateria esparsa, mi menor. Cara de fim de dia.
TENSAO  - dramatica (23/09): batida de coracao, drone grave, tique de relogio, re menor com A no fim.

As tres sao deterministicas: mesma entrada, mesmo arquivo.
"""
import sys, subprocess, tempfile, os, wave
import numpy as np

SR = 44100
OUT  = sys.argv[1] if len(sys.argv) > 1 else "Pisca_trilha_PULSO.mp3"
DUR  = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0

# nome da trilha: 3o argumento, ou deduzido do nome do arquivo de saida
if len(sys.argv) > 3:
    NOME = sys.argv[3].upper()
else:
    base = os.path.basename(OUT).upper()
    NOME = next((n for n in ("CORRIDA", "NOTURNO", "PULSO", "TENSAO") if n in base), "PULSO")

N = int(SR * DUR)
buf = np.zeros(N, dtype=np.float64)


def put(sig, t):
    i = int(t * SR)
    if i >= N:
        return
    k = min(len(sig), N - i)
    buf[i:i + k] += sig[:k]


def env(n, a, d, curve=2.2):
    na = max(1, int(a * SR)); nd = max(1, n - na)
    return np.concatenate([np.linspace(0, 1, na), np.linspace(1, 0, nd) ** curve])


def kick(t, g=0.92, f0=105, queda=26, piso=44, dur=0.30):
    n = int(dur * SR); x = np.arange(n) / SR
    f = f0 * np.exp(-x * queda) + piso
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    put(s * env(n, 0.001, dur, 2.6) * g, t)


def sub(t, hz, dur, g=0.40):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * hz * x) + 0.22 * np.sin(4 * np.pi * hz * x)
    put(s * env(n, 0.012, dur, 1.5) * g, t)


def hat(t, open_=False, g=0.20):
    d = 0.16 if open_ else 0.045
    n = int(d * SR)
    rng = np.random.default_rng(int(t * 1000) % 99991)
    s = rng.standard_normal(n)
    s = np.diff(np.concatenate([[0.0], s]))
    put(s * env(n, 0.001, d, 3.0) * g, t)


def tick(t, g=0.30):
    n = int(0.030 * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * 2300 * x) * np.exp(-x * 190)
    rng = np.random.default_rng(int(t * 997) % 99991)
    s = s + 0.5 * rng.standard_normal(n) * np.exp(-x * 320)
    put(s * g, t)


def stab(t, hz, dur=0.42, g=0.17, brilho=4.2):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.zeros(n)
    for k in range(1, 9):
        s += np.sin(2 * np.pi * hz * k * x) / k
    s *= np.exp(-x * brilho)
    put(s * env(n, 0.006, dur, 2.0) * g, t)


def pad(t, hz, dur, g=0.10):
    """acorde sustentado e quente: tres vozes levemente desafinadas"""
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.zeros(n)
    for mult, det in ((1.0, 0.0), (1.5, 0.6), (2.0, -0.9)):     # raiz, quinta, oitava
        f = hz * mult + det
        s += np.sin(2 * np.pi * f * x) / mult
    a = min(0.35, dur * 0.3)
    n_a = max(1, int(a * SR)); n_d = max(1, n - n_a)
    e = np.concatenate([np.linspace(0, 1, n_a), np.linspace(1, 0, n_d) ** 1.2])
    put(s * e * g, t)


def riser(t, dur=1.8, g=0.15):
    n = int(dur * SR); x = np.arange(n) / SR
    rng = np.random.default_rng(7)
    s = rng.standard_normal(n) * (x / dur) ** 2
    s *= np.sin(2 * np.pi * (300 + 2400 * (x / dur)) * x) * 0.5 + 0.5
    put(s * g, t)


# ---------------------------------------------------------------- as tres trilhas

def build_pulso():
    """la menor: Am - F - C - G. Pulso em todos os tempos + tique de relogio."""
    bpm = 100.0; spb = 60.0 / bpm
    A, F, C, G = 110.0, 87.31, 130.81, 98.0
    prog = [A, A, F, F, C, C, G, G]
    riser(0.0, 1.8)
    beat = 0; t = 0.0
    while t < DUR:
        b = beat % 8; raiz = prog[b]
        kick(t)
        sub(t, raiz / 2, spb * 0.92)
        hat(t + spb / 2, open_=(b % 4 == 3))
        tick(t + spb / 4, g=0.22)
        tick(t + 3 * spb / 4, g=0.14)
        if b % 2 == 0:
            stab(t, raiz * 2)
        if b == 7:
            stab(t + spb / 2, raiz * 3, dur=0.30, g=0.13)
        beat += 1; t += spb


def build_corrida():
    """re menor: Dm - Bb - F - C. Mais rapida, baixo sincopado, sem tique."""
    bpm = 116.0; spb = 60.0 / bpm
    D, Bb, F, C = 146.83, 116.54, 174.61, 130.81
    prog = [D, D, Bb, Bb, F, F, C, C]
    riser(0.0, 1.4, g=0.13)
    beat = 0; t = 0.0
    while t < DUR:
        b = beat % 8; raiz = prog[b]
        kick(t, g=0.86, f0=120, queda=30, piso=48, dur=0.24)
        if b % 2 == 1:                                  # contratempo no bumbo
            kick(t + spb * 0.75, g=0.42, f0=118, queda=34, piso=50, dur=0.18)
        sub(t, raiz / 2, spb * 0.55, g=0.34)
        sub(t + spb * 0.5, raiz / 2, spb * 0.40, g=0.24)   # baixo sincopado
        hat(t + spb / 2, g=0.22)
        hat(t + spb / 4, g=0.11)
        hat(t + 3 * spb / 4, open_=(b % 4 == 3), g=0.15)
        if b % 2 == 0:
            stab(t, raiz, dur=0.30, g=0.15, brilho=3.0)
        if b in (3, 7):
            stab(t + spb * 0.5, raiz * 1.5, dur=0.26, g=0.13, brilho=2.6)
        beat += 1; t += spb


def build_noturno():
    """mi menor: Em - C - G - D. Mais lenta, pad sustentado, bateria esparsa."""
    bpm = 88.0; spb = 60.0 / bpm
    E, C, G, D = 82.41, 130.81, 98.0, 146.83
    prog = [E, E, C, C, G, G, D, D]
    beat = 0; t = 0.0
    while t < DUR:
        b = beat % 8; raiz = prog[b]
        if b % 2 == 0:                                   # pad de dois tempos
            pad(t, raiz * 2, spb * 2.05, g=0.115)
        if b in (0, 2, 4, 6):
            kick(t, g=0.70, f0=95, queda=22, piso=41, dur=0.34)
        if b in (2, 6):
            hat(t + spb, open_=True, g=0.11)
        else:
            hat(t + spb / 2, g=0.13)
        sub(t, raiz / 2, spb * 1.6, g=0.34) if b % 2 == 0 else None
        if b == 7:
            stab(t + spb / 2, raiz * 3, dur=0.50, g=0.10, brilho=5.5)
        beat += 1; t += spb


def build_tensao():
    """re menor: Dm - Bb - Gm - A (o A maior no fim puxa a tensao de volta).
    72 bpm, batida de coracao em todo tempo, drone grave por compasso, tique no contratempo."""
    bpm = 72.0; spb = 60.0 / bpm
    D, Bb, G, A = 73.42, 58.27, 49.0, 55.0
    prog = [D, Bb, G, A]
    riser(0.0, 2.2, g=0.12)
    beat = 0; t = 0.0
    while t < DUR:
        bar = (beat // 4) % 4; b = beat % 4; raiz = prog[bar]
        kick(t, g=0.82, f0=86, queda=20, piso=42, dur=0.36)            # tum
        kick(t + 0.23, g=0.46, f0=80, queda=22, piso=42, dur=0.28)     # -tum (coracao)
        tick(t + spb / 2, g=0.17)
        if b == 0:
            pad(t, raiz * 2, spb * 4.1, g=0.13)
            sub(t, raiz, spb * 3.9, g=0.34)
            stab(t, raiz * 2, dur=0.95, g=0.11, brilho=1.7)
        if b == 2:
            stab(t, raiz * 3, dur=0.35, g=0.06, brilho=4.0)
        if bar == 3 and b == 2:
            riser(t, spb * 2, g=0.09)
        beat += 1; t += spb


TRILHAS = {"PULSO": build_pulso, "CORRIDA": build_corrida, "NOTURNO": build_noturno, "TENSAO": build_tensao}
if NOME not in TRILHAS:
    sys.exit(f"trilha desconhecida: {NOME}. Use uma de: {', '.join(TRILHAS)}")
TRILHAS[NOME]()

# normaliza e aplica um limitador macio
buf /= max(1e-9, np.max(np.abs(buf)))
buf = np.tanh(buf * 1.45) / np.tanh(1.45)
buf *= 0.89
st = np.stack([buf, buf], axis=1)

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    wav = f.name
with wave.open(wav, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())

subprocess.run(["ffmpeg", "-y", "-i", wav,
                "-af", "acompressor=threshold=-14dB:ratio=3:attack=6:release=120,"
                       "alimiter=limit=0.95,aformat=sample_fmts=s16p",
                "-c:a", "libmp3lame", "-b:a", "192k", OUT],
               check=True, capture_output=True)
os.unlink(wav)
print(f"OK {OUT}  {NOME}  {DUR:.0f}s")
