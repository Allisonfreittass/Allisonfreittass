"""Gráfico de contribuições e ritmo, no sistema Rastros.

Lê o calendário de contribuições dos últimos 12 meses pela API GraphQL do GitHub
e escreve atividade-*.svg (noite e neblina), com as sequências no rodapé. Roda todo dia pela
Action .github/workflows/rastros.yml; à mão:

    GITHUB_TOKEN=$(gh auth token) python3 assets/atividade.py
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request

from gerar import M, SANS, SANS_M, TEMAS, W, cabecalho, cartao, larg_mono, mono, salvar, svg, txt

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
def celula(x, y, lado, nivel, c):
    if nivel == 0:
        return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s"/>' % (x, y, lado, lado, c['hover'])
    op = {1: .3, 2: .5, 3: .75, 4: 1}[nivel]
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s" opacity="%s"/>' % (x, y, lado, lado, c['estanho'], op)


def grafico(t, total, dias):
    H = 292
    c = TEMAS[t]
    ativos = sum(1 for _, n, _ in dias if n)
    pico = max(dias, key=lambda x: x[1])
    atual, maior = sequencias(dias)
    corpo = cartao(H, c) + cabecalho('03', 'Rhythm', 50, c)
    corpo += mono('%d %s · %d active %s · last 12 months' % (
        total, plural(total, 'contribution', 'contributions'), ativos, plural(ativos, 'day', 'days')),
        W - M, 50, c['fraca'], 10.5, 'end')
    # grade: uma coluna por semana, domingo em cima
    semanas = ((dias[-1][0] - dias[0][0]).days + (dias[0][0].weekday() + 1) % 7) // 7 + 1
    passo = (W - 2 * M + 3) / semanas
    lado = passo - 3
    x0, y0 = M, 78
    inicio = dias[0][0] - dt.timedelta(days=(dias[0][0].weekday() + 1) % 7)
    ultimo = None
    for d, n, nivel in dias:
        col, lin = (d - inicio).days // 7, (d.weekday() + 1) % 7
        x, y = x0 + col * passo, y0 + lin * passo
        if (d, n) == pico[:2] and n:
            corpo += '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s"/>' % (x, y, lado, lado, c['lanterna'])
        else:
            corpo += celula(x, y, lado, nivel, c)
        if d.day <= 7 and lin == 0 and d.month != ultimo:
            ultimo = d.month
            if col < semanas - 2:
                corpo += mono(MESES[d.month - 1], x, y0 + 7 * passo + 16, c['fraca'], 9.5)
    # rodapé: as sequências, e a legenda à direita
    y = H - M + 2
    x = M
    for rot, val, destaque in [('Current streak', '%d %s' % (atual, plural(atual, 'day', 'days')), False),
                               ('Longest', '%d %s' % (maior, plural(maior, 'day', 'days')), False),
                               ('Busiest', '%d on %s %d' % (pico[1], MESES[pico[0].month - 1], pico[0].day), True)]:
        corpo += mono(rot, x, y, c['fraca'], 9.5)
        x += larg_mono(rot, 9.5) + 8
        corpo += txt(SANS_M, val, 13, x, y + .5, c['lanterna'] if destaque else c['tinta'])
        x += SANS_M.largura(val, 13) + 26
    lx = W - M
    corpo += mono('More', lx, y, c['fraca'], 9.5, 'end')
    lx -= larg_mono('MORE', 9.5) + 8
    for nivel in (4, 3, 2, 1, 0):
        lx -= 10
        corpo += celula(lx, y - 9, 10, nivel, c)
        lx -= 3
    corpo += mono('Less', lx - 5, y, c['fraca'], 9.5, 'end')
    alt = '%d contributions and %d active days in the last 12 months. Current streak %d days, longest %d. Busiest day: %s, with %d.' % (
        total, ativos, atual, maior, pico[0].isoformat(), pico[1])
    salvar('atividade', t, svg(H, alt, corpo))


if __name__ == '__main__':
    total, dias = buscar()
    for tema in TEMAS:
        grafico(tema, total, dias)
    print('ok', total, len(dias))
