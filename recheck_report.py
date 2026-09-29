# =====================================================================================
#  ПЕРЕПРОВЕРКА ОТЧЁТА 28.09.2026 — что команда Polyester исправила, а что нет
# =====================================================================================
#
#  ЧТО ДЕЛАЕТ
#    Проходит по пунктам отправленного отчёта (docs/report_2026-09-28.md) и по каждому
#    пишет одну строку:
#       ИСПРАВЛЕНО      — ошибки больше нет
#       НЕ ИСПРАВЛЕНО   — ошибка на месте (рядом цифры/пример)
#       НЕ ЯСНО         — не хватило данных (например, ещё нет новых операций)
#    Не проверяет: выгрузки CSV (п.17) и застывший счётчик (п.5).
#
#  КАК ЗАПУСТИТЬ (Windows, PowerShell)
#    1. Нужен Python 3.9 или новее (проверить: python --version).
#    2. Скачать этот файл с GitHub (кнопка «Download raw file») в любую папку.
#    3. В PowerShell перейти в эту папку и выполнить:
#          python recheck_report.py
#       Работает 2–3 минуты (между запросами пауза, сервер не нагружает).
#    4. Если хочется смотреть только операции после определённой даты
#       (например, после того как команда сказала «исправили»):
#          python recheck_report.py --since 2026-10-01
#       По умолчанию смотрит операции, начатые после 29.09.2026 00:00 UTC.
#
#  ВАЖНО ПРО СТАРЫЕ ОПЕРАЦИИ
#    Команда часто чинит только новые данные, а старые операции остаются как были.
#    Поэтому пункты про данные операций (комиссия, шаги, доставка) скрипт считает
#    ТОЛЬКО по операциям, начатым после даты --since. Примеры из отчёта выводятся
#    отдельной строкой «для сведения» и на итог не влияют.
#    Пункты про сайт (ссылки, заглушки, страницы) проверяются на примерах из отчёта:
#    страницы строятся заново при каждом открытии, поэтому видно текущий код сайта.
#
#  ЧТО НУЖНО
#    Только Python, без установки библиотек и без ключей — всё публичное.
#
# =====================================================================================

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---- Адреса (всё в одном месте) ----------------------------------------------------
SITE = "https://testnet.polyesterscan.com"      # обозреватель
BLOCKSCOUT = "https://scan.polyester.live"      # данные блокчейна Polyester
API = "https://api.testnet.polyester.com"       # API биржи (операции ввода/вывода)
RPC = "https://rpc.polyester.live"              # RPC сети Polyester

PAUSE = 0.7
UA = "polyester-recheck/1.0 (+public testnet checks)"   # стандартный UA Python Cloudflare режет
LC = "chain.lifecycle.v1.LifecycleReadService/"

# Примеры из отчёта
EX_FEE_DEPOSIT = "flow_4xW7RUSVcPK"      # XRP, комиссия 0.2 удержана, в API нет
EX_FEE_WITHDRAW = "flow_WmsSrDpe1Ng"     # вывод 100 USDC, получено 99.6
EX_LOST_STEPS = "flow_ab1QeSbCqcE"       # только SOURCE и SETTLEMENT
EX_STUCK = "flow_6DSDcV3jmMw"            # висит на SOURCE с 24.09
EX_SOLANA_PAGE = "flow_SMQSpzMh1NM"      # подпись Solana в нижнем регистре
EX_MAINNET_LINKS = {"flow_SMQSpzMh1NM": ("solscan.io", "?cluster=devnet"),
                    "flow_frT2okTWCsw": ("mempool.space", "/testnet"),
                    "flow_4LoDbiGuScY": ("litecoinspace.org", "/testnet")}
EX_PROXY_TX = "0x10c5d7a58a06c72835251cb24f2509b9b60797201ca2763fb3ab2e4ae6477c14"
SOL_SIG = "45bQAAfmzUhjAAwe3XJsPDxPS8PtJa6mLxkMgU31SQYts7H8rQbTHTFajeSZr4XXKZQpbVtQQSTSfW1wLRxfhMHJ"
STEPS = ["SOURCE", "REQUEST", "VALIDATION", "TRANSFER", "SETTLEMENT"]

RESULTS = {"ИСПРАВЛЕНО": 0, "НЕ ИСПРАВЛЕНО": 0, "НЕ ЯСНО": 0}


