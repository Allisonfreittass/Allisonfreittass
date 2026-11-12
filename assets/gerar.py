"""Gera as imagens do README do perfil no sistema Rastros.

Cada imagem sai em duas versões: -noite (escuro, padrão) e -neblina (claro).
Todo texto vira contorno (path), então a Instrument Serif e a JetBrains Mono
aparecem iguais no GitHub sem carregar fonte nenhuma.

Uso:  python3 gerar.py <pasta-das-fontes>
      (precisa de fonttools e uharfbuzz; fontes: InstrumentSerif-Regular/Italic,
       JetBrainsMono-Regular/Medium .ttf)
"""
import html
import math
import os
import sys

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONTES = sys.argv[1] if len(sys.argv) > 1 else 'fontes'
SAIDA = os.path.dirname(os.path.abspath(__file__))

# ─────────── Tokens Rastros ───────────
TEMAS = {
    'noite': dict(
        fundo='#090E10', elev='#0E1619', hover='#142024',
        tinta='#E6E9E6', suave='#A9B4B2', fraca='#7E8B8A',
        linha='rgba(214,228,226,.09)', forte='rgba(214,228,226,.22)',
        estanho='#A9BCBD', estanho_linha='rgba(169,188,189,.34)',
        lanterna='#E0483F', brilho='rgba(224,72,63,.55)', luz='rgba(224,72,63,.16)',
        sobre_tinta='#090E10', chuva='200,218,222', nevoa='#A9B4B2', nevoa_a=(.06, .05, .07),
        lua='rgba(214,228,226,.20)',
    ),
    'neblina': dict(
        fundo='#E9EDEC', elev='#F3F5F4', hover='#DCE2E1',
        tinta='#0E1619', suave='#3D4A4B', fraca='#546163',
        linha='rgba(14,22,25,.10)', forte='rgba(14,22,25,.22)',
        estanho='#4F6366', estanho_linha='rgba(79,99,102,.40)',
        lanterna='#B3342B', brilho='rgba(179,52,43,.30)', luz='rgba(179,52,43,.08)',
        sobre_tinta='#E9EDEC', chuva='14,22,25', nevoa='#FFFFFF', nevoa_a=(.55, .45, .6),
        lua='rgba(255,255,255,.75)',
    ),
}


# ─────────── Texto em contorno ───────────
class Fonte:
    def __init__(self, nome):
        caminho = os.path.join(FONTES, nome)
        self.tt = TTFont(caminho)
        self.glyphs = self.tt.getGlyphSet()
        self.upem = self.tt['head'].unitsPerEm
        with open(caminho, 'rb') as f:
            self.hb = hb.Font(hb.Face(hb.Blob(f.read())))
        self.ordem = self.tt.getGlyphOrder()

    def _molda(self, texto):
        buf = hb.Buffer()
        buf.add_str(texto)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {'kern': True, 'liga': True})
        return buf.glyph_infos, buf.glyph_positions

    def largura(self, texto, tam, track=0.0):
        _, pos = self._molda(texto)
        s = tam / self.upem
        return sum(p.x_advance for p in pos) * s + track * tam * max(0, len(pos) - 1)

    def path(self, texto, tam, x, y, track=0.0, ancora='start'):
        infos, pos = self._molda(texto)
        s = tam / self.upem
        w = self.largura(texto, tam, track)
        if ancora == 'middle':
            x -= w / 2
        elif ancora == 'end':
            x -= w
        partes, cx = [], x
        for info, p in zip(infos, pos):
            nome = self.ordem[info.codepoint]
            pen = SVGPathPen(self.glyphs, ntos=lambda v: ('%.1f' % v).rstrip('0').rstrip('.'))
            gx, gy = cx + p.x_offset * s, y - p.y_offset * s
            self.glyphs[nome].draw(TransformPen(pen, (s, 0, 0, -s, gx, gy)))
            d = pen.getCommands()
            if d:
                partes.append(d)
            cx += p.x_advance * s + track * tam
        return ''.join(partes)


SERIF = Fonte('InstrumentSerif-Regular.ttf')
ITALICO = Fonte('InstrumentSerif-Italic.ttf')
MONO = Fonte('JetBrainsMono-Regular.ttf')
MONO_M = Fonte('JetBrainsMono-Medium.ttf')


def txt(fonte, texto, tam, x, y, cor, track=0.0, ancora='start', extra=''):
    return '<path fill="%s" %s d="%s"/>' % (cor, extra, fonte.path(texto, tam, x, y, track, ancora))


