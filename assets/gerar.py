"""Gera as imagens do README do perfil no sistema Noite (o mesmo do portfólio).

Regras desta versão, para não poluir:
  · todo cartão é igual (mesmo fundo, borda, raio e margem de 32);
  · as imagens têm 800 de largura, perto do tamanho em que o GitHub as mostra,
    então o texto chega à tela com tamanho de leitura;
  · ônix, pérola e um único metal (latão); a pérola marca o que está vivo;
  · a única ilustração são os fios de seda com pérolas, revelados por uma
    lanterna que passeia devagar, como no hero do site.

Cada imagem sai em -noite (escuro) e -neblina (claro). O texto vira contorno,
então as fontes aparecem iguais no GitHub sem carregar nada.

Uso:  pip install fonttools uharfbuzz
      python3 assets/gerar.py        (imagens fixas)
      python3 assets/atividade.py    (gráfico; roda todo dia na Action)
As fontes ficam em assets/fontes (SIL Open Font License, licenças ao lado).
"""
import html
import math
import os

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

SAIDA = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(SAIDA, 'fontes')
W = 800      # largura de todas as imagens
M = 32       # margem interna dos cartões

# ─────────── Tokens Noite ───────────
TEMAS = {
    'noite': dict(
        cartao='#050505', borda='rgba(232,226,214,.12)', hover='#17140F',
        tinta='#E8E2D6', suave='#CFC8BB', fraca='#9C968B', linha='rgba(232,226,214,.09)', forte='rgba(232,226,214,.22)',
        latao='#B8995A',
        perola=('#FFFDF8', '#E6DFD0', '#8F877A'), brilho='rgba(245,238,224,.16)',
        fio='232,226,214', fio_fraco=.07, fio_forte=.55, luz='rgba(240,230,210,.08)',
    ),
    'neblina': dict(
        cartao='#F2EEE6', borda='rgba(20,18,16,.14)', hover='#E2DCD0',
        tinta='#141210', suave='#3E3A34', fraca='#5E5950', linha='rgba(20,18,16,.10)', forte='rgba(20,18,16,.22)',
        latao='#7A6232',
        perola=('#FFFFFF', '#E3DCCD', '#7E7668'), brilho='rgba(255,255,255,.75)',
        fio='20,18,16', fio_fraco=.08, fio_forte=.5, luz='rgba(255,255,255,.5)',
    ),
}


# ─────────── Texto em contorno ───────────
class Fonte:
    def __init__(self, nome, ligaduras=True):
        self.ligaduras = ligaduras
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
        hb.shape(self.hb, buf, {'kern': True, 'liga': self.ligaduras, 'dlig': False, 'hlig': False})
        return buf.glyph_infos, buf.glyph_positions

    def largura(self, texto, tam, track=0.0):
        _, pos = self._molda(texto)
        return sum(p.x_advance for p in pos) * tam / self.upem + track * tam * max(0, len(pos) - 1)

    def path(self, texto, tam, x, y, track=0.0, ancora='start'):
        infos, pos = self._molda(texto)
        s = tam / self.upem
        w = self.largura(texto, tam, track)
        x -= {'start': 0, 'middle': w / 2, 'end': w}[ancora]
        partes, cx = [], x
        for info, p in zip(infos, pos):
            pen = SVGPathPen(self.glyphs, ntos=lambda v: ('%.1f' % v).rstrip('0').rstrip('.'))
            self.glyphs[self.ordem[info.codepoint]].draw(
                TransformPen(pen, (s, 0, 0, -s, cx + p.x_offset * s, y - p.y_offset * s)))
            partes.append(pen.getCommands())
            cx += p.x_advance * s + track * tam
        return ''.join(partes)


SERIF = Fonte('LibreCaslonDisplay-Regular.ttf')
ITALICO = Fonte('LibreCaslonText-Italic.ttf', ligaduras=False)  # sem o 'st' histórico da Caslon
SANS = Fonte('InstrumentSans-Regular.ttf')
SANS_M = Fonte('InstrumentSans-Medium.ttf')
MONO = Fonte('IBMPlexMono-Regular.ttf')


def txt(fonte, texto, tam, x, y, cor, track=0.0, ancora='start'):
    return '<path fill="%s" d="%s"/>' % (cor, fonte.path(texto, tam, x, y, track, ancora))


