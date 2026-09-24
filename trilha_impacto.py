#!/usr/bin/env python3
"""IMPACTO — trilha original do Pisca que BATE NOS CORTES do Reels (23/09/2026).

O José Miguel pediu "músicas mais impactantes". A biblioteca de músicas do Instagram não existe na API
(só no app), então a nossa trilha passou a ser feita sob medida para cada vídeo:
- cada troca de cartão cai numa PANCADA (sub grave + prato), com SUBIDA antes e a batida saindo
  no último tempo — o "drop" das edições de Reels;
- base trap escura a 140 bpm (meio-tempo): 808 saturado (aparece até no alto-falante do celular),
  palma no 3, chimbal com viradas, sino FM em ré menor (Dm-Bb-Gm-A) com eco, pad baixo;
- pancada GRANDE (com "braam" de metais graves) no gancho e onde o JSON pedir;
- sai em -14 LUFS, pico -1 dBTP. Sem direitos de terceiros: tudo sintetizado aqui.

Uso:
  python3 trilha_impacto.py saida.wav DURACAO "0,4.8,12.8,..." [--grande "0,12.8,50.4"] [--final 50.4]
  --final: a partir desse corte (o fecho) a batida para; fica pancada + 808 + sino e o fade.
"""
import sys, os, re, subprocess, tempfile, wave, json, argparse
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
BPM = 140.0
SPB = 60.0 / BPM

# ré menor: Dm - Bb - Gm - A  (raiz do 808 em Hz, notas do sino)
PROG = [
    dict(raiz=73.42, sino=[587.33, 880.00, 698.46, 440.00], pad=[146.83, 174.61, 220.00]),   # Dm
    dict(raiz=58.27, sino=[587.33, 698.46, 466.16, 349.23], pad=[116.54, 146.83, 174.61]),   # Bb
    dict(raiz=98.00, sino=[587.33, 466.16, 392.00, 293.66], pad=[98.00, 116.54, 146.83]),    # Gm
    dict(raiz=55.00, sino=[554.37, 659.25, 440.00, 329.63], pad=[110.00, 138.59, 164.81]),   # A
]
PADRAO_SINO = [0, 2, 1, 2, 0, 3, 1, 2]          # colcheias por compasso (índices em sino[])


class Mesa:
    def __init__(self, dur):
        self.N = int(SR * (dur + 2.0))
        self.bus = {k: np.zeros((self.N, 2)) for k in ("bateria", "baixo", "musica", "fx")}

    def put(self, bus, sig, t, pan=0.0, g=1.0):
        i = int(round(t * SR))
        if i >= self.N or i + len(sig) <= 0:
            return
        if i < 0:
            sig = sig[-i:]; i = 0
        k = min(len(sig), self.N - i)
        a = (pan + 1) * np.pi / 4                   # pan de potência constante
        self.bus[bus][i:i + k, 0] += sig[:k] * np.cos(a) * g
        self.bus[bus][i:i + k, 1] += sig[:k] * np.sin(a) * g


def _x(dur):
    return np.arange(int(dur * SR)) / SR


def _fade(s, ms_in=2, ms_out=15):
    n1, n2 = int(ms_in * SR / 1000), int(ms_out * SR / 1000)
    if n1: s[:n1] *= np.linspace(0, 1, n1)
    if n2 and len(s) > n2: s[-n2:] *= np.linspace(1, 0, n2)
    return s


def _filtro(s, tipo, f):
    sos = butter(2, f, btype=tipo, fs=SR, output="sos")
    return sosfilt(sos, s)


_rng = np.random.default_rng(23092026)
def _ruido(n):
    return _rng.standard_normal(n)


# ------------------------------------------------------------------ instrumentos
def kick(m, t, g=0.9):
    x = _x(0.28)
    f = 48 + 110 * np.exp(-x * 38)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 11)
    click = _filtro(_ruido(len(x)), "highpass", 2500) * np.exp(-x * 900) * 0.35
    m.put("bateria", _fade(np.tanh((s + click) * 1.6)), t, g=g)