def rotulo(texto, x, y, cor, tam=13, ancora='start', fonte=None):
    """Rótulo mono em caixa alta com tracking .08em, como o token `rotulo`.
    O GitHub mostra as imagens a ~65% do tamanho, então o corpo é ampliado (ROT)
    para o rótulo chegar à tela com uns 11–12px, como na landing."""
    return txt(fonte or MONO_M, texto.upper(), tam * ROT, x, y, cor, .08, ancora)


ROT = 1.38


def svg(w, h, titulo, corpo, estilo=''):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n') % (w, h, w, h, html.escape(titulo), html.escape(titulo),
                                                ('<style>%s</style>' % estilo) if estilo else '', corpo)


def leque(x, y, w, cor):
    """O leque Art Deco da marca (viewBox 100×52), na largura w."""
    k = w / 100
    return ('<g transform="translate(%.1f %.1f) scale(%.3f)">'
            '<g fill="none" stroke="%s" stroke-width="%.2f">'
            '<path d="M2 50 A48 48 0 0 1 98 50"/><path d="M14 50 A36 36 0 0 1 86 50" opacity=".6"/>'
            '<path d="M50 50V4M50 50L26 10.4M50 50L74 10.4M50 50L9.6 26M50 50L90.4 26"/></g>'
            '<path d="M40 50 A10 10 0 0 1 60 50 Z" fill="%s"/></g>') % (x, y, k, cor, 1.3 / k, cor)


def salvar(nome, tema, conteudo):
    with open(os.path.join(SAIDA, '%s-%s.svg' % (nome, tema)), 'w', encoding='utf-8') as f:
        f.write(conteudo)


# ─────────── Floresta (mesmo desenho da landing) ───────────
def floresta(seed, camadas, largura):
    s = [seed]

    def rnd():
        s[0] = (s[0] * 16807) % 2147483647
        return s[0] / 2147483647

    def pinheiro(x, base, h, w):
        n, step, W, L, R = 8, h / 9, w / 2, [], []
        for k in range(n):
            yk = base - step * k - step * .3
            o = W * (1 - k / n) * (.85 + rnd() * .3)
            L += [(x - o, yk), (x - o * .3, yk - step * 1.25)]
            R += [(x + o, yk + step * .1), (x + o * .3, yk - step * 1.2)]
        p = 'M%.1f %.1f' % (x - W * .12, base)
        p += ''.join(' L%.1f %.1f' % q for q in L)
        p += ' L%.1f %.1f' % (x, base - h)
        p += ''.join(' L%.1f %.1f' % q for q in reversed(R))
        return p + ' L%.1f %.1f Z' % (x + W * .12, base)

    saida = []
    for cor, base, hmin, hmax, gap, fundo in camadas:
        d, x = '', -20.0
        while x < largura + 40:
            h = hmin + rnd() * (hmax - hmin)
            d += pinheiro(x, base + rnd() * 14, h, h * .3)
            x += gap * (.55 + rnd() * .8)
        d += 'M0 %d H%d V%d H0 Z' % (base, largura, fundo)
        saida.append('<path fill="%s" d="%s"/>' % (cor, d))
    return ''.join(saida)


def onda(x0, x1, meio, amp):
    """A linha de sinal da landing, congelada em t = 0."""
    pts = []
    for i in range(0, 301):
        u = i / 300
        env = math.exp(-((u - .5) / .22) ** 2) * .85 + .08
        y = meio + math.sin(u * 40) * math.sin(u * 6) * env * amp + math.sin(u * 130) * env * amp * .083
        pts.append((x0 + (x1 - x0) * u, y))
    return 'M' + ' L'.join('%.1f %.1f' % p for p in pts)