def mono(texto, x, y, cor, tam=11, ancora='start'):
    """Rótulo mono discreto, em caixa normal (datas, stacks, legendas)."""
    return txt(MONO, texto, tam, x, y, cor, .02, ancora)


def larg_mono(texto, tam=11):
    return MONO.largura(texto, tam, .02)


def quebra(fonte, texto, tam, largura):
    linhas, atual = [], ''
    for p in texto.split():
        teste = (atual + ' ' + p).strip()
        if atual and fonte.largura(teste, tam) > largura:
            linhas.append(atual)
            atual = p
        else:
            atual = teste
    return linhas + [atual]


def svg(h, titulo, corpo, estilo=''):
    t = html.escape(titulo)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n') % (W, h, W, h, t, t, ('<style>%s</style>' % estilo) if estilo else '', corpo)


def cartao(h, c):
    return '<rect x=".5" y=".5" width="%d" height="%d" rx="12" fill="%s" stroke="%s"/>' % (W - 1, h - 1, c['cartao'], c['borda'])


def cabecalho(n, titulo, y, c, direita=''):
    corpo = mono(n, M, y, c['latao'], 12)
    corpo += txt(SERIF, titulo, 24, M + larg_mono(n, 12) + 12, y + 2, c['tinta'])
    if direita:
        corpo += mono(direita, W - M, y, c['fraca'], 10.5, 'end')
    return corpo


# ─────────── Pérolas ───────────
def perola_defs(c):
    a, b, d = c['perola']
    return ('<radialGradient id="pe" cx=".36" cy=".32" r=".72">'
            '<stop offset="0" stop-color="%s"/><stop offset=".45" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
            '</radialGradient>') % (a, b, d)


def perola(x, y, r, c, halo=True):
    corpo = '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, r * 3, c['brilho']) if halo else ''
    return corpo + '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#pe)"/>' % (x, y, r)


def pilula(x, y, texto, c, ponto=False):
    w = larg_mono(texto, 10.5) + 28 + (14 if ponto else 0)
    corpo = '<rect x="%.1f" y="%.1f" width="%.1f" height="26" rx="13" fill="none" stroke="%s"/>' % (x + .5, y + .5, w - 1, c['forte'])
    tx = x + 14
    if ponto:
        corpo += perola(tx + 3, y + 13, 3.6, c, halo=False)
        tx += 14
    corpo += mono(texto, tx, y + 17, c['suave'], 10.5)
    return corpo, w


def salvar(nome, tema, conteudo):
    with open(os.path.join(SAIDA, '%s-%s.svg' % (nome, tema)), 'w', encoding='utf-8') as f:
        f.write(conteudo)


# ─────────── Fios de seda (o hero do site, congelado) ───────────
def fio_y(i, n, u, top, h, t=6.0):
    k = i / (n - 1) - .5
    c = top + h * (.5 + .22 * math.sin(u * 2.1 + t * .1) + .06 * math.sin(u * 5.1 - t * .15))
    tw = math.cos(u * 2.8 + t * .08 + .6)
    spread = h * (.42 + .14 * math.sin(u * 1.7 - t * .07))
    return c + k * spread * tw + math.sin(u * 9 + i * .35 + t * .35) * 2.2 * (1 - abs(tw))


def fios(x0, x1, top, h, n=28, t=6.0):
    saida = []
    for i in range(n):
        pts = []
        for j in range(0, 121):
            u = j / 120
            pts.append((x0 + (x1 - x0) * u, fio_y(i, n, u * 1.35, top, h, t)))
        saida.append('M' + ' L'.join('%.1f %.1f' % p for p in pts))
    return saida