def b808(m, t, hz, dur, g=0.8):
    x = _x(dur)
    f = hz * (1 + 0.9 * np.exp(-x * 45))              # cai para a nota em ~40 ms
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = np.exp(-x * 1.6)
    s = np.tanh(s * env * 3.2) / np.tanh(3.2)         # saturação: harmônicos que o celular toca
    m.put("baixo", _fade(s, 2, 25), t, g=g)


def palma(m, t, g=0.55):
    x = _x(0.30)
    n = _filtro(_ruido(len(x)), "bandpass", [900, 3200])
    env = np.zeros(len(x))
    for d in (0.0, 0.010, 0.021):
        i = int(d * SR)
        env[i:] += np.exp(-(x[: len(x) - i]) * 180)
    env += 0.55 * np.exp(-x * 16) * (x > 0.021)
    corpo = np.sin(2 * np.pi * 190 * x) * np.exp(-x * 30) * 0.5
    m.put("bateria", _fade(n * env * 0.8 + corpo), t, pan=0.05, g=g)


def chimbal(m, t, aberto=False, g=0.17, pan=0.25):
    d = 0.16 if aberto else 0.04
    x = _x(d)
    n = _filtro(_ruido(len(x)), "highpass", 7000)
    m.put("bateria", _fade(n * np.exp(-x * (18 if aberto else 110))), t, pan=pan, g=g)


def sino(m, t, hz, g=0.10, pan=-0.3):
    x = _x(1.3)
    mod = np.sin(2 * np.pi * hz * 3.5 * x) * 2.0 * np.exp(-x * 7)
    s = np.sin(2 * np.pi * hz * x + mod) * np.exp(-x * 3.6)
    s = _fade(s, 1, 40)
    m.put("musica", s, t, pan=pan, g=g)
    for k, ganho in ((1, 0.33), (2, 0.14)):          # eco de colcheia pontuada, do outro lado
        m.put("musica", s, t + k * SPB * 0.75, pan=-pan, g=g * ganho)


def pad(m, t, freqs, dur, g=0.045):
    x = _x(dur)
    s = np.zeros(len(x))
    for f in freqs:
        for det in (-0.35, 0.35):
            for k in range(1, 9):
                s += np.sin(2 * np.pi * (f + det) * k * x + k) / (k ** 1.4)
    a = min(0.25, dur * 0.3)
    env = np.minimum(1, x / a) * np.minimum(1, (dur - x) / 0.2)
    m.put("musica", s * env / len(freqs), t, g=g)


def subida(m, t_fim, dur=1.0, g=0.30):
    """ruído que abre e sobe de tom, terminando EXATAMENTE no corte"""
    x = _x(dur)
    n = _ruido(len(x))
    # passa-banda que "sobe" de 400 Hz a 6 kHz: 8 bandas fixas, cruzadas suavemente no tempo
    centros = 400 * (15 ** (np.arange(8) / 7))
    pos = (x / dur) * 7                            # 0..7: em que banda estamos
    s = np.zeros(len(x))
    for j, fc in enumerate(centros):
        banda = _filtro(n, "bandpass", [fc * 0.7, min(fc * 1.45, SR / 2 - 100)])
        s += banda * np.clip(1 - np.abs(pos - j), 0, 1)
    tom = np.sin(2 * np.pi * np.cumsum(180 * (6 ** (x / dur))) / SR) * 0.25
    env = (x / dur) ** 2.2
    m.put("fx", _fade((s + tom) * env, 5, 8), t_fim - dur, g=g)