# ─────────── Banner ───────────
def banner(t, nome):
    W, H = 1280, 420
    c = TEMAS[t]
    estilo = (
        '.chuva{animation:cai 1.1s linear infinite}.chuva2{animation:cai2 1.9s linear infinite}'
        '@keyframes cai{to{transform:translate(-36px,200px)}}@keyframes cai2{to{transform:translate(-47px,260px)}}'
        '.nv{animation:deriva 46s ease-in-out infinite alternate}.nv2{animation-duration:70s;animation-direction:alternate-reverse}'
        '.nv3{animation-duration:90s}@keyframes deriva{to{transform:translateX(-140px)}}'
        '.farol{offset-path:path("%s");animation:corre 12s linear infinite}'
        '@keyframes corre{from{offset-distance:0%%}to{offset-distance:100%%}}'
        '@media (prefers-reduced-motion:reduce){.chuva,.chuva2,.nv,.farol{animation:none}.farol{offset-distance:62%%}}'
    ) % onda(56, 1224, 300, 24)
    rgb = c['chuva']
    defs = (
        '<defs>'
        '<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
        '<stop offset=".55" stop-color="%s"/><stop offset=".8" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<radialGradient id="lua" cx="1010" cy="118" r="210" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="%s"/><stop offset=".4" stop-color="%s" stop-opacity=".35"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="sinal" x1="56" x2="1224" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="%s" stop-opacity="0"/>'
        '<stop offset=".12" stop-color="%s"/><stop offset=".88" stop-color="%s"/><stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>'
        '<filter id="nevoa" x="-20%%" y="-200%%" width="140%%" height="500%%"><feGaussianBlur stdDeviation="16"/></filter>'
        '<filter id="glow" x="-300%%" y="-300%%" width="700%%" height="700%%"><feGaussianBlur stdDeviation="5"/></filter>'
        '<pattern id="gotas" width="160" height="200" patternUnits="userSpaceOnUse">'
        '<path stroke="rgba(%s,.13)" stroke-width=".9" d="M20 10l-3 17M88 64l-4 22M140 120l-3 16M52 150l-4 20M118 6l-2 13M8 98l-3 18"/></pattern>'
        '<pattern id="gotas2" width="210" height="260" patternUnits="userSpaceOnUse">'
        '<path stroke="rgba(%s,.08)" stroke-width=".8" d="M30 30l-2 12M120 90l-2 14M180 200l-2 11M70 220l-2 13M160 20l-2 10"/></pattern>'
        '</defs>'
    ) % (c['fundo'], c['elev'], c['hover'], c['fundo'], c['lua'], c['lua'], c['lua'],
         c['tinta'], c['tinta'], c['tinta'], c['tinta'], rgb, rgb)
    a1, a2, a3 = c['nevoa_a']
    mata = floresta(7, [
        (c['hover'], 300, 80, 150, 22, H),
        (c['elev'], 345, 100, 175, 29, H),
        (c['fundo'], 392, 120, 200, 40, H),
    ], W)
    nevoa = (
        '<g filter="url(#nevoa)">'
        '<rect class="nv" x="-80" y="250" width="1500" height="34" rx="17" fill="%s" opacity="%s"/>'
        '<rect class="nv nv2" x="-160" y="318" width="1600" height="30" rx="15" fill="%s" opacity="%s"/>'
        '<rect class="nv nv3" x="-60" y="384" width="1500" height="40" rx="20" fill="%s" opacity="%s"/></g>'
    ) % (c['nevoa'], a1, c['nevoa'], a2, c['nevoa'], a3)
    nome_tam = 150
    corpo = (
        defs
        + '<rect width="%d" height="%d" fill="url(#ceu)"/>' % (W, H)
        + '<circle cx="1010" cy="118" r="210" fill="url(#lua)"/>'
        + mata + nevoa
        + rotulo('Software engineer · Full-stack · Backend · AI', 56, 62, c['suave'])
        + rotulo('Varginha, BR · Open to relocation · NL / EU', 1224, 62, c['suave'], ancora='end')
        + txt(SERIF, 'Allison Freitas', nome_tam, 50, 238, c['tinta'], -.035)
        + '<path d="%s" fill="none" stroke="url(#sinal)" stroke-width="1.3" opacity=".8"/>' % onda(56, 1224, 300, 24)
        + '<g class="farol"><circle r="11" fill="%s" filter="url(#glow)"/><circle r="3.6" fill="%s"/></g>' % (c['brilho'], c['lanterna'])
        + txt(ITALICO, 'Systems that keep running when nobody is watching.', 34, 56, 380, c['suave'])
        + rotulo('allisonfreittass.github.io ↗', 1224, 372, c['fraca'], 12, 'end')
        + '<g class="chuva"><rect x="0" y="-200" width="1320" height="620" fill="url(#gotas)"/></g>'
        + '<g class="chuva2"><rect x="0" y="-260" width="1340" height="680" fill="url(#gotas2)"/></g>'
    )
    corpo = '<g>%s</g>' % corpo
    salvar('banner', t, svg(W, H, nome, '<clipPath id="q"><rect width="%d" height="%d" rx="6"/></clipPath><g clip-path="url(#q)">%s</g>' % (W, H, corpo), estilo))