def cena(x0, x1, top, h, c, ids, rota, perolas, fade=None):
    """Fios escuros, a mesma trama revelada por uma lanterna que passeia, e pérolas.

    ids: prefixo único por cena; rota: pontos (x, y) por onde a lanterna anda;
    perolas: [(indice_do_fio, u, raio)]; fade: (xa, xb) para os fios nascerem do nada.
    """
    n = 28
    caminhos = fios(x0, x1, top, h, n)
    fx = fade or (x0, x0 + 1)
    defs = ('<linearGradient id="%sf" x1="%.1f" x2="%.1f" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
            '<mask id="%sm" maskUnits="userSpaceOnUse"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="url(#%sf)"/></mask>'
            '<radialGradient id="%sl"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#fff" stop-opacity=".55"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="%sg"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<mask id="%sz" maskUnits="userSpaceOnUse"><g mask="url(#%sm)"><circle class="%slz" cx="0" cy="0" r="150" fill="url(#%sl)"/></g></mask>'
            ) % (ids, fx[0], fx[1], ids, x0 - 20, top - 60, x1 - x0 + 40, h + 120, ids, ids, ids, c['luz'], c['luz'], ids, ids, ids, ids)
    rgb = c['fio']
    fracos = ''.join('<path d="%s"/>' % d for d in caminhos)
    fortes = ''
    for i, d in enumerate(caminhos):
        k = abs(i / (n - 1) - .5)
        if i % 9 == 4:
            fortes += '<path d="%s" stroke="%s" stroke-width="1"/>' % (d, c['latao'])
        else:
            fortes += '<path d="%s" stroke-opacity="%.2f"/>' % (d, .35 + .65 * (1 - k * 1.6))
    joias = ''
    for i, u, r in perolas:
        px = x0 + (x1 - x0) * u
        joias += perola(px, fio_y(i, n, u * 1.35, top, h), r, c)
    passos = len(rota)
    quadros = ''.join('%d%%{transform:translate(%.1fpx,%.1fpx)}' % (round(100 * k / (passos - 1)), x, y)
                      for k, (x, y) in enumerate(rota))
    estilo = '.%slz,.%sgl{animation:%sanda 26s ease-in-out infinite alternate}@keyframes %sanda{%s}' % (
        ids, ids, ids, ids, quadros)
    corpo = '<defs>%s</defs>' % defs
    corpo += '<circle class="%sgl" cx="0" cy="0" r="190" fill="url(#%sg)"/>' % (ids, ids)
    corpo += '<g mask="url(#%sm)" fill="none" stroke="rgb(%s)" stroke-opacity="%s" stroke-width=".6">%s</g>' % (ids, rgb, c['fio_fraco'], fracos)
    corpo += '<g mask="url(#%sz)" fill="none" stroke="rgb(%s)" stroke-width=".7">%s%s</g>' % (ids, rgb, fortes, joias)
    return corpo, estilo


MOVIMENTO = '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'


# ─────────── 1. Topo ───────────
def topo(t):
    H = 300
    c = TEMAS[t]
    corpo = cartao(H, c) + '<defs>%s<clipPath id="tc"><rect x="1" y="1" width="%d" height="%d" rx="11"/></clipPath></defs>' % (
        perola_defs(c), W - 2, H - 2)
    rota = [(690, 120), (610, 190), (520, 110), (650, 80), (720, 200)]
    fundo, estilo = cena(330, W + 10, 30, 240, c, 't', rota,
                         [(8, .55, 4.2), (17, .78, 3.2), (24, .38, 3.6), (12, .92, 2.8)], fade=(380, 560))
    corpo += '<g clip-path="url(#tc)">%s</g>' % fundo
    p1, w1 = pilula(M, M, 'Open to relocation · NL / EU', c, ponto=True)
    p2, _ = pilula(M + w1 + 8, M, 'Varginha, BR · UTC−3', c)
    corpo += p1 + p2
    corpo += txt(SERIF, 'Allison', 74, M - 3, 140, c['tinta'], -.02)
    corpo += txt(SERIF, 'Freitas', 74, M - 3, 206, c['tinta'], -.02)
    corpo += txt(SANS, 'Software engineer · Full-stack at F2 Tecnologia', 14.5, M, 240, c['suave'])
    corpo += txt(SANS, 'I build systems that keep running when nobody is watching.', 14.5, M, 266, c['tinta'])
    salvar('topo', t, svg(H, 'Allison Freitas. Software engineer, full-stack at F2 Tecnologia. I build systems that keep running when nobody is watching. Open to relocation, Netherlands / EU.', corpo, estilo + MOVIMENTO))


# ─────────── 2. About, com o painel de fios ───────────
SOBRE_TEXTO = [
    'Full-stack engineer, mostly on the backend: public APIs, webhooks into ERPs and automations with LLMs.',
    'On my own time I build systems that keep running when nobody is watching, from a Game Boy emulator in Go to an agent with persistent memory.',
]
SOBRE = [
    ('now', 'Visão, a cognitive architecture with memory'),
    ('goal', 'Relocate to the Netherlands / EU'),
    ('beyond code', 'Late nights, rain, The Neighbourhood'),
]