def pancada(m, t, grande=False):
    x = _x(1.8 if grande else 1.2)
    f = 28 + 42 * np.exp(-x * 5)                  # sub que despenca
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * (2.2 if grande else 3.2))
    sub = np.tanh(sub * 2.2) / np.tanh(2.2)
    m.put("fx", _fade(sub, 1, 60), t, g=0.95)
    kick(m, t, g=1.0)
    xc = _x(2.2 if grande else 1.3)                # prato
    prato = _filtro(_ruido(len(xc)), "highpass", 3500) * np.exp(-xc * (1.8 if grande else 3.0))
    m.put("fx", _fade(prato, 1, 80), t, pan=0.1, g=0.30 if grande else 0.22)
    if grande:
        braam(m, t)


def braam(m, t, dur=2.4):
    """metais graves de trailer: pilha de serras em ré, filtro abrindo e fechando"""
    x = _x(dur)
    corte = 180 + 1300 * np.sin(np.pi * np.minimum(1, x / (dur * 0.9))) ** 0.8
    s = np.zeros(len(x))
    for f in (36.71, 73.42, 110.0, 146.83):
        for det in (-0.25, 0.25):
            for k in range(1, int(1600 / f) + 1):
                ganho = np.clip(1.2 - (k * f) / corte, 0, 1)
                s += ganho * np.sin(2 * np.pi * (f + det) * k * x) / k
    env = np.minimum(1, x / 0.06) * np.exp(-x * 0.9)
    s = np.tanh(s * env * 0.9)
    m.put("fx", _fade(s, 3, 200), t, g=0.28)


# ------------------------------------------------------------------ arranjo
def arranjo(dur, cortes, grandes, final):
    m = Mesa(dur)
    cortes = sorted(set(round(c, 3) for c in cortes if c < dur))
    if not cortes or cortes[0] > 0.001:
        cortes = [0.0] + cortes
    secoes = list(zip(cortes, cortes[1:] + [dur]))
    eventos_808 = []
    compasso_global = 0
    for si, (a, b) in enumerate(secoes):
        grande = any(abs(a - g) < 0.05 for g in grandes)
        pancada(m, a, grande=grande)
        if a > 0.05:
            subida(m, a, dur=min(1.0, max(0.3, (a - secoes[si - 1][0]) * 0.4)))
        if final is not None and a >= final - 0.01:
            ch = PROG[compasso_global % 4]
            eventos_808.append((a, ch["raiz"], 2.4))
            pad(m, a, ch["pad"], b - a + 0.5, g=0.06)
            sino(m, a + SPB, ch["sino"][0], g=0.12)
            sino(m, a + 2 * SPB, ch["sino"][2], g=0.09)
            continue
        k = 0
        while True:
            t = a + k * SPB
            if t >= b - SPB * 0.98:                  # último tempo antes do corte: sem batida
                break
            bar, beat = divmod(k, 4)
            ch = PROG[(compasso_global + bar) % 4]
            if beat == 0:
                kick(m, t)
                eventos_808.append((t, ch["raiz"], SPB * 1.5))
                pad(m, t, ch["pad"], min(4 * SPB, b - t), g=0.045)
            if beat == 1:
                eventos_808.append((t + SPB * 0.5, ch["raiz"], SPB * 1.0))
            if beat == 2:
                palma(m, t)
            if beat == 3 and bar % 2 == 1:
                kick(m, t + SPB * 0.5, g=0.6)
                eventos_808.append((t + SPB * 0.5, ch["raiz"] * 1.5 if bar % 4 == 3 else ch["raiz"], SPB * 0.5))
            # chimbal: colcheias; virada de semicolcheias no fim de compasso ímpar; tercina de fusas a cada 4
            if beat == 3 and bar % 4 == 3:
                for i in range(6):
                    chimbal(m, t + i * SPB / 6, g=0.12 + 0.012 * i)
            elif beat == 3 and bar % 2 == 1:
                for i in range(4):
                    chimbal(m, t + i * SPB / 4, g=0.15)
            else:
                chimbal(m, t, g=0.17)
                chimbal(m, t + SPB / 2, aberto=(beat == 1 and bar % 2 == 0), g=0.13)
            # sino em colcheias
            for h in range(2):
                idx = PADRAO_SINO[(beat * 2 + h) % 8]
                sino(m, t + h * SPB / 2, ch["sino"][idx], g=0.085 if h else 0.10)
            k += 1
        compasso_global += (k + 3) // 4
    # 808 monofônico: cada nota corta a anterior
    eventos_808.sort()
    for i, (t, hz, d) in enumerate(eventos_808):
        prox = eventos_808[i + 1][0] if i + 1 < len(eventos_808) else t + d
        b808(m, t, hz, max(0.05, min(d, prox - t)))
    # silencia bateria e 808 no último tempo antes de cada corte (o "respiro" antes da pancada)
    gate = np.ones(m.N)
    for a, b in secoes[1:]:
        i0, i1 = int((a - SPB * 0.98) * SR), int(a * SR)
        f = int(0.02 * SR)
        gate[i0:i1] = 0.0
        gate[max(0, i0 - f):i0] = np.minimum(gate[max(0, i0 - f):i0], np.linspace(1, 0, i0 - max(0, i0 - f)))
    for bus in ("bateria", "baixo"):
        m.bus[bus] *= gate[:, None]
    # leito (batida, 808, sino) mais baixo que as pancadas: é o contraste que dá o impacto
    baixo = sosfilt(butter(2, 35, btype="highpass", fs=SR, output="sos"), m.bus["baixo"], axis=0)
    leito = m.bus["bateria"] * 0.62 + baixo * 0.42 + m.bus["musica"] * 0.95
    # o leito abaixa por 0,35 s depois de cada corte (a pancada fica sozinha na frente)
    duck = np.ones(m.N)
    for a, _ in secoes:
        i0, n = int(a * SR), int(0.35 * SR)
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 0.45 + 0.55 * np.linspace(0, 1, len(duck[i0:i0 + n])) ** 2)
    mix = leito * duck[:, None] + m.bus["fx"] * 1.25
    mix = mix[: int(dur * SR)]
    n_out = int(1.2 * SR)                                  # fade final de 1,2 s (como o motor)
    mix[-n_out:] *= np.linspace(1, 0, n_out)[:, None] ** 1.5
    mix /= max(1e-9, np.max(np.abs(mix)))
    return mix