# ─────────── Números ───────────
def numeros(t):
    W, H = 1280, 150
    c = TEMAS[t]
    itens = [('2', '', 'REST APIs in production at F2'), ('6', '', 'Own systems, open source'),
             ('498', '/500', 'SM83 opcodes validated'), ('2022', '', 'Coding since')]
    corpo = '<path d="M0 .5H%dM0 %0.1fH%d" stroke="%s"/>' % (W, H - .5, W, c['forte'])
    col = W / 4
    for i, (n, suf, rot) in enumerate(itens):
        x = i * col + (8 if i == 0 else 32)
        if i:
            corpo += '<path d="M%.1f 24V126" stroke="%s"/>' % (i * col + .5, c['linha'])
        corpo += txt(SERIF, n, 76, x, 90, c['tinta'], -.02)
        if suf:
            corpo += txt(SERIF, suf, 34, x + SERIF.largura(n, 76, -.02) + 4, 90, c['fraca'])
        corpo += rotulo(rot, x + 2, 126, c['fraca'], 11)
    salvar('numeros', t, svg(W, H, '2 REST APIs in production at F2 · 6 own open-source systems · 498/500 SM83 opcodes validated · coding since 2022', corpo))


# ─────────── Cabeçalho de seção ───────────
def cabeca(t, chave, num, titulo, italico, direita):
    W, H = 1280, 150
    c = TEMAS[t]
    corpo = leque(0, 6, 64, c['estanho'])
    corpo += rotulo(num, 82, 36, c['estanho'], 13)
    x = 0
    if titulo:
        corpo += txt(SERIF, titulo, 84, x - 3, 126, c['tinta'], -.02)
        x += SERIF.largura(titulo, 84, -.02) + 14
    if italico:
        corpo += txt(ITALICO, italico, 84, x - 3, 126, c['suave'], -.02)
    if direita:
        corpo += rotulo(direita, W, 122, c['fraca'], 12, 'end')
    corpo += '<path d="M0 %.1fH%d" stroke="%s"/>' % (H - .5, W, c['linha'])
    salvar('titulo-' + chave, t, svg(W, H, (titulo + ' ' + italico).strip(), corpo))