def painel(x, y, w, h, c):
    corpo = '<defs><clipPath id="pc"><rect x="%d" y="%d" width="%d" height="%d" rx="8"/></clipPath></defs>' % (x, y, w, h)
    rota = [(x + w * .7, y + h * .3), (x + w * .3, y + h * .6), (x + w * .55, y + h * .2), (x + w * .8, y + h * .7)]
    cena_, estilo = cena(x - 10, x + w + 10, y + 10, h - 20, c, 'p', rota,
                         [(9, .3, 3.4), (18, .62, 4), (5, .85, 2.8)])
    corpo += '<g clip-path="url(#pc)"><rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>%s</g>' % (x, y, w, h, c['cartao'], cena_)
    corpo += '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="none" stroke="%s"/>' % (x + .5, y + .5, w - 1, h - 1, c['linha'])
    return corpo, estilo


def sobre(t):
    c = TEMAS[t]
    col = 470
    y = 92
    corpo_txt = ''
    for par in SOBRE_TEXTO:
        for linha in quebra(SANS, par, 14.5, col - M):
            corpo_txt += txt(SANS, linha, 14.5, M, y, c['suave'])
            y += 23
        y += 12
    y += 4
    for k, v in SOBRE:
        corpo_txt += '<path d="M%d %.1fH%d" stroke="%s"/>' % (M, y - 18.5, col, c['linha'])
        corpo_txt += mono(k, M, y + 2, c['latao'], 10.5)
        corpo_txt += txt(SANS, v, 13.5, M + 128, y + 3, c['tinta'])
        y += 34
    corpo_txt += '<path d="M%d %.1fH%d" stroke="%s"/>' % (M, y - 18.5, col, c['linha'])
    H = int(y + 10)
    corpo = cartao(H, c) + '<defs>%s</defs>' % perola_defs(c) + cabecalho('01', 'About', 50, c) + corpo_txt
    pn, estilo = painel(col + 34, M, W - M - col - 34, H - 2 * M, c)
    corpo += pn
    alt = 'About. ' + ' '.join(SOBRE_TEXTO) + ' ' + ' '.join('%s: %s.' % kv for kv in SOBRE)
    salvar('sobre', t, svg(H, alt, corpo, estilo + MOVIMENTO))


# ─────────── 3. Rastros ───────────
RASTROS = [
    ('Visão', 'An agent born without a name that decides who it is.', 'Research · phases 0–6, 9', True),
    ('AURIS', 'Listening without intruding: no bot joins the room.', 'Desktop · audio + LLM', False),
    ('gameboy', 'Going back to childhood, demanding 498 out of 500.', 'Emulator · Go', False),
    ('Thoth AI', 'Only claim what has a source.', 'SaaS · RAG', False),
    ('MyBlock', 'Rules that enforce themselves, with nobody chasing.', 'Web3 · Solidity', False),
    ('webhook-go', 'Nothing entrusted to me gets lost.', 'Infra · Go', True),
]


def rastros(t):
    c = TEMAS[t]
    topo_, lh = 76, 48
    H = topo_ + lh * len(RASTROS) + 14
    corpo = cartao(H, c) + '<defs>%s</defs>' % perola_defs(c)
    corpo += cabecalho('02', 'Traces', 50, c, 'The trait first, then the tech')
    for i, (nome, frase, tipo, ativo) in enumerate(RASTROS):
        y = topo_ + i * lh
        corpo += '<path d="M%d %.1fH%d" stroke="%s"/>' % (M, y + .5, W - M, c['linha'])
        b = y + 31
        corpo += mono('%02d' % (i + 1), M, b, c['fraca'], 10.5)
        corpo += txt(SERIF, nome, 21, M + 34, b, c['tinta'])
        if ativo:
            corpo += perola(M + 34 + SERIF.largura(nome, 21) + 11, b - 6, 3.4, c, halo=False)
        limite = W - M - larg_mono(tipo, 10) - 24 - 176
        tam = 15.5
        while ITALICO.largura(frase, tam) > limite:
            tam -= .5
        corpo += txt(ITALICO, frase, tam, M + 176, b, c['suave'])
        corpo += mono(tipo, W - M, b, c['fraca'], 10, 'end')
    alt = 'Traces. ' + ' '.join('%s: %s' % (n, f) for n, f, _, _ in RASTROS)
    salvar('rastros', t, svg(H, alt, corpo))


def main():
    for tema in TEMAS:
        topo(tema)
        sobre(tema)
        rastros(tema)
    print('ok')


if __name__ == '__main__':
    main()
