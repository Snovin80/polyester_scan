#!/usr/bin/env python3
"""Проверки обозревателя Polyester Scan (testnet) и его API.

Только публичные запросы, только стандартная библиотека Python.
Вывод: по строке на проверку — ОК / ОШИБКА / ИНФО (только по коду, не видно на сайте) / БЛОК (закрыто Cloudflare) / НЕТ ДАННЫХ.
При ошибке ниже печатается сырой ответ сервера (обрезан).

Запуск:
    python3 scan_probe.py                 # все проверки
    python3 scan_probe.py --only bs,site  # группы: site, bs, sol, api
    python3 scan_probe.py --save data/raw # сохранить сырые ответы (data/ в .gitignore)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

# ---- Адреса: всё в одном месте -------------------------------------------
BASE = "https://testnet.polyesterscan.com"           # сам обозреватель (SvelteKit)
BLOCKSCOUT = "https://scan.polyester.live"           # откуда сайт берёт блоки/операции
API = "https://api.testnet.polyester.com"            # API биржи (Connect-RPC, JSON)
RPC = "https://rpc.polyester.live"                   # RPC сети Polyester (testnet)
SOLANA_DEVNET_RPC = "https://api.devnet.solana.com"
SOLANA_MAINNET_RPC = "https://api.mainnet-beta.solana.com"

PAUSE = 1.0          # пауза между запросами к API, сек
PAUSE_STATIC = 0.2   # пауза для статики (JS-файлы с CDN)
TIMEOUT = 30
RAW_LIMIT = 400      # сколько символов сырого ответа печатать при ошибке
# Cloudflare режет стандартный User-Agent Python (403), поэтому свой.
UA = "polyester-scan-probe/0.1 (+public testnet checks)"

SAVE_DIR = None
COUNTS = {"ОК": 0, "ОШИБКА": 0, "ИНФО": 0, "БЛОК": 0, "НЕТ ДАННЫХ": 0}


# ---- HTTP -----------------------------------------------------------------
class Resp:
    def __init__(self, url, status, body):
        self.url, self.status, self.body = url, status, body

    def json(self):
        return json.loads(self.body)

    @property
    def cf_blocked(self):
        return self.status == 403 and "Just a moment" in self.body


def http(url, data=None, headers=None, pause=PAUSE, name=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.1"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            resp = Resp(url, r.status, r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        resp = Resp(url, e.code, e.read().decode("utf-8", "replace"))
    except Exception as e:  # сеть, таймаут
        resp = Resp(url, 0, f"{type(e).__name__}: {e}")
    time.sleep(pause)
    if SAVE_DIR and name:
        fn = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:120]
        with open(os.path.join(SAVE_DIR, fn + ".txt"), "w") as f:
            f.write(f"{'POST' if data is not None else 'GET'} {url}\n")
            if data is not None:
                f.write(data.decode() + "\n")
            f.write(f"HTTP {resp.status}\n\n{resp.body}")
    return resp


def get(url, **kw):
    return http(url, **kw)


def jget(url, **kw):
    """GET и JSON; None, если ответ не 200 или не JSON (обрыв, заглушка Cloudflare)."""
    r = http(url, **kw)
    try:
        return r.json() if r.status == 200 else None
    except ValueError:
        return None


def rjson(r):
    try:
        return r.json()
    except ValueError:
        return None


def rpc_call(method, body):
    """Connect-RPC в JSON-режиме: POST {API}/{пакет.Сервис}/{Метод}."""
    return http(f"{API}/{method}", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Connect-Protocol-Version": "1"},
                name="api_" + method.split("/")[-1] + "_" + json.dumps(body)[:40])


def eth_rpc(method, params):
    r = http(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
             headers={"Content-Type": "application/json"}, pause=0.5)
    return r.json().get("result") if r.status == 200 else None


def sol_rpc(url, method, params):
    r = http(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
             headers={"Content-Type": "application/json"})
    return r


# ---- Вывод ----------------------------------------------------------------
def report(status, group, title, note="", raw=None):
    COUNTS[status] += 1
    line = f"{status:<10} [{group}] {title}"
    if note:
        line += f" — {note}"
    print(line)
    if raw is not None and status in ("ОШИБКА", "БЛОК", "ИНФО"):
        if isinstance(raw, Resp):
            raw = f"{raw.url} -> HTTP {raw.status}: {raw.body}"
        raw = " ".join(str(raw).split())
        print(f"{'':11}ответ: {raw[:RAW_LIMIT]}{'…' if len(raw) > RAW_LIMIT else ''}")


def http_ok_or_4xx(r):
    return r.status and r.status < 500


# ---- Помощники разбора ----------------------------------------------------
def parse_zipper_chains(html):
    """Сети-источники из конфига, встроенного сервером в HTML главной."""
    chains = {}
    for m in re.finditer(r'\{chainId:(\d+),code:"([^"]+)",name:"([^"]+)",nativeChainId:"[^"]*",'
                         r'nativeCurrencySymbol:"[^"]*",explorerUrl:"([^"]*)"', html):
        chains.setdefault(int(m.group(1)), {"code": m.group(2), "name": m.group(3), "explorer": m.group(4)})
    return chains


def parse_zipper_supply(html):
    """(код сети, supply из конфига, адрес zToken, decimals, quantityScale актива)."""
    rows = []
    for am in re.finditer(r'\{asset:"([A-Za-z0-9]+)",ledgerId:\d+,name:"[^"]*",icon:"[^"]*",quantityScale:(\d+)', html):
        seg = html[am.end():am.end() + 20000]
        nxt = re.search(r'\{asset:"[A-Za-z0-9]+",ledgerId:', seg)
        seg = seg[:nxt.start()] if nxt else seg
        for c in re.finditer(r'code:"([a-z0-9\-]+)"[^{}]*?supply:"([^"]*)",sourceToken:\{[^}]*\},'
                             r'zToken:\{address:"(0x[0-9a-fA-F]+)",decimals:(\d+)\}', seg):
            rows.append((am.group(1), c.group(1), c.group(2), c.group(3).lower(), int(c.group(4)), int(am.group(2))))
    return rows


def site_link(explorer_url, kind, value):
    """Повтор логики сайта (чанк CKgKAkPt.js, функция h + подстановка): ссылка на tx/адрес/токен."""
    n = explorer_url.strip()
    ph = "{hash}" if kind == "tx" else "{address}"
    if "{address}" not in n and "{hash}" not in n:
        u = urllib.parse.urlsplit(n)
        origin = f"{u.scheme}://{u.netloc}"
        path = u.path.rstrip("/")
        search = f"?{u.query}" if u.query else ""
        host = u.hostname.lower()
        s = origin + path
        if "xrpl.org" in host:
            n = f"{s}/transactions/{{hash}}{search}" if kind == "tx" else f"{s}/accounts/{{address}}{search}"
        elif "solscan.io" in host:
            e = search or "?cluster=devnet"
            n = {"tx": f"{origin}/tx/{{hash}}{e}", "token": f"{origin}/token/{{address}}{e}"}.get(
                kind, f"{origin}/account/{{address}}{e}")
        elif "tronscan.org" in host:
            n = {"tx": f"{origin}/#/transaction/{{hash}}", "token": f"{origin}/#/token20/{{address}}"}.get(
                kind, f"{origin}/#/address/{{address}}")
        else:
            seg = {"tx": "tx", "token": "token"}.get(kind, "address")
            n = f"{s}/{seg}/{ph}{search}"
    return n.replace(ph, value) if ph in n else (n + value if n.endswith("/") else f"{n}/{value}")


def native_token_link(explorer_url):
    """Сайт для нативного токена берёт только origin от explorerUrl (чанк Dj4nS8JF.js, функция I)."""
    u = urllib.parse.urlsplit(explorer_url.strip())
    return f"{u.scheme}://{u.netloc}"


def loses_network(original, link):
    """True, если ссылка потеряла путь/параметр, который указывал на тестовую сеть."""
    o = urllib.parse.urlsplit(original)
    lk = urllib.parse.urlsplit(link)
    if o.query and o.query not in lk.query:
        return True
    p = o.path.rstrip("/")
    return bool(p) and not lk.path.startswith(p)


def u128(v):
    if isinstance(v, dict):
        return (int(v.get("hi", 0)) << 64) | int(v.get("lo", 0))
    return int(v)


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---- Группа site: сам обозреватель -----------------------------------------
def checks_site(ctx):
    g = "сайт"
    home = get(BASE + "/", name="site_home")
    ctx["home_html"] = home.body if home.status == 200 else ""
    if home.status != 200:
        report("ОШИБКА", g, "главная страница", f"HTTP {home.status}", home)
        return
    m = re.search(r'<html lang="([^"]*)"', home.body)
    lang = m.group(1) if m else None
    if lang and "%" in lang:
        report("ОШИБКА", g, "атрибут lang в <html>", f'незаменённая заглушка lang="{lang}"', f'<html lang="{lang}" ...>')
    else:
        report("ОК", g, "атрибут lang в <html>", f'lang="{lang}"')

    r = get(BASE + "/tx/0xnothex", name="site_tx_bad")
    if r.status == 200:
        report("ОШИБКА", g, "страница /tx/0xnothex (кривой хэш)", "HTTP 200 вместо 404 (мягкая 404)",
               f"GET {BASE}/tx/0xnothex -> HTTP {r.status}, {len(r.body)} байт HTML")
    else:
        report("ОК", g, "страница /tx/0xnothex (кривой хэш)", f"HTTP {r.status}")

    # Служебные страницы разработчиков не должны быть доступны
    for path in ("/dev/sentry-test-client", "/dev/og-images"):
        r = get(BASE + path, name="site_dev" + path.replace("/", "_"))
        title = re.search(r"<title>(.*?)</title>", r.body)
        st = "ОШИБКА" if r.status == 200 else "ОК"
        report(st, g, f"служебная страница {path}", f"HTTP {r.status}" + (f", «{title.group(1)}»" if title and r.status == 200 else ""),
               f"GET {BASE}{path} -> HTTP {r.status}, title={title.group(1) if title else None}")

    # JS-бандлы страниц: ищем зашитые числа и адреса чужой сети
    app = re.search(r'_app/immutable/entry/app\.[\w-]+\.js', home.body)
    if not app:
        report("НЕТ ДАННЫХ", g, "JS-бандлы страниц", "не нашёл entry/app.*.js в HTML")
        return
    app_js = get(f"{BASE}/{app.group(0)}", pause=PAUSE_STATIC).body
    nodes = sorted(set(re.findall(r'nodes/[\w.-]+\.js', app_js)))
    hard, devnet = [], []
    for nd in nodes:
        js = get(f"{BASE}/_app/immutable/{nd}", pause=PAUSE_STATIC).body
        for mm in re.finditer(r'\{txs:(\d+),tps:(\d+)\}', js):
            hard.append((nd, f"txs={mm.group(1)}, tps={mm.group(2)}"))
        tvl = js.find("label:`TVL (Polyester Exchange)`")
        if tvl >= 0:
            seg = js[tvl:tvl + 900]
            if re.search(r'\{value:0,', seg) and re.search(r'percentage:0,', seg):
                hard.append((nd, "TVL value:0, percentage:0"))
        for mm in re.finditer(r'https://api[-.]devnet\.polyester\.[a-z]+[^`"\']{0,40}', js):
            devnet.append((nd, mm.group(0)))
    shown = re.findall(r'(11,124,982|123,922)', home.body)
    if hard:
        report("ОШИБКА", g, "главная: «Total Txns / TPS / TVL (Polyester Exchange)»",
               "числа зашиты в код, а не берутся из API",
               "; ".join(f"{a}: {b}" for a, b in hard))
    else:
        report("ОК", g, "главная: «Total Txns / TPS / TVL (Polyester Exchange)»", "зашитых чисел не нашёл")
    if devnet:
        uniq = sorted({u for _, u in devnet})
        report("ИНФО", g, "панель «API» у расчётов (flow)", "в коде адрес API devnet (кнопка в сборке не показывается)",
               "; ".join(f"{n}: {u}" for n, u in devnet[:3]) + f" (уникальных: {', '.join(uniq)})")
    else:
        report("ОК", g, "панель «API» у расчётов (flow)", "адресов devnet в бандле нет")

    # Ссылки на обозреватели сетей-источников
    chains = parse_zipper_chains(home.body)
    ctx["chains"] = chains
    if not chains:
        report("НЕТ ДАННЫХ", g, "ссылки на обозреватели сетей", "конфиг сетей не найден в HTML")
        return
    bad_tx, bad_native = [], []
    for cid, c in sorted(chains.items()):
        if c["code"].startswith("polyester"):
            continue
        link = site_link(c["explorer"], "tx", "HASH")
        if loses_network(c["explorer"], link):
            bad_tx.append(f'{c["code"]}: {c["explorer"]} -> {link}')
        nat = native_token_link(c["explorer"])
        if loses_network(c["explorer"], nat):
            bad_native.append(f'{c["code"]}: {c["explorer"]} -> {nat}')
    sol = next((c for c in chains.values() if c["code"].startswith("solana")), None)
    if sol:
        link = site_link(sol["explorer"], "tx", "SIG")
        st = "ОК" if "cluster=devnet" in link else "ОШИБКА"
        report(st, g, "ссылка на tx в Solana (по конфигу сайта)", link, f'explorerUrl={sol["explorer"]}')
    report("ОШИБКА" if bad_tx else "ОК", g, f"ссылки на tx сетей-источников ({len(chains)} сетей)",
           "часть ссылок теряет тестовую сеть" if bad_tx else "все сохраняют тестовую сеть",
           "; ".join(bad_tx) if bad_tx else None)
    report("ОШИБКА" if bad_native else "ОК", g, "ссылка «нативный токен» (по коду сайта: origin от explorerUrl)",
           "ведёт в основную сеть: " + ", ".join(b.split(":")[0] for b in bad_native) if bad_native else "",
           "; ".join(bad_native) if bad_native else None)


# ---- Группа bs: Blockscout API (данные сети Polyester) ---------------------
def checks_blockscout(ctx):
    g = "blockscout"
    B = BLOCKSCOUT
    # Поиск
    for title, q, expect_empty in [
        ("поиск: пустой запрос", "", True),
        ("поиск: кривой хэш 0x123", "0x123", True),
        ("поиск: адрес Bitcoin (чужая сеть)", "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", True),
        ("поиск: адрес Solana (чужая сеть)", "So11111111111111111111111111111111111111112", True),
    ]:
        r = get(f"{B}/api/v2/search?q={urllib.parse.quote(q)}", name="bs_search_" + q[:20])
        if r.status == 200:
            report("ОК", g, title, f"HTTP 200, найдено {len(r.json().get('items', []))}")
        elif http_ok_or_4xx(r):
            report("ОК", g, title, f"HTTP {r.status}")
        else:
            report("ОШИБКА", g, title, f"HTTP {r.status}", r)
    for n in (1000, 3000, 5000):
        r = get(f"{B}/api/v2/search?q={'a' * n}", name=f"bs_search_long_{n}")
        st = "ОК" if http_ok_or_4xx(r) else "ОШИБКА"
        report(st, g, f"поиск: строка {n} символов", f"HTTP {r.status}",
               f"GET {B}/api/v2/search?q=aaa…(x{n}) -> HTTP {r.status}, тело: {r.body[:200]!r}")
    r = get(f"{B}/api/v2/search/quick?q=0xzz", name="bs_quick_bad")
    report("ОК" if http_ok_or_4xx(r) else "ОШИБКА", g, "быстрый поиск: 0xzz", f"HTTP {r.status}", r)

    # Кривые адреса страниц
    for title, path, ok in [
        ("tx: кривой хэш 0x1234", "/api/v2/transactions/0x1234", (400, 404, 422)),
        ("tx: нулевой хэш", "/api/v2/transactions/0x" + "0" * 64, (404,)),
        ("блок: -1", "/api/v2/blocks/-1", (400, 404, 422)),
        ("блок: 99999999999999999999", "/api/v2/blocks/99999999999999999999", (400, 404, 422)),
        ("блок: 9223372036854775808 (2^63)", "/api/v2/blocks/9223372036854775808", (400, 404, 422)),
        ("адрес: 0xZZ", "/api/v2/addresses/0xZZ", (400, 404, 422)),
    ]:
        r = get(B + path, name="bs_" + title)
        st = "ОК" if r.status in ok else "ОШИБКА"
        report(st, g, title, f"HTTP {r.status}, ожидалось {'/'.join(map(str, ok))}", r)

    # Листание: блоки
    p1 = get(f"{B}/api/v2/blocks?type=block", name="bs_blocks_p1")
    if p1.status != 200:
        report("ОШИБКА", g, "листание блоков", f"HTTP {p1.status}", p1)
    else:
        d1 = p1.json()
        p2 = get(f"{B}/api/v2/blocks?type=block&" + urllib.parse.urlencode(d1["next_page_params"]), name="bs_blocks_p2")
        d2 = p2.json()
        h1 = [b["height"] for b in d1["items"]]
        h2 = [b["height"] for b in d2["items"]]
        dup = set(h1) & set(h2)
        gap = h1[-1] - h2[0]
        ctx["latest_height"] = h1[0]
        st = "ОК" if not dup and gap == 1 else "ОШИБКА"
        report(st, g, "листание блоков стр.1→2", f"{h1[0]}..{h1[-1]} | {h2[0]}..{h2[-1]}, дублей {len(dup)}, шаг {gap}",
               f"next_page_params={d1['next_page_params']}")

    # Листание: транзакции
    t1 = get(f"{B}/api/v2/transactions?filter=validated", name="bs_txs_p1")
    if t1.status == 200:
        d1 = t1.json()
        ctx["tx_page"] = d1["items"]
        t2 = get(f"{B}/api/v2/transactions?filter=validated&" + urllib.parse.urlencode(d1["next_page_params"]),
                 name="bs_txs_p2")
        d2 = t2.json()
        k1 = [(t["block_number"], t["position"]) for t in d1["items"]]
        k2 = [(t["block_number"], t["position"]) for t in d2["items"]]
        dup = {t["hash"] for t in d1["items"]} & {t["hash"] for t in d2["items"]}
        order_ok = all(a > b for a, b in zip(k1 + k2, (k1 + k2)[1:]))
        st = "ОК" if not dup and order_ok else "ОШИБКА"
        report(st, g, "листание транзакций стр.1→2", f"дублей {len(dup)}, порядок {'строго убывает' if order_ok else 'НАРУШЕН'}",
               f"стр.1 конец {k1[-1]}, next={d1['next_page_params']}, стр.2 начало {k2[0]}")
    else:
        report("ОШИБКА", g, "листание транзакций", f"HTTP {t1.status}", t1)

    # Крайние значения параметров листания
    top = ctx.get("latest_height", 1000)
    for title, params in [
        ("items_count=0", {"block_number": top, "items_count": 0}),
        ("items_count=-1", {"block_number": top, "items_count": -1}),
        ("items_count=10^12", {"block_number": top, "items_count": 10 ** 12}),
        ("items_count=abc", {"block_number": top, "items_count": "abc"}),
        ("block_number=-1", {"block_number": -1, "items_count": 50}),
        ("block_number=0", {"block_number": 0, "items_count": 50}),
        ("block_number=10^20", {"block_number": 10 ** 20, "items_count": 50}),
        ("block_number=abc", {"block_number": "abc", "items_count": 50}),
    ]:
        r = get(f"{B}/api/v2/blocks?type=block&" + urllib.parse.urlencode(params), name="bs_page_" + title)
        note = f"HTTP {r.status}"
        st = "ОК" if http_ok_or_4xx(r) else "ОШИБКА"
        if r.status == 200:
            items = r.json().get("items", [])
            note += f", блоков {len(items)}"
            bn = params["block_number"]
            if isinstance(bn, int) and items and any(b["height"] >= bn for b in items) and bn <= top:
                st, note = "ОШИБКА", note + f", есть блоки ≥ {bn} (должны быть меньше)"
        report(st, g, f"листание блоков: {title}", note, r)

    # Время и суммы: сверка с RPC сети
    txs = ctx.get("tx_page") or []
    if txs:
        t = next((x for x in txs if x.get("value") not in (None, "0")), txs[0])
        blk = eth_rpc("eth_getBlockByNumber", [hex(t["block_number"]), False])
        rtx = eth_rpc("eth_getTransactionByHash", [t["hash"]])
        rcp = eth_rpc("eth_getTransactionReceipt", [t["hash"]])
        if blk and rtx and rcp:
            ts_rpc = int(blk["timestamp"], 16)
            ts_bs = datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()
            now = time.time()
            ok = abs(ts_rpc - ts_bs) < 1 and 1.6e9 < ts_rpc < now + 3600 and t["timestamp"].endswith("Z")
            report("ОК" if ok else "ОШИБКА", g, "время блока: Blockscout vs RPC",
                   f'{t["timestamp"]} vs {iso(ts_rpc)} (RPC={blk["timestamp"]})', json.dumps(t)[:300])
            v_rpc = int(rtx["value"], 16)
            fee_rpc = int(rcp["gasUsed"], 16) * int(rcp.get("effectiveGasPrice") or rtx["gasPrice"], 16)
            ok = str(v_rpc) == t["value"] and str(fee_rpc) == t["fee"]["value"]
            report("ОК" if ok else "ОШИБКА", g, "сумма и комиссия tx: Blockscout vs RPC",
                   f'value {t["value"]} vs {v_rpc}, fee {t["fee"]["value"]} vs {fee_rpc} (wei)', t["hash"])
        else:
            report("НЕТ ДАННЫХ", g, "сверка с RPC", "RPC не ответил")

    # Масштаб сумм: supply из конфига сайта vs total_supply токена в сети
    html = ctx.get("home_html") or get(BASE + "/", name="site_home2").body
    tk = get(f"{B}/api/v2/tokens", name="bs_tokens")
    rows = parse_zipper_supply(html)
    if tk.status == 200 and rows:
        toks = {x["address_hash"].lower(): x for x in tk.json()["items"]}
        bad, checked = [], 0
        for asset, code, sup, addr, dec, qscale in rows:
            x = toks.get(addr)
            if not x or not sup:
                continue
            checked += 1
            on_chain = Decimal(x["total_supply"]) / (Decimal(10) ** int(x["decimals"]))
            cfg = Decimal(sup)
            if int(x["decimals"]) != dec:
                bad.append(f"{x['symbol']}@{code}: decimals {x['decimals']} vs конфиг {dec}")
            elif cfg and not (Decimal("0.5") < on_chain / cfg < Decimal("2")):
                bad.append(f"{x['symbol']}@{code}: конфиг {cfg} vs сеть {on_chain} (x{(on_chain / cfg):.3f})")
        report("ОШИБКА" if bad else "ОК", g, f"масштаб supply: конфиг сайта vs токены сети ({checked} шт.)",
               "расхождение в разы" if bad else "порядок совпадает (нет ×1000)", "; ".join(bad) if bad else None)
    else:
        report("НЕТ ДАННЫХ", g, "масштаб supply", f"токены HTTP {tk.status}, строк конфига {len(rows)}")

    # Согласованность счётчиков
    st_r = get(f"{B}/api/v2/stats", name="bs_stats")
    ct_r = get(f"{BASE}/api/stats/counters", name="site_stats_counters")
    if st_r.status == 200 and ct_r.status == 200:
        s = st_r.json()
        c = {x["id"]: x["value"] for x in ct_r.json()["counters"]}
        comp, tot = int(c.get("completedTxns", 0)), int(c.get("totalTxns", 0))
        report("ОК" if comp <= tot else "ОШИБКА", g, "счётчики: успешных tx ≤ всех tx",
               f"completedTxns={comp}, totalTxns={tot}", f"{BASE}/api/stats/counters -> {ct_r.body[:300]}")
        gt, gu = int(s.get("total_gas_used") or 0), int(s.get("gas_used_today") or 0)
        report("ОК" if not (gu > 0 and gt == 0) else "ОШИБКА", g, "счётчики: total_gas_used",
               f"total_gas_used={gt}, gas_used_today={gu}", st_r.body[:300])
        tb, h = int(s.get("total_blocks") or 0), ctx.get("latest_height")
        if h:
            diff = h + 1 - tb
            report("ОК" if abs(diff) < 1000 else "ОШИБКА", g, "счётчики: total_blocks vs высота сети",
                   f"total_blocks={tb}, последний блок={h}, разница {diff}",
                   f"/api/v2/stats total_blocks={tb}; counters totalBlocks={c.get('totalBlocks')}")
    else:
        report("НЕТ ДАННЫХ", g, "счётчики", f"stats HTTP {st_r.status}, counters HTTP {ct_r.status}")


# ---- Группа sol: реальные операции из Solana ------------------------------
def checks_solana(ctx):
    g = "solana"
    chains = ctx.get("chains") or parse_zipper_chains(get(BASE + "/", name="site_home3").body)
    sol_id, sol = next(((k, v) for k, v in chains.items() if v["code"].startswith("solana")), (None, None))
    if not sol:
        report("НЕТ ДАННЫХ", g, "Solana", "сеть Solana не найдена в конфиге сайта")
        return
    # Контракт приёма депозитов ищем по методу reqDepositZTokens в свежих операциях
    contract, q = None, ""
    for _ in range(3):
        d = jget(f"{BLOCKSCOUT}/api/v2/transactions?filter=validated" + (f"&{q}" if q else ""))
        if d is None:
            break
        contract = next((t["to"]["hash"] for t in d["items"] if t.get("method") == "reqDepositZTokens" and t.get("to")), None)
        if contract or not d.get("next_page_params"):
            break
        q = urllib.parse.urlencode(d["next_page_params"])
    if not contract:
        report("НЕТ ДАННЫХ", g, "поиск депозитов", "не нашёл вызовов reqDepositZTokens в последних операциях")
        return
    sigs, q = [], ""
    for _ in range(10):
        d = jget(f"{BLOCKSCOUT}/api/v2/addresses/{contract}/transactions" + (f"?{q}" if q else ""))
        if d is None:
            break
        for t in d["items"]:
            di = t.get("decoded_input") or {}
            if not di.get("method_call", "").startswith("reqDepositZTokens"):
                continue
            for req in di["parameters"][0]["value"]:
                if int(req[0]) == sol_id:
                    try:
                        sigs.append((bytes.fromhex(req[5][2:]).decode(), t["hash"], t["timestamp"]))
                    except ValueError:
                        pass
        if len(sigs) >= 3 or not d.get("next_page_params"):
            break
        q = urllib.parse.urlencode(d["next_page_params"])
    if not sigs:
        report("НЕТ ДАННЫХ", g, "депозиты из Solana", f"в последних операциях контракта {contract} не нашлось")
        return
    sigs = sigs[:3]
    body = [[s for s, _, _ in sigs], {"searchTransactionHistory": True}]
    dev = sol_rpc(SOLANA_DEVNET_RPC, "getSignatureStatuses", body)
    main = sol_rpc(SOLANA_MAINNET_RPC, "getSignatureStatuses", body)
    try:
        on_dev = [v is not None for v in rjson(dev)["result"]["value"]]
        on_main = [v is not None for v in rjson(main)["result"]["value"]]
    except (TypeError, KeyError):
        report("НЕТ ДАННЫХ", g, "проверка подписей в Solana", "RPC Solana не ответил", f"{dev.body[:150]} | {main.body[:150]}")
        return
    for (sig, ptx, ts), d_, m_ in zip(sigs, on_dev, on_main):
        net = "devnet" if d_ and not m_ else ("mainnet" if m_ and not d_ else f"devnet={d_}, mainnet={m_}")
        link = site_link(sol["explorer"], "tx", sig)
        ok = (net == "devnet" and "cluster=devnet" in link) or (net == "mainnet" and "cluster=" not in link)
        report("ОК" if ok else "ОШИБКА", g, f"депозит {sig[:12]}… ({ts[:16]})",
               f"tx найдена в {net}; ссылка сайта {link[:60]}…", f"Polyester tx {ptx}; ссылка {link}")
    nat = native_token_link(sol["explorer"])
    report("ОШИБКА" if "cluster=" not in nat and on_dev[0] and not on_main[0] else "ОК", g,
           "ссылка «нативный токен» SOL (по коду сайта)", f"{nat} — основная сеть, а операции в devnet",
           f"explorerUrl={sol['explorer']} -> new URL(...).origin = {nat}")


# ---- Группа api: API биржи (Connect-RPC) ------------------------------------
def checks_api(ctx):
    g = "api"
    LF = "chain.lifecycle.v1.LifecycleReadService/ListFlows"
    # Доступные без Cloudflare методы биржи: единицы времени
    r = rpc_call("marketdata.v1.MarketDataService/GetSpotConfig", {})
    if r.status == 200:
        ts = int(r.json().get("tsSec", 0))
        ok = 1.6e9 < ts < time.time() + 3600
        report("ОК" if ok else "ОШИБКА", g, "GetSpotConfig.tsSec в секундах", f"{ts} = {iso(ts) if ok else '?'}", r)
    else:
        report("БЛОК" if r.cf_blocked else "ОШИБКА", g, "GetSpotConfig", f"HTTP {r.status}", r)
    r = rpc_call("marketoverview.v1.MarketOverviewService/ListMarketOverview", {})
    if r.status == 200:
        mk = [m for m in r.json().get("markets", []) if m.get("lastTradeTsNs")]
        bad = [m for m in mk if not (1.6e18 < int(m["lastTradeTsNs"]) < (time.time() + 3600) * 1e9)]
        report("ОШИБКА" if bad else "ОК", g, f"ListMarketOverview.lastTradeTsNs в наносекундах ({len(mk)} рынков)",
               "есть значения не в нс" if bad else "все значения правдоподобны", json.dumps(bad[:2]) if bad else None)
    else:
        report("БЛОК" if r.cf_blocked else "ОШИБКА", g, "ListMarketOverview", f"HTTP {r.status}", r)

    # Операции (flows). Из облачных IP закрыто Cloudflare — тогда БЛОК.
    first = rpc_call(LF, {"limit": 5})
    if first.cf_blocked:
        report("БЛОК", g, "ListFlows и остальные проверки flows",
               "Cloudflare «Just a moment» — запустить с домашнего ПК", first)
        return
    if first.status != 200:
        report("ОШИБКА", g, "ListFlows {limit:5}", f"HTTP {first.status}", first)
        return
    for title, body, max_items, expect_4xx in [
        ("limit=0", {"limit": 0}, 500, False),
        ("limit=1", {"limit": 1}, 1, False),
        ("limit=500", {"limit": 500}, 500, False),
        ("limit=501 (клиент сайта разрешает максимум 500)", {"limit": 501}, 500, False),
        ("limit=-1", {"limit": -1}, 0, True),
        ("limit=2^32 (переполнение uint32)", {"limit": 2 ** 32}, 0, True),
        ("pageToken=мусор", {"limit": 5, "pageToken": "!!!garbage!!!"}, 0, True),
    ]:
        r = rpc_call(LF, body)
        if r.status >= 500 or r.status == 0:
            report("ОШИБКА", g, f"ListFlows {title}", f"HTTP {r.status} (ошибка сервера)", r)
        elif expect_4xx:
            report("ОК" if 400 <= r.status < 500 else "ОШИБКА", g, f"ListFlows {title}",
                   f"HTTP {r.status}, ожидалось 4xx (invalid_argument)", r)
        elif r.status == 200:
            n = len(r.json().get("flows", []))
            report("ОК" if n <= max_items else "ОШИБКА", g, f"ListFlows {title}", f"вернул {n} (ожидалось ≤ {max_items})",
                   r.body[:300])
        else:
            report("ОК", g, f"ListFlows {title}", f"HTTP {r.status}", r)

    # Листание flows: дубли между страницами
    a = rjson(rpc_call(LF, {"limit": 20})) or {}
    tok = a.get("nextPageToken")
    if tok:
        b = rjson(rpc_call(LF, {"limit": 20, "pageToken": tok})) or {}
        ids1 = [f["flowId"] for f in a.get("flows", [])]
        ids2 = [f["flowId"] for f in b.get("flows", [])]
        dup = set(ids1) & set(ids2)
        report("ОК" if not dup else "ОШИБКА", g, "ListFlows листание стр.1→2", f"{len(ids1)}+{len(ids2)}, дублей {len(dup)}",
               ", ".join(sorted(dup)[:5]))
    else:
        report("НЕТ ДАННЫХ", g, "ListFlows листание", "нет nextPageToken")

    # Время и суммы во flows
    flows = a.get("flows", [])
    bad_t, bad_a = [], []
    for f in flows:
        for k in ("startedAtUnixMs", "updatedAtUnixMs", "lastActivityAtUnixMs"):
            v = f.get(k)
            if v in (None, "", "0", 0):
                continue
            v = int(v)
            if not (1.6e12 < v < (time.time() + 86400) * 1000):
                bad_t.append(f'{f["flowId"]}.{k}={v}')
        if "amountE18" in f:
            try:
                u128(f["amountE18"])
            except Exception:
                bad_a.append(f'{f["flowId"]}.amountE18={f["amountE18"]}')
    report("ОШИБКА" if bad_t else "ОК", g, f"flows: время в миллисекундах ({len(flows)} шт.)",
           "есть значения не в мс" if bad_t else "всё правдоподобно", "; ".join(bad_t[:5]) if bad_t else None)
    report("ОШИБКА" if bad_a else "ОК", g, "flows: формат amountE18", "", "; ".join(bad_a[:5]) if bad_a else None)

    # Кривые запросы к одной операции
    for title, method, body in [
        ("ListFlowsByTx: хэш 0x123", "chain.lifecycle.v1.LifecycleReadService/ListFlowsByTx", {"txHash": "0x123"}),
        ("ListFlowsByTx: пустой хэш", "chain.lifecycle.v1.LifecycleReadService/ListFlowsByTx", {"txHash": ""}),
        ("GetFlowById: flow_0 (кривой id)", "chain.lifecycle.v1.LifecycleReadService/GetFlowById", {"flowId": "flow_0"}),
        ("GetFlowById: несуществующий", "chain.lifecycle.v1.LifecycleReadService/GetFlowById", {"flowId": "flow_1111111111"}),
    ]:
        r = rpc_call(method, body)
        report("ОК" if 200 <= r.status < 500 else "ОШИБКА", g, title, f"HTTP {r.status}", r)

    # Страницы реальных операций: ссылки на обозреватели сетей-источников в HTML.
    # Берём сети, где тестовая сеть задана путём/параметром (Solana, Bitcoin, Litecoin),
    # и Solana отдельно — у неё подписи base58, регистр важен.
    chains = ctx.get("chains") or parse_zipper_chains(get(BASE + "/", name="site_home4").body)
    for cid, c in sorted(chains.items()):
        exp = c["explorer"]
        if not (loses_network(exp, native_token_link(exp)) or c["code"].startswith("solana")):
            continue
        host = urllib.parse.urlsplit(exp).netloc
        d = rjson(rpc_call(LF, {"limit": 3, "polyesterChainIds": [cid]})) or {}
        fl = [f for f in d.get("flows", []) if f.get("flowId")]
        if not fl:
            report("НЕТ ДАННЫХ", g, f"страница операции {c['code']}", "операций этой сети в API нет")
            continue
        f = next((x for x in fl if x.get("flowKind") == "KIND_DEPOSIT"), fl[0])
        page = get(f"{BASE}/flow/{f['flowId']}", name=f"site_flow_{f['flowId']}")
        hrefs = sorted(set(h for h in re.findall(r'href="(https?://[^"]+)"', page.body) if host in h))
        wrong = [h for h in hrefs if loses_network(exp, h)]
        report("ОШИБКА" if wrong else "ОК", g, f"страница {f['flowId']} ({c['code']}): ссылки на {host}",
               f"{len(wrong)} из {len(hrefs)} ведут в основную сеть" if wrong else f"{len(hrefs)} ссылок, сеть сохранена",
               f"{BASE}/flow/{f['flowId']}: " + ", ".join(wrong) if wrong else None)
        src = (f.get("sourceTxHash") or "").strip()
        if c["code"].startswith("solana") and src and src != src.lower() and not src.startswith("0x"):
            low = [h for h in hrefs if src.lower() in h]
            report("ОШИБКА" if low else "ОК", g, f"страница {f['flowId']}: регистр подписи Solana в ссылках",
                   "подпись приведена к нижнему регистру — ссылка битая" if low else "регистр сохранён",
                   "; ".join(low) + f" (верная подпись: {src})" if low else None)
            st = rjson(sol_rpc(SOLANA_DEVNET_RPC, "getSignatureStatuses", [[src], {"searchTransactionHistory": True}]))
            mn = rjson(sol_rpc(SOLANA_MAINNET_RPC, "getSignatureStatuses", [[src], {"searchTransactionHistory": True}]))
            if st and mn and "result" in st and "result" in mn:
                on_dev, on_main = st["result"]["value"][0] is not None, mn["result"]["value"][0] is not None
                report("ОК" if on_dev and not on_main else "ОШИБКА", g, f"подпись {src[:12]}… в сети Solana",
                       f"devnet={on_dev}, mainnet={on_main}")

    # Комиссия за ввод: у каждой сети есть networkFee (в конфиге), биржа его удерживает.
    # Проверяем, что API указывает удержание (requestFee) — иначе сайт пишет «Network Fee: None».
    dep, tok = [], ""
    for _ in range(2):
        body = {"limit": 100, "flowKind": "KIND_DEPOSIT", "scope": "LIST_TERMINAL_ONLY"}
        if tok:
            body["pageToken"] = tok
        d = rjson(rpc_call(LF, body)) or {}
        dep += d.get("flows", [])
        tok = d.get("nextPageToken")
        if not tok:
            break
    if not dep:
        report("НЕТ ДАННЫХ", g, "депозиты: комиссия", "завершённых депозитов нет")
        return
    by_chain = {}
    for f in dep:
        by_chain.setdefault(f.get("polyesterChainId"), []).append(f)
    good = []
    for cid, fs in sorted(by_chain.items(), key=lambda x: str(x[0])):
        name = (chains.get(cid) or {}).get("code", f"chain {cid}")
        missing = [f for f in fs if not f.get("requestFee")]
        if not missing:
            good.append(f"{name} {len(fs)}")
            continue
        examples = []
        for f in missing[:2]:
            fw = (rjson(rpc_call("chain.lifecycle.v1.LifecycleReadService/GetFlowById", {"flowId": f["flowId"]})) or {}).get("flow") or {}
            steps = [s for s in fw.get("observedSteps", []) if s.get("amountE18")]
            if len(steps) >= 2:
                a0, a1 = u128(steps[0]["amountE18"]), u128(steps[-1]["amountE18"])
                examples.append(f'{f["flowId"]}: {Decimal(a0) / 10**18:f} → {Decimal(a1) / 10**18:f}')
        report("ОШИБКА", g, f"депозиты {name}: нет поля комиссии (requestFee)",
               f"{len(missing)} из {len(fs)} — сайт покажет «Network Fee: None»",
               "удержание по шагам: " + "; ".join(examples))
    report("ОК", g, "депозиты: комиссия указана", ", ".join(good) if good else "—")

    # Полнота шагов: у завершённого депозита должны быть все наблюдённые стадии
    need = ["SOURCE", "REQUEST", "VALIDATION", "TRANSFER", "SETTLEMENT"]
    inc, total = [], 0
    for f in dep[:20]:
        fw = (rjson(rpc_call("chain.lifecycle.v1.LifecycleReadService/GetFlowById", {"flowId": f["flowId"]})) or {}).get("flow")
        if not fw:
            continue
        total += 1
        seen = {x.get("step", "").replace("FLOW_STEP_", "") for x in fw.get("observedSteps", [])}
        miss = [k for k in need if k not in seen]
        if miss:
            name = (chains.get(f.get("polyesterChainId")) or {}).get("code", "?")
            inc.append(f'{f["flowId"]} ({name}): нет {",".join(miss)}')
    report("ОШИБКА" if inc else "ОК", g, f"депозиты: потерянные шаги ({total} последних)",
           f"неполных {len(inc)}" if inc else "все шаги на месте", "; ".join(inc[:4]) if inc else None)

def main():
    global SAVE_DIR
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", default="site,bs,sol,api", help="группы через запятую: site,bs,sol,api")
    ap.add_argument("--save", metavar="DIR", help="сохранять сырые ответы в папку")
    a = ap.parse_args()
    if a.save:
        SAVE_DIR = a.save
        os.makedirs(SAVE_DIR, exist_ok=True)
    groups = [x.strip() for x in a.only.split(",")]
    print(f"Polyester Scan probe — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    ctx = {}
    for key, fn in [("site", checks_site), ("bs", checks_blockscout), ("sol", checks_solana), ("api", checks_api)]:
        if key in groups:
            try:
                fn(ctx)
            except Exception as e:  # одна упавшая группа не должна ронять остальные
                report("НЕТ ДАННЫХ", key, "группа прервана", f"{type(e).__name__}: {e}")
    print("Итог: " + ", ".join(f"{k} {v}" for k, v in COUNTS.items()))
    return 1 if COUNTS["ОШИБКА"] else 0


if __name__ == "__main__":
    sys.exit(main())
