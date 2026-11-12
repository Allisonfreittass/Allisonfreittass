"""Gráfico de contribuições e ritmo, no sistema Rastros.

Lê o calendário de contribuições dos últimos 12 meses pela API GraphQL do GitHub
e escreve atividade-*.svg e ritmo-*.svg (noite e neblina). Roda todo dia pela
Action .github/workflows/rastros.yml; à mão:

    GITHUB_TOKEN=$(gh auth token) python3 assets/atividade.py
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request

from gerar import ITALICO, MONO, MONO_M, ROT, SERIF, TEMAS, rotulo, salvar, svg, txt

USUARIO = os.environ.get('RASTROS_USUARIO', 'Allisonfreittass')
MESES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NIVEIS = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}


def buscar():
    consulta = ('query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{'
                'totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}')
    # METRICS_TOKEN (pessoal) conta também as contribuições privadas; se estiver
    # vencido ou ausente, cai para o token da própria Action.
    tokens = [t for t in (os.environ.get('METRICS_TOKEN'), os.environ.get('GITHUB_TOKEN')) if t]
    for i, token in enumerate(tokens):
        req = urllib.request.Request(
            'https://api.github.com/graphql',
            data=json.dumps({'query': consulta, 'variables': {'u': USUARIO}}).encode(),
            headers={'Authorization': 'bearer ' + token, 'Content-Type': 'application/json',
                     'User-Agent': 'rastros-readme'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                dados = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 401 or i == len(tokens) - 1:
                raise
            print('token %d recusado (401), tentando o próximo' % (i + 1))
    if 'errors' in dados:
        raise SystemExit(dados['errors'])
    cal = dados['data']['user']['contributionsCollection']['contributionCalendar']
    dias = [(dt.date.fromisoformat(d['date']), d['contributionCount'], NIVEIS[d['contributionLevel']])
            for w in cal['weeks'] for d in w['contributionDays']]
    return cal['totalContributions'], dias


def sequencias(dias):
    hoje = dias[-1][0]
    ativos = {d for d, n, _ in dias if n}
    # a sequência atual não quebra só porque hoje ainda não teve commit
    d = hoje if hoje in ativos else hoje - dt.timedelta(days=1)
    atual = 0
    while d in ativos:
        atual += 1
        d -= dt.timedelta(days=1)
    maior = corrida = 0
    for _, n, _ in dias:
        corrida = corrida + 1 if n else 0
        maior = max(maior, corrida)
    return atual, maior


def por_mes(dias):
    hoje = dias[-1][0]
    chaves = []
    a, m = hoje.year, hoje.month
    for _ in range(12):
        chaves.append((a, m))
        a, m = (a, m - 1) if m > 1 else (a - 1, 12)
    chaves.reverse()
    soma = {k: 0 for k in chaves}
    for d, n, _ in dias:
        if (d.year, d.month) in soma:
            soma[(d.year, d.month)] += n
    return [(k, soma[k]) for k in chaves]


def plural(n, um, varios):
    return um if n == 1 else varios


# ─────────── Gráfico de contribuições ───────────
def grafico(t, total, dias):
    W, H = 1280, 336
    c = TEMAS[t]
    ativos = sum(1 for _, n, _ in dias if n)
    pico = max(dias, key=lambda x: x[1])
    corpo = '<rect x=".5" y=".5" width="%d" height="%d" rx="6" fill="%s" stroke="%s"/>' % (W - 1, H - 1, c['elev'], c['linha'])
    corpo += rotulo('Last 12 months · %d %s · %d active %s' % (
        total, plural(total, 'contribution', 'contributions'), ativos, plural(ativos, 'day', 'days')), 48, 58, c['estanho'], 12)
    # legenda
    x = 1232
    corpo += rotulo('More', x, 58, c['fraca'], 11, 'end')
    x -= MONO_M.largura('MORE', 11 * ROT, .08) + 12
    for nivel in (4, 3, 2, 1, 0):
        x -= 16
        corpo += celula(x, 45, 14, nivel, c)
        x -= 5
    corpo += rotulo('Less', x - 8, 58, c['fraca'], 11, 'end')
    # grade: uma coluna por semana, domingo em cima
    x0, y0, passo, lado = 48, 92, 22, 17
    inicio = dias[0][0] - dt.timedelta(days=(dias[0][0].weekday() + 1) % 7)
    ultimo_mes = None
    for d, n, nivel in dias:
        col = (d - inicio).days // 7
        lin = (d.weekday() + 1) % 7
        x, y = x0 + col * passo, y0 + lin * passo
        if (d, n) == pico[:2] and n:
            corpo += '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="4" fill="%s" opacity=".5" filter="url(#g)"/>' % (x - 3, y - 3, lado + 6, lado + 6, c['brilho'])
            corpo += '<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s"/>' % (x, y, lado, lado, c['lanterna'])
        else:
            corpo += celula(x, y, lado, nivel, c)
        if d.day <= 7 and lin == 0 and d.month != ultimo_mes:
            ultimo_mes = d.month
            if col < 52:
                corpo += rotulo(MESES[d.month - 1], x, y0 + 7 * passo + 20, c['fraca'], 11)
    corpo = '<defs><filter id="g" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter></defs>' + corpo
    corpo += rotulo('Busiest day in red · updated %s' % dias[-1][0].isoformat(), 1232, 314, c['fraca'], 11, 'end')
    alt = '%d contributions and %d active days in the last 12 months. Busiest day: %s, with %d.' % (
        total, ativos, pico[0].isoformat(), pico[1])
    salvar('atividade', t, svg(W, H, alt, corpo))


def celula(x, y, lado, nivel, c):
    if nivel == 0:
        return '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="3" fill="%s"/>' % (x, y, lado, lado, c['hover'])
    op = {1: .3, 2: .5, 3: .75, 4: 1}[nivel]
    return '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="3" fill="%s" opacity="%s"/>' % (x, y, lado, lado, c['estanho'], op)


# ─────────── Ritmo: sequências e meses ───────────
def ritmo(t, total, dias):
    W, H = 1280, 380
    c = TEMAS[t]
    atual, maior = sequencias(dias)
    ativos = sum(1 for _, n, _ in dias if n)
    pico = max(dias, key=lambda x: x[1])
    meses = por_mes(dias)
    corpo = '<rect x=".5" y=".5" width="%d" height="%d" rx="6" fill="%s" stroke="%s"/>' % (W - 1, H - 1, c['elev'], c['linha'])
    stats = [
        ('Current streak', str(atual), plural(atual, ' day', ' days')),
        ('Longest streak', str(maior), plural(maior, ' day', ' days')),
        ('Active days', str(ativos), ''),
        ('Busiest day', str(pico[1]), ' on %s %d' % (MESES[pico[0].month - 1], pico[0].day)),
    ]
    for i, (rot, num, suf) in enumerate(stats):
        x, y = 48 + (i % 2) * 220, 62 + (i // 2) * 160
        corpo += rotulo(rot, x, y, c['fraca'], 11)
        cor = c['lanterna'] if i == 0 and atual else c['tinta']
        corpo += txt(SERIF, num, 78, x - 2, y + 82, cor, -.02)
        if suf:
            corpo += txt(ITALICO, suf, 24, x + SERIF.largura(num, 78, -.02) + 2, y + 82, c['suave'])
    corpo += '<path d="M520.5 40V340" stroke="%s"/>' % c['linha']
    # barras por mês
    x0, x1, base, alto = 572, 1232, 300, 196
    corpo += rotulo('Contributions per month', x0, 62, c['fraca'], 11)
    mx = max(n for _, n in meses) or 1
    passo = (x1 - x0) / 12
    larg = passo * .62
    corpo += '<path d="M%d %.1fH%d" stroke="%s"/>' % (x0, base + .5, x1, c['forte'])
    for i, ((a, m), n) in enumerate(meses):
        x = x0 + i * passo + (passo - larg) / 2
        h = alto * n / mx
        if n:
            destaque = n == mx
            cor = c['lanterna'] if destaque else c['estanho']
            op = 1 if destaque else .55
            corpo += '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s" opacity="%s"/>' % (x, base - h, larg, h, cor, op)
            corpo += txt(MONO, str(n), 15, x + larg / 2, base - h - 10, c['tinta'] if destaque else c['fraca'], ancora='middle')
        corpo += rotulo(MESES[m - 1], x + larg / 2, base + 30, c['fraca'], 10, 'middle')
    alt = 'Current streak %d days, longest %d, %d active days, busiest day %d contributions. Per month: %s.' % (
        atual, maior, ativos, pico[1], ', '.join('%s %d' % (MESES[m - 1], n) for (a, m), n in meses))
    salvar('ritmo', t, svg(W, H, alt, corpo))


if __name__ == '__main__':
    total, dias = buscar()
    for tema in TEMAS:
        grafico(tema, total, dias)
        ritmo(tema, total, dias)
    print('ok', total, len(dias))
