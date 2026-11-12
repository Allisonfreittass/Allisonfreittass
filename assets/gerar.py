"""Gera as imagens do README do perfil no sistema Rastros.

Regras desta versão, para não poluir:
  · todo cartão é igual (mesmo fundo, borda, raio e margem de 32);
  · as imagens têm 800 de largura, perto do tamanho em que o GitHub as mostra,
    então o texto chega à tela com tamanho de leitura;
  · no máximo dois estilos de texto por bloco; a única ilustração (a floresta
    com chuva) fica num painel do cartão About; o vermelho aparece só em pontos.

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

# ─────────── Tokens Rastros ───────────
TEMAS = {
    'noite': dict(
        cartao='#090E10', borda='rgba(214,228,226,.13)', hover='#142024', elev='#0E1619', fundo='#090E10',
        tinta='#E6E9E6', suave='#A9B4B2', fraca='#7E8B8A', linha='rgba(214,228,226,.09)', forte='rgba(214,228,226,.22)',
        estanho='#A9BCBD', lanterna='#E0483F', brilho='rgba(224,72,63,.55)', luaz='#E6E9E6',
        # a ilustração: céu que clareia na névoa do horizonte, pinheiros mais escuros quanto mais perto
        ceu=('#0B1214', '#1F3035'), pinheiros=('#18282D', '#0F1A1E', '#070B0D'),
        chuva='200,218,222', nevoa='#A9B4B2', nevoa_a=.07, lua='rgba(214,228,226,.22)',
    ),
    'neblina': dict(
        cartao='#F6F8F7', borda='rgba(14,22,25,.12)', hover='#DCE2E1', elev='#F3F5F4', fundo='#E9EDEC',
        tinta='#0E1619', suave='#3D4A4B', fraca='#546163', linha='rgba(14,22,25,.10)', forte='rgba(14,22,25,.22)',
        estanho='#4F6366', lanterna='#B3342B', brilho='rgba(179,52,43,.30)', luaz='#FFFFFF',
        ceu=('#F3F5F4', '#D3DCDB'), pinheiros=('#BCC8C7', '#98A8A7', '#6F8382'),
        chuva='14,22,25', nevoa='#FFFFFF', nevoa_a=.6, lua='rgba(255,255,255,.8)',
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


SERIF = Fonte('InstrumentSerif-Regular.ttf')
ITALICO = Fonte('InstrumentSerif-Italic.ttf')
SANS = Fonte('InterTight-Regular.ttf')
SANS_M = Fonte('InterTight-Medium.ttf')
MONO = Fonte('JetBrainsMono-Regular.ttf')


def txt(fonte, texto, tam, x, y, cor, track=0.0, ancora='start'):
    return '<path fill="%s" d="%s"/>' % (cor, fonte.path(texto, tam, x, y, track, ancora))


def mono(texto, x, y, cor, tam=11, ancora='start'):
    """Rótulo mono em caixa alta com tracking .06em (o token `rotulo`)."""
    return txt(MONO, texto.upper(), tam, x, y, cor, .06, ancora)


def larg_mono(texto, tam=11):
    return MONO.largura(texto.upper(), tam, .06)


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
    corpo = mono(n, M, y, c['estanho'], 12)
    corpo += txt(SANS_M, titulo, 17, M + larg_mono(n, 12) + 12, y + 1, c['tinta'])
    if direita:
        corpo += mono(direita, W - M, y, c['fraca'], 10.5, 'end')
    return corpo


def pilula(x, y, texto, c, ponto=False):
    w = larg_mono(texto, 10.5) + 28 + (14 if ponto else 0)
    corpo = '<rect x="%.1f" y="%.1f" width="%.1f" height="26" rx="13" fill="none" stroke="%s"/>' % (x + .5, y + .5, w - 1, c['forte'])
    tx = x + 14
    if ponto:
        corpo += '<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (tx + 3, y + 13, c['lanterna'])
        tx += 14
    corpo += mono(texto, tx, y + 17, c['suave'], 10.5)
    return corpo, w


def salvar(nome, tema, conteudo):
    with open(os.path.join(SAIDA, '%s-%s.svg' % (nome, tema)), 'w', encoding='utf-8') as f:
        f.write(conteudo)


# ─────────── Desenhos da marca ───────────
def floresta(seed, camadas, largura):
    s = [seed]

    def rnd():
        s[0] = (s[0] * 16807) % 2147483647
        return s[0] / 2147483647

    def pinheiro(x, base, h, w):
        n, step, Wd, L, R = 8, h / 9, w / 2, [], []
        for k in range(n):
            yk = base - step * k - step * .3
            o = Wd * (1 - k / n) * (.85 + rnd() * .3)
            L += [(x - o, yk), (x - o * .3, yk - step * 1.25)]
            R += [(x + o, yk + step * .1), (x + o * .3, yk - step * 1.2)]
        p = 'M%.1f %.1f' % (x - Wd * .12, base)
        p += ''.join(' L%.1f %.1f' % q for q in L)
        p += ' L%.1f %.1f' % (x, base - h)
        p += ''.join(' L%.1f %.1f' % q for q in reversed(R))
        return p + ' L%.1f %.1f Z' % (x + Wd * .12, base)

    saida = []
    for cor, base, hmin, hmax, gap, fundo in camadas:
        d, x = '', -10.0
        while x < largura + 20:
            h = hmin + rnd() * (hmax - hmin)
            d += pinheiro(x, base + rnd() * 6, h, h * .3)
            x += gap * (.55 + rnd() * .8)
        d += 'M0 %d H%d V%d H0 Z' % (base, largura, fundo)
        saida.append('<path fill="%s" d="%s"/>' % (cor, d))
    return ''.join(saida)


def onda(x0, x1, meio, amp):
    """A linha de sinal da landing, congelada em t = 0."""
    pts = []
    for i in range(0, 241):
        u = i / 240
        env = math.exp(-((u - .5) / .22) ** 2) * .85 + .08
        y = meio + math.sin(u * 40) * math.sin(u * 6) * env * amp + math.sin(u * 130) * env * amp * .083
        pts.append((x0 + (x1 - x0) * u, y))
    return 'M' + ' L'.join('%.1f %.1f' % p for p in pts)


MOVIMENTO = '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'


# ─────────── 1. Topo ───────────
def topo(t):
    H = 300
    c = TEMAS[t]
    trilha = onda(470, W - M, 150, 40)
    estilo = ('.farol{offset-path:path("%s");animation:corre 11s linear infinite}'
              '@keyframes corre{from{offset-distance:0%%}to{offset-distance:100%%}}' % trilha) + MOVIMENTO
    corpo = cartao(H, c)
    corpo += ('<defs><linearGradient id="s" x1="470" x2="%d" gradientUnits="userSpaceOnUse">'
              '<stop offset="0" stop-color="%s" stop-opacity="0"/><stop offset=".2" stop-color="%s"/>'
              '<stop offset=".85" stop-color="%s"/><stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>'
              '<filter id="b" x="-300%%" y="-300%%" width="700%%" height="700%%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
              ) % (W - M, c['tinta'], c['tinta'], c['tinta'], c['tinta'])
    p1, w1 = pilula(M, M, 'Open to relocation · NL / EU', c, ponto=True)
    p2, _ = pilula(M + w1 + 8, M, 'Varginha, BR · UTC−3', c)
    corpo += p1 + p2
    corpo += txt(SERIF, 'Allison', 76, M - 3, 140, c['tinta'], -.025)
    corpo += txt(SERIF, 'Freitas', 76, M - 3, 206, c['tinta'], -.025)
    corpo += txt(SANS, 'Software engineer · Full-stack at F2 Tecnologia', 14.5, M, 240, c['suave'])
    a = 'I build systems that keep running '
    corpo += txt(SANS, a, 14.5, M, 266, c['tinta'])
    corpo += txt(ITALICO, 'when nobody is watching.', 18, M + SANS.largura(a, 14.5), 266, c['tinta'])
    # a linha de sinal, com a lanterna correndo
    corpo += '<path d="%s" fill="none" stroke="url(#s)" stroke-width="1.2" opacity=".85"/>' % trilha
    corpo += '<g class="farol"><circle r="8" fill="%s" filter="url(#b)"/><circle r="3" fill="%s"/></g>' % (c['brilho'], c['lanterna'])
    corpo += mono('System running · signal steady', W - M, 266, c['fraca'], 10.5, 'end')
    salvar('topo', t, svg(H, 'Allison Freitas. Software engineer, full-stack at F2 Tecnologia. I build systems that keep running when nobody is watching. Open to relocation, Netherlands / EU.', corpo, estilo))


# ─────────── 2. About, com a única ilustração ───────────
SOBRE_TEXTO = [
    'Full-stack engineer, mostly on the backend: public APIs, webhooks into ERPs and automations with LLMs.',
    'On my own time I build systems that keep running when nobody is watching, from a Game Boy emulator in Go to an agent with persistent memory.',
]
SOBRE = [
    ('now', 'Visão, a cognitive architecture with memory'),
    ('goal', 'Relocate to the Netherlands / EU'),
    ('beyond code', 'Late nights, rain, The Neighbourhood'),
]


def ilustracao(x, y, w, h, c):
    """Floresta de Forks à noite, com névoa e chuva fina, recortada num painel."""
    lx, ly = x + w * .7, y + h * .24
    corpo = ('<defs><clipPath id="pc"><rect x="%d" y="%d" width="%d" height="%d" rx="8"/></clipPath>'
             '<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
             '<radialGradient id="lua" cx="%.1f" cy="%.1f" r="80" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
             '<filter id="nv" x="-20%%" y="-200%%" width="140%%" height="500%%"><feGaussianBlur stdDeviation="7"/></filter>'
             '<pattern id="gotas" width="60" height="90" patternUnits="userSpaceOnUse">'
             '<path stroke="rgba(%s,.22)" stroke-width=".8" d="M10 6l-2 11M38 40l-2 13M52 70l-2 10M24 76l-2 9"/></pattern></defs>'
             ) % (x, y, w, h, c['ceu'][0], c['ceu'][1], lx, ly, c['lua'], c['lua'], c['chuva'])
    p1, p2, p3 = c['pinheiros']
    mata = floresta(11, [(p1, 150, 50, 90, 9, 230), (p2, 175, 60, 105, 12, 230), (p3, 205, 70, 120, 16, 230)], w)
    corpo += '<g clip-path="url(#pc)"><rect x="%d" y="%d" width="%d" height="%d" fill="url(#ceu)"/>' % (x, y, w, h)
    corpo += '<circle cx="%.1f" cy="%.1f" r="80" fill="url(#lua)"/>' % (lx, ly)
    corpo += '<circle cx="%.1f" cy="%.1f" r="12" fill="%s" opacity=".5"/>' % (lx, ly, c['luaz'])
    corpo += '<g transform="translate(%d %d)">%s</g>' % (x, y + h - 215, mata)
    corpo += '<rect class="nv" x="%d" y="%d" width="%d" height="16" rx="8" fill="%s" opacity="%s" filter="url(#nv)"/>' % (x - 20, y + h - 70, w + 40, c['nevoa'], c['nevoa_a'])
    corpo += '<g class="chuva"><rect x="%d" y="%d" width="%d" height="%d" fill="url(#gotas)"/></g></g>' % (x, y - 90, w + 30, h + 90)
    corpo += '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="none" stroke="%s"/>' % (x + .5, y + .5, w - 1, h - 1, c['linha'])
    return corpo


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
        corpo_txt += mono('→ ' + k, M, y + 2, c['estanho'], 10.5)
        corpo_txt += txt(SANS, v, 13.5, M + 128, y + 3, c['tinta'])
        y += 34
    corpo_txt += '<path d="M%d %.1fH%d" stroke="%s"/>' % (M, y - 18.5, col, c['linha'])
    H = int(y + 10)
    estilo = ('.chuva{animation:cai 1.3s linear infinite}@keyframes cai{to{transform:translate(-6px,90px)}}'
              '.nv{animation:deriva 30s ease-in-out infinite alternate}@keyframes deriva{to{transform:translateX(-40px)}}') + MOVIMENTO
    corpo = cartao(H, c) + cabecalho('01', 'About', 50, c) + corpo_txt
    corpo += ilustracao(col + 34, M, W - M - col - 34, H - 2 * M, c)
    alt = 'About. ' + ' '.join(SOBRE_TEXTO) + ' ' + ' '.join('%s: %s.' % kv for kv in SOBRE)
    salvar('sobre', t, svg(H, alt, corpo, estilo))


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
    topo_, lh = 76, 44
    H = topo_ + lh * len(RASTROS) + 14
    corpo = cartao(H, c) + cabecalho('02', 'Traces', 50, c, 'The trait first, then the tech')
    for i, (nome, frase, tipo, ativo) in enumerate(RASTROS):
        y = topo_ + i * lh
        corpo += '<path d="M%d %.1fH%d" stroke="%s"/>' % (M, y + .5, W - M, c['linha'])
        b = y + 28
        corpo += mono('%02d' % (i + 1), M, b, c['fraca'], 10.5)
        corpo += txt(SANS_M, nome, 14.5, M + 34, b, c['tinta'])
        if ativo:
            corpo += '<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (M + 34 + SANS_M.largura(nome, 14.5) + 9, b - 4.5, c['lanterna'])
        limite = W - M - larg_mono(tipo, 10) - 24 - 176
        tam = 16.5
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
