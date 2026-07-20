"""Generate the cohermes README banner (wide)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

S = 2
W, H = 1280 * S, 360 * S
OUT = "/storage/Work/cohermes/docs/assets/banner.png"
BG = (0x0f, 0x11, 0x17); INK = (0xe7, 0xeb, 0xf3); INK_SOFT = (0xaa, 0xb3, 0xc5)
INK_FAINT = (0x7b, 0x84, 0x99); TEAL = (0x22, 0xc3, 0xd6); TEAL2 = (0x19, 0xb8, 0x9a)
BLUE = (0x5b, 0x8d, 0xef); CYAN = (0xbd, 0xf0, 0xea); PANEL = (0x1b, 0x1f, 0x2a); LINE = (0x2c, 0x33, 0x46)
MONT = "/usr/share/fonts/julietaula-montserrat-fonts/"; SCP = "/usr/share/fonts/adobe-source-code-pro-fonts/"


def f(p, s): return ImageFont.truetype(p, int(s * S))
def mont(w, s): return f(MONT + {"x": "Montserrat-ExtraBold.otf", "b": "Montserrat-Bold.otf", "r": "Montserrat-Regular.otf"}[w], s)
def mono(s): return f(SCP + "SourceCodePro-Semibold.otf", s)


bg = np.zeros((H, W, 3), dtype=np.float32); bg[:] = np.array(BG, dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def glow(cx, cy, r, c, k):
    a = np.exp(-(((xx - cx * S) ** 2 + (yy - cy * S) ** 2) / ((r * S) ** 2))) * k
    for i in range(3): bg[:, :, i] += c[i] * a
glow(1050, 70, 520, TEAL, 0.30); glow(1180, 300, 460, TEAL2, 0.14); glow(150, 320, 480, BLUE, 0.08)
np.clip(bg, 0, 255, out=bg)
img = Image.fromarray(bg.astype(np.uint8), "RGB"); d = ImageDraw.Draw(img, "RGBA")


def measure(t, ft): b = d.textbbox((0, 0), t, font=ft); return b[2] - b[0], b[3] - b[1], b
def ltext(x, y, t, ft, fill): _, _, b = measure(t, ft); d.text((x * S - b[0], y * S - b[1]), t, font=ft, fill=fill)
def spaced(x, y, t, ft, fill, tr):
    cx = x * S
    for c in t:
        _, _, b = measure(c, ft); d.text((cx - b[0], y * S - b[1]), c, font=ft, fill=fill); cx += measure(c, ft)[0] + tr * S
def grad_left(x, y, t, ft, c1, c2):
    w, h, b = measure(t, ft); pad = 12 * S
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0); ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), t, font=ft, fill=255)
    ga = np.zeros((h + 2 * pad, w + 2 * pad, 3), dtype=np.uint8); tv = np.linspace(0, 1, w + 2 * pad)
    for i in range(3): ga[:, :, i] = (c1[i] + (c2[i] - c1[i]) * tv).astype(np.uint8)
    img.paste(Image.fromarray(ga, "RGB"), (int(x * S - pad), int(y * S - pad)), m)


MX = 90
spaced(MX + 4, 92, "AN EXTENSION OF HERMES   ·   POWERED BY CONTEXT GRAPH", mono(14), INK_FAINT, 4)
# wordmark
wf = mont("x", 104); wco = measure("co", wf)[0] / S
ltext(MX, 128, "co", wf, TEAL); grad_left(MX + wco, 128, "hermes", wf, CYAN, BLUE)
ltext(MX + 2, 258, "A team of AI coding agents that share one brain.", mont("r", 26), INK_SOFT)
# right-side chips
for i, txt in enumerate(["decisions", "code reviews", "tasks", "commits", "learnings"]):
    tw = measure(txt, mont("b", 15))[0] / S; x = 812 + (i % 2) * 210; y = 150 + (i // 2) * 56
    d.rounded_rectangle([x * S, y * S, (x + tw + 34) * S, (y + 38) * S], radius=999 * S,
                        fill=(0x1b, 0x1f, 0x2a, 255), outline=TEAL2 + (200,), width=int(1.4 * S))
    _, _, b = measure(txt, mont("b", 15)); d.text(((x + 17) * S - b[0], (y + 10) * S - b[1]), txt, font=mont("b", 15), fill=(0x7f, 0xe3, 0xcf))

final = img.resize((1280, 360), Image.LANCZOS); final.save(OUT); print("saved", OUT, final.size)