# ─────────── Visão, na moldura Deco ───────────
def visao(t):
    W, H = 1280, 400
    c = TEMAS[t]
    corpo = (
        '<defs><radialGradient id="vl" cx="300" cy="0" r="520" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient></defs>'
    ) % (c['forte'], c['forte'])
    corpo += '<rect x=".5" y=".5" width="%d" height="%d" rx="6" fill="%s" stroke="%s"/>' % (W - 1, H - 1, c['elev'], c['linha'])
    corpo += '<rect x="1" y="1" width="760" height="%d" fill="url(#vl)" opacity=".5"/>' % (H - 2)
    # cantos Deco em estanho
    k, m = 30, 14
    for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        corpo += '<path d="M%d %dV%dH%d M%d %dV%dH%d" fill="none" stroke="%s"/>' % (
            x, y + sy * k, y, x + sx * k, x + sx * 6, y + sy * (k - 10), y + sy * 6, x + sx * (k - 10), c['estanho_linha'])
    corpo += '<path d="M764.5 40V360" stroke="%s"/>' % c['linha']
    # esquerda
    corpo += rotulo('Featured · Personal research · 2026', 64, 76, c['estanho'])
    corpo += txt(SERIF, 'Visão', 132, 58, 196, c['tinta'], -.03)
    px = 58 + SERIF.largura('Visão', 132, -.03) + 2
    corpo += '<circle cx="%.1f" cy="187" r="16" fill="%s" opacity=".6" filter="url(#vg)"/>' % (px + 10, c['brilho'])
    corpo += txt(SERIF, '.', 132, px, 196, c['lanterna'])
    corpo += '<defs><filter id="vg" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="8"/></filter></defs>'
    corpo += rotulo('Trace · Introspection', 64, 252, c['estanho'], 12)
    corpo += txt(ITALICO, 'An agent born without a name', 34, 64, 296, c['tinta'])
    corpo += txt(ITALICO, 'that decides who it is.', 34, 64, 336, c['tinta'])
    # direita: roteiro
    x0 = 820
    corpo += '<circle cx="%d" cy="72" r="4" fill="%s"/>' % (x0 + 4, c['lanterna'])
    corpo += rotulo('Cognitive architecture', x0 + 18, 76, c['suave'], 12)
    corpo += rotulo('Roadmap · phases 0–9', x0, 128, c['fraca'], 12)
    feitas, construidas = {0, 1, 3, 4, 6}, {2, 5, 9}
    bw, gap, by, bh = 36, 5.5, 146, 60
    for i in range(10):
        x = x0 + i * (bw + gap)
        if i in feitas:
            corpo += '<rect x="%.1f" y="%d" width="%d" height="%d" fill="%s"/>' % (x, by, bw, bh, c['tinta'])
            cor = c['sobre_tinta']
        elif i in construidas:
            corpo += '<rect x="%.1f" y="%d" width="%d" height="%d" fill="%s" stroke="%s"/>' % (x + .5, by + .5, bw - 1, bh - 1, c['luz'], c['lanterna'])
            cor = c['lanterna']
        else:
            corpo += '<rect x="%.1f" y="%d" width="%d" height="%d" fill="none" stroke="%s"/>' % (x + .5, by + .5, bw - 1, bh - 1, c['forte'])
            cor = c['fraca']
        corpo += txt(MONO, str(i), 16, x + bw / 2, by + bh - 9, cor, ancora='middle')
    ly = 240
    lx = x0
    for nome, tipo in [('Done', 'ok'), ('Built', 'feita'), ('Planned', 'plan')]:
        if tipo == 'ok':
            corpo += '<rect x="%d" y="%d" width="9" height="9" fill="%s"/>' % (lx, ly - 9, c['tinta'])
        elif tipo == 'feita':
            corpo += '<rect x="%.1f" y="%.1f" width="8" height="8" fill="none" stroke="%s"/>' % (lx + .5, ly - 8.5, c['lanterna'])
        else:
            corpo += '<rect x="%.1f" y="%.1f" width="8" height="8" fill="none" stroke="%s"/>' % (lx + .5, ly - 8.5, c['forte'])
        corpo += rotulo(nome, lx + 16, ly, c['fraca'], 11)
        lx += 16 + MONO_M.largura(nome.upper(), 11 * ROT, .08) + 30
    corpo += '<path d="M%d 278.5H1216" stroke="%s"/>' % (x0, c['linha'])
    corpo += rotulo('Python 3.12 · FastAPI · PostgreSQL', x0, 312, c['suave'], 12)
    corpo += rotulo('React · Docker', x0, 336, c['suave'], 12)
    salvar('visao', t, svg(W, H, 'Visão. Personal research, 2026. Trace: introspection. An agent born without a name that decides who it is. Phases 0 to 6 and 9 built.', corpo))


# ─────────── Rastros (faixas) ───────────
FAIXAS = [
    ('01', 'auris', 'AURIS', 'Desktop · Audio + LLM', 'Listening',
     'Listening without intruding: no bot joins the room.', 'Electron · React · Python · faster-whisper · Claude', False),
    ('02', 'gameboy', 'gameboy', 'Emulator · Go', 'Nostalgia & precision',
     'Going back to childhood, but demanding 498 out of 500.', 'Go · Ebitengine · MBC1/2/3/5 · Blargg', False),
    ('03', 'thoth', 'Thoth AI', 'SaaS · LLM', 'Knowledge',
     'Only claim what has a source.', 'Next.js 14 · FastAPI · PostgreSQL · Stripe', False),
    ('04', 'myblock', 'MyBlock', 'Web3 · Real estate', 'Autonomy',
     'Rules that enforce themselves, with nobody chasing.', 'Solidity · Hardhat · Node · Vue 3 · Ethers.js', False),
    ('05', 'webhook', 'webhook-go', 'Infra · Go', 'Care',
     'Nothing entrusted to me gets lost.', 'Go · net/http · PostgreSQL · pgx', True),
]