def http(url, body=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.1"}
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, text = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        status, text = 0, f"{type(e).__name__}: {e}"
    time.sleep(PAUSE)
    return status, text


def js(text):
    try:
        return json.loads(text)
    except ValueError:
        return {}


def lc(method, body):
    st, t = http(API + "/" + LC + method, body,
                 {"Content-Type": "application/json", "Connect-Protocol-Version": "1"})
    return js(t) if st == 200 else {}


def steps(flow):
    return {x["step"].replace("FLOW_STEP_", ""): x for x in (flow or {}).get("observedSteps", [])}


def result(status, item, note):
    RESULTS[status] += 1
    print(f"{status:<14} {item} — {note}")


def info(item, note):
    print(f"{'  для сведения':<14} {item} — {note}")


def list_flows(body, pages, since_ms):
    out, tok = [], ""
    for _ in range(pages):
        b = dict(body, limit=100)
        if tok:
            b["pageToken"] = tok
        d = lc("ListFlows", b)
        out += d.get("flows", [])
        tok = d.get("nextPageToken")
        if not tok:
            break
    return [f for f in out if int(f.get("startedAtUnixMs", 0)) >= since_ms]


# ---- Пункты отчёта про данные операций ------------------------------------------------
def check_fee(since_ms):
    item = "п.3 комиссия (requestFee) у депозитов XRP/SOL"
    new = []
    for cid in (9, 3):
        new += list_flows({"flowKind": "KIND_DEPOSIT", "scope": "LIST_TERMINAL_ONLY", "polyesterChainIds": [cid]}, 1, since_ms)
    miss = [f["flowId"] for f in new if not f.get("requestFee")]
    if not new:
        result("НЕ ЯСНО", item, "новых завершённых депозитов XRP/SOL после даты нет")
    else:
        result("НЕ ИСПРАВЛЕНО" if miss else "ИСПРАВЛЕНО", item,
               f"без комиссии {len(miss)} из {len(new)} новых" + (f", пример {miss[0]}" if miss else ""))

    item = "п.3 комиссия (requestFee) у выводов"
    new = list_flows({"flowKind": "KIND_WITHDRAW", "scope": "LIST_TERMINAL_ONLY"}, 2, since_ms)
    miss = [f["flowId"] for f in new if not f.get("requestFee")]
    if not new:
        result("НЕ ЯСНО", item, "новых завершённых выводов после даты нет")
    else:
        result("НЕ ИСПРАВЛЕНО" if miss else "ИСПРАВЛЕНО", item,
               f"без комиссии {len(miss)} из {len(new)} новых" + (f", пример {miss[0]}" if miss else ""))

    for fid in (EX_FEE_DEPOSIT, EX_FEE_WITHDRAW):
        s = (lc("GetFlowById", {"flowId": fid}).get("flow") or {}).get("summary", {})
        info(f"пример {fid}", "requestFee " + ("есть" if s.get("requestFee") else "нет"))
    return new


def check_delivery(new_withdrawals):
    item = "п.14 у выводов ссылка на транзакцию доставки"
    sample = new_withdrawals[:20]
    if not sample:
        result("НЕ ЯСНО", item, "новых завершённых выводов после даты нет")
        return
    with_ext = 0
    for f in sample:
        d = lc("GetFlowById", {"flowId": f["flowId"]}).get("flow") or {}
        srcs = {x.get("lifecycleSource") for x in d.get("observedSteps", [])}
        srcs |= {a.get("lifecycleSource") for x in d.get("observedSteps", []) for a in x.get("activities", [])}
        if srcs - {"SOURCE_POLYESTER_CHAIN", "SOURCE_LEDGER", None}:
            with_ext += 1
    result("ИСПРАВЛЕНО" if with_ext == len(sample) else "НЕ ИСПРАВЛЕНО", item,
           f"запись из сети назначения есть у {with_ext} из {len(sample)} новых выводов")


def check_steps(since_ms):
    item = "п.12 потерянные шаги у депозитов"
    new = list_flows({"flowKind": "KIND_DEPOSIT", "scope": "LIST_TERMINAL_ONLY"}, 1, since_ms)[:30]
    if not new:
        result("НЕ ЯСНО", item, "новых завершённых депозитов после даты нет")
    else:
        bad, votes = [], []
        for f in new:
            st = steps(lc("GetFlowById", {"flowId": f["flowId"]}).get("flow"))
            if any(k not in st for k in STEPS):
                bad.append(f["flowId"])
            v = st.get("VALIDATION")
            if v and int(v.get("approveCount", 0)) < int(v.get("requiredApprovals", 0)):
                votes.append(f["flowId"])
        result("НЕ ИСПРАВЛЕНО" if bad else "ИСПРАВЛЕНО", item,
               f"неполных {len(bad)} из {len(new)} новых" + (f", пример {bad[0]}" if bad else ""))
        result("НЕ ИСПРАВЛЕНО" if votes else "ИСПРАВЛЕНО", "п.12 голоса валидаторов (approveCount < нужного)",
               f"{len(votes)} из {len(new)} новых" + (f", пример {votes[0]}" if votes else ""))

    s = (lc("GetFlowById", {"flowId": EX_STUCK}).get("flow") or {}).get("summary", {})
    result("НЕ ИСПРАВЛЕНО" if s.get("isOpen") else "ИСПРАВЛЕНО", f"п.12 зависшая операция {EX_STUCK}",
           f"шаг {s.get('currentStep')}, открыта: {s.get('isOpen')}")
    st = steps(lc("GetFlowById", {"flowId": EX_LOST_STEPS}).get("flow"))
    info(f"пример {EX_LOST_STEPS}", "шаги: " + ", ".join(st.keys()))


# ---- Пункты отчёта про сайт -----------------------------------------------------------
def hrefs(fid):
    st, html = http(f"{SITE}/flow/{fid}")
    return st, sorted(set(re.findall(r'href="(https?://[^"]+)"', html)))


def check_site():
    st, links = hrefs(EX_SOLANA_PAGE)
    low = [h for h in links if SOL_SIG.lower() in h]
    if st != 200:
        result("НЕ ЯСНО", "п.1 ссылка Solana в нижнем регистре", f"страница не открылась (HTTP {st})")
    else:
        result("НЕ ИСПРАВЛЕНО" if low else "ИСПРАВЛЕНО", "п.1 ссылка Solana в нижнем регистре",
               "в шаге Deposit Seen подпись строчными" if low else "строчной подписи на странице нет")

    bad = []
    for fid, (host, keep) in EX_MAINNET_LINKS.items():
        st, links = hrefs(fid)
        bad += [f"{fid}: {h}" for h in links if host in h and keep not in h]
    result("НЕ ИСПРАВЛЕНО" if bad else "ИСПРАВЛЕНО", "п.2 ссылки «сеть/нативный токен» в основную сеть (SOL/BTC/LTC)",
           f"таких ссылок {len(bad)}" + (f", пример {bad[0]}" if bad else ""))

    st, t = http(f"{BLOCKSCOUT}/api/v2/internal-transactions")
    items = js(t).get("items", [])
    st2, t2 = http(f"{BLOCKSCOUT}/api/v2/transactions/{EX_PROXY_TX}/internal-transactions")
    result("ИСПРАВЛЕНО" if items and js(t2).get("items") else "НЕ ИСПРАВЛЕНО", "п.16 внутренние транзакции",
           f"во всей сети {len(items)} на 1-й странице, у примера {len(js(t2).get('items', []))}")

    st, home = http(SITE + "/")
    m = re.search(r"_app/immutable/entry/app\.[\w-]+\.js", home)
    found = None
    if m:
        st, app = http(f"{SITE}/{m.group(0)}")
        for node in sorted(set(re.findall(r"nodes/[\w.-]+\.js", app))):
            st, code = http(f"{SITE}/_app/immutable/{node}")
            hit = re.search(r"\{txs:\d+,tps:\d+\}", code)
            if hit or "label:`TVL (Polyester Exchange)`" in code:
                found = (node, hit.group(0) if hit else "TVL")
                break
    if not m:
        result("НЕ ЯСНО", "п.4 заглушки на главной", "не нашёл код сайта")
    else:
        result("НЕ ИСПРАВЛЕНО" if found and found[1] != "TVL" else "ИСПРАВЛЕНО", "п.4 заглушки на главной (Total Txns/TPS)",
               f"в коде {found[1]}" if found and found[1] != "TVL" else "зашитых чисел не найдено")

    st, t = http(f"{SITE}/dev/sentry-test-client")
    result("НЕ ИСПРАВЛЕНО" if st == 200 else "ИСПРАВЛЕНО", "п.11 отладочная страница /dev/sentry-test-client",
           f"HTTP {st}")

    st, t = http(f"{BLOCKSCOUT}/api/v2/blocks/99999999999999999999")
    result("НЕ ИСПРАВЛЕНО" if st >= 500 else "ИСПРАВЛЕНО", "п.7 огромный номер блока", f"HTTP {st} {t[:40]}")

    lang = re.search(r'<html lang="([^"]*)"', home)
    result("НЕ ИСПРАВЛЕНО" if lang and "%" in lang.group(1) else "ИСПРАВЛЕНО", "п.9 lang у страниц",
           f'lang="{lang.group(1) if lang else "?"}"')


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Перепроверка отчёта Polyester Scan от 28.09.2026")
    ap.add_argument("--since", default="2026-09-29", help="смотреть операции, начатые после этой даты (UTC), ГГГГ-ММ-ДД")
    a = ap.parse_args()
    since = datetime.strptime(a.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    since_ms = int(since.timestamp() * 1000)
    print(f"Перепроверка отчёта 28.09 — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, операции после {a.since}")
    print("-" * 90)
    new_wd = check_fee(since_ms)
    check_delivery(new_wd)
    check_steps(since_ms)
    check_site()
    print("-" * 90)
    print("Итог: " + ", ".join(f"{k} {v}" for k, v in RESULTS.items()))


if __name__ == "__main__":
    main()