def grava(mix, out):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        bruto = f.name
    with wave.open(bruto, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32000).astype("<i2").tobytes())
    # ganho até -14 LUFS e limitador de pico (sem compressor: as pancadas continuam saltando)
    def lufs(arq, af="anull"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", arq, "-af", af + ",ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    ganho = -14.0 - lufs(bruto)[0]
    teto = 0.80
    for _ in range(6):
        af = f"volume={ganho:.2f}dB,alimiter=limit={teto:.3f}:attack=5:release=80:level=disabled"
        i, pico = lufs(bruto, af)
        if pico > -1.0:                      # pico real acima de -1 dBTP: baixa o teto do limitador
            teto *= 10 ** ((-1.1 - pico) / 20)
            continue
        if abs(i + 14.0) < 0.3:
            break
        ganho += (-14.0 - i)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", bruto, "-af", af, "-ar", "44100", out], check=True)
    os.unlink(bruto)
    print(f"  {i:.1f} LUFS, pico {pico:.1f} dBFS (ganho {ganho:+.1f} dB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("saida"); ap.add_argument("duracao", type=float); ap.add_argument("cortes")
    ap.add_argument("--grande", default="0"); ap.add_argument("--final", type=float, default=None)
    a = ap.parse_args()
    cortes = [float(c) for c in a.cortes.split(",") if c.strip()]
    grandes = [float(c) for c in a.grande.split(",") if c.strip()]
    grava(arranjo(a.duracao, cortes, grandes, a.final), a.saida)
    print(f"OK {a.saida}  IMPACTO  {a.duracao:.1f}s  cortes={cortes}")