def faixa(t, f):
    n, chave, nome, tipo, traco, frase, stack, andamento = f
    W, H = 1280, 236
    c = TEMAS[t]
    corpo = '<rect x=".5" y=".5" width="%d" height="%d" rx="6" fill="%s" stroke="%s"/>' % (W - 1, H - 1, c['elev'], c['linha'])
    corpo += txt(SERIF, n, 64, 44, 104, c['estanho'], -.02)
    x = 168
    corpo += rotulo('Trace · ' + traco, x, 62, c['estanho'], 13)
    if andamento:
        rx = 1236
        corpo += rotulo('In progress', rx, 62, c['suave'], 12, 'end')
        corpo += '<circle cx="%.1f" cy="57.5" r="4" fill="%s"/>' % (rx - MONO_M.largura('IN PROGRESS', 12 * ROT, .08) - 14, c['lanterna'])
    corpo += txt(ITALICO, frase, 44, x, 124, c['tinta'], -.005)
    corpo += '<path d="M%d 158.5H1236" stroke="%s"/>' % (x, c['linha'])
    corpo += txt(SERIF, nome, 38, x, 205, c['tinta'], -.01)
    nx = x + SERIF.largura(nome, 38, -.01) + 18
    corpo += rotulo(tipo, nx, 202, c['fraca'], 12)
    corpo += rotulo(stack, 1236, 202, c['suave'], 12, 'end', MONO)
    salvar('rastro-%s' % chave, t, svg(W, H, '%s %s. Trace: %s. %s %s' % (n, nome, traco.lower(), frase, stack), corpo))


# ─────────── Contato: o quarto ───────────
def quarto(t):
    W, H = 1280, 400
    c = TEMAS[t]
    corpo = (
        '<defs><linearGradient id="qf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
        '<stop offset=".55" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<linearGradient id="ql" x1="0" x2="1"><stop offset="0" stop-color="%s"/><stop offset=".2" stop-color="%s" stop-opacity="0"/>'
        '<stop offset=".8" stop-color="%s" stop-opacity="0"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<radialGradient id="qa" cx="640" cy="80" r="200" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="%s"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
        '<filter id="qb" x="-50%%" y="-100%%" width="200%%" height="300%%"><feGaussianBlur stdDeviation="22"/></filter></defs>'
    ) % (c['fundo'], c['elev'], c['fundo'], c['luz'], c['luz'], c['luz'], c['luz'], c['estanho_linha'], c['estanho_linha'])
    corpo += '<rect width="%d" height="%d" rx="6" fill="url(#qf)"/>' % (W, H)
    corpo += '<rect width="%d" height="%d" rx="6" fill="url(#ql)" opacity=".4"/>' % (W, H)
    corpo += '<circle cx="640" cy="80" r="200" fill="url(#qa)" opacity=".7"/>'
    corpo += leque(560, 36, 160, c['estanho'])
    # status
    st = 'Native Portuguese · fluent English'
    sw = MONO_M.largura(st.upper(), 12 * ROT, .08)
    corpo += '<circle cx="%.1f" cy="150" r="4" fill="%s"/>' % (640 - sw / 2 - 10, c['lanterna'])
    corpo += rotulo(st, 640 + 8, 154, c['suave'], 12, 'middle')
    # Let's build.
    tam = 118
    a, b = "Let’s", 'build.'
    wa, wb = SERIF.largura(a, tam, -.03), ITALICO.largura(b, tam, -.03)
    x = 640 - (wa + 26 + wb) / 2
    corpo += '<ellipse cx="640" cy="250" rx="300" ry="40" fill="%s" filter="url(#qb)"/>' % c['luz']
    corpo += txt(SERIF, a, tam, x, 272, c['tinta'], -.03)
    corpo += txt(ITALICO, b, tam, x + wa + 26, 272, c['suave'], -.03)
    corpo += txt(ITALICO, 'Got a system that needs to run without supervision? I want to hear about it.', 30, 640, 330, c['suave'], ancora='middle')
    corpo += rotulo('Open to relocation · Netherlands · European Union', 640, 372, c['fraca'], 11, 'middle')
    salvar('contato', t, svg(W, H, "Let's build. Got a system that needs to run without supervision? I want to hear about it.", corpo))


for tema in TEMAS:
    banner(tema, 'Allison Freitas. Software engineer, full-stack, backend and AI. Systems that keep running when nobody is watching.')
    numeros(tema)
    cabeca(tema, 'visao', '01 — Featured', '', 'Featured', '')
    cabeca(tema, 'rastros', '02 — Traces · side A', 'Traces', '', '05 tracks')
    cabeca(tema, 'percurso', '03 — Path', 'Path', '', 'Mar 2025 — now')
    visao(tema)
    for f in FAIXAS:
        faixa(tema, f)
    quarto(tema)
print('ok')
