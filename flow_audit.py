#!/usr/bin/env python3
"""Сверка операций (flows) Polyester Scan между API, блокчейном Polyester и исходными сетями.

Шаг 1 — снимок:  python3 flow_audit.py collect     (≈6 мин, пауза между запросами, кэш в data/)
Шаг 2 — проверки: python3 flow_audit.py check       (по снимку + точечные запросы в блокчейн)

Только публичные запросы, стандартная библиотека. Вывод как у scan_probe.py:
ОК / ОШИБКА / ИНФО / НЕТ ДАННЫХ + сырой фрагмент при ошибке.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal

import scan_probe as sp  # адреса, http, report, разбор конфига — в одном месте

SNAP = os.path.join("data", "flows_snapshot.json")
LC = "chain.lifecycle.v1.LifecycleReadService/"
STEPS = ["SOURCE", "REQUEST", "VALIDATION", "TRANSFER", "SETTLEMENT"]
PAUSE_API = 0.7


def rpc(method, body):
    r = sp.http(f"{sp.API}/{LC}{method}", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Connect-Protocol-Version": "1"}, pause=PAUSE_API)
    return sp.rjson(r) or {}


def list_flows(body, pages):
    out, tok = [], ""
    for _ in range(pages):
        b = dict(body, limit=100)
        if tok:
            b["pageToken"] = tok
        d = rpc("ListFlows", b)
        out += d.get("flows", [])
        tok = d.get("nextPageToken")
        if not tok:
            break
    return out


def collect():
    os.makedirs("data", exist_ok=True)
    t0 = time.time()
    snap = {"taken_at": int(t0), "lists": {}, "details": {}}
    snap["lists"]["deposit"] = list_flows({"flowKind": "KIND_DEPOSIT", "scope": "LIST_TERMINAL_ONLY"}, 3)
    snap["lists"]["withdraw"] = list_flows({"flowKind": "KIND_WITHDRAW", "scope": "LIST_TERMINAL_ONLY"}, 2)
    snap["lists"]["open"] = list_flows({"scope": "LIST_OPEN_ONLY"}, 2)
    snap["lists"]["transfer"] = list_flows({"flowKind": "KIND_TRANSFER"}, 1)
    ids = [f["flowId"] for k in ("deposit", "withdraw") for f in snap["lists"][k]]
    for i, fid in enumerate(ids):
        snap["details"][fid] = rpc("GetFlowById", {"flowId": fid}).get("flow")
        if i % 50 == 49:
            print(f"  детали {i + 1}/{len(ids)}", flush=True)
    snap["home_html"] = sp.get(sp.BASE + "/").body
    json.dump(snap, open(SNAP, "w"))
    print("снимок:", {k: len(v) for k, v in snap["lists"].items()}, "деталей", len(snap["details"]),
          f"за {time.time() - t0:.0f} с -> {SNAP}")


def u128(v):
    return (int((v or {}).get("hi", 0)) << 64) | int((v or {}).get("lo", 0))


def steps(f):
    return {x["step"].replace("FLOW_STEP_", ""): x for x in (f or {}).get("observedSteps", [])}


def blockscout_logs(tx):
    r = sp.get(f"{sp.BLOCKSCOUT}/api/v2/transactions/{tx}/logs", pause=1.0)
    out = {}
    for item in (sp.rjson(r) or {}).get("items", []):
        dec = item.get("decoded") or {}
        name = dec.get("method_call", "").split("(")[0]
        if name:
            out[name] = {p["name"]: p["value"] for p in dec.get("parameters", [])}
    return out


def check():
    S = json.load(open(SNAP))
    D, L = S["details"], S["lists"]
    code = {int(a): b for a, b in __import__("re").findall(r'\{chainId:(\d+),code:"([^"]+)"', S["home_html"])}
    age_min = (time.time() - S["taken_at"]) / 60
    print(f"снимок {SNAP}: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(S['taken_at']))} ({age_min:.0f} мин назад)")
    g = "flows"
    dep = [D[f["flowId"]] for f in L["deposit"] if D.get(f["flowId"])]
    wd = [D[f["flowId"]] for f in L["withdraw"] if D.get(f["flowId"])]

    # список = карточка
    diff = [f["flowId"] for k in ("deposit", "withdraw") for f in L[k]
            if D.get(f["flowId"]) and f.get("amountE18") != D[f["flowId"]]["summary"].get("amountE18")]
    sp.report("ОК" if not diff else "ОШИБКА", g, f"ListFlows = GetFlowById ({len(dep) + len(wd)} операций)",
              f"расхождений {len(diff)}", ", ".join(diff[:5]) if diff else None)

    # дубли и уникальность
    k = Counter((f["summary"].get("sourceTxHash", "").lower(), f["summary"].get("txOccurrenceIndex"))
                for f in dep + wd if f["summary"].get("sourceTxHash"))
    dup = [h for h, c in k.items() if c > 1]
    sp.report("ОК" if not dup else "ОШИБКА", g, "одна исходная tx — одна операция", f"дублей {len(dup)}", str(dup[:3]) if dup else None)
    refs = Counter(steps(f)["SETTLEMENT"].get("milestoneTxRef") for f in dep + wd if "SETTLEMENT" in steps(f))
    rep = [r for r, c in refs.items() if r and c > 1]
    sp.report("ОК" if not rep else "ОШИБКА", g, "Settlement Ref уникальны", f"повторов {len(rep)}", str(rep[:3]) if rep else None)

    # п.12 — потерянные шаги (депозиты)
    need = ["SOURCE", "REQUEST", "VALIDATION", "TRANSFER", "SETTLEMENT"]
    inc = defaultdict(list)
    for f in dep:
        miss = [s for s in need if s not in steps(f)]
        if miss:
            inc[code.get(f["summary"]["polyesterChainId"], "?")].append(f["summary"]["flowId"])
    total = sum(len(v) for v in inc.values())
    sp.report("ОШИБКА" if total else "ОК", g, f"п.12 депозиты с потерянными шагами ({len(dep)})",
              f"{total}: " + ", ".join(f"{c} {len(v)}" for c, v in sorted(inc.items())) if total else "нет",
              "примеры: " + ", ".join(v[0] for v in inc.values()) if total else None)

    # п.3 — нет requestFee (депозиты и выводы по сетям)
    for kind, arr in (("депозиты", dep), ("выводы", wd)):
        miss = Counter(code.get(f["summary"]["polyesterChainId"], "?") for f in arr if not f["summary"].get("requestFee"))
        allc = Counter(code.get(f["summary"]["polyesterChainId"], "?") for f in arr)
        sp.report("ОШИБКА" if miss else "ОК", g, f"п.3 {kind} без requestFee",
                  ", ".join(f"{c} {n}/{allc[c]}" for c, n in miss.most_common()) if miss else "у всех есть",
                  "по сетям без комиссии в API" if miss else None)

    # п.3 — доказательство в блокчейне: у первого депозита без requestFee есть DepositFeeLocked
    ex = next((f for f in dep if not f["summary"].get("requestFee") and "REQUEST" in steps(f)), None)
    if ex:
        lg = blockscout_logs(steps(ex)["REQUEST"]["milestoneTxRef"])
        fee = lg.get("DepositFeeLocked", {}).get("feeZAmount")
        sp.report("ОШИБКА" if fee else "ИНФО", g, f"п.3 комиссия в блокчейне у {ex['summary']['flowId']}",
                  f"DepositFeeLocked feeZAmount={fee}, в API requestFee нет" if fee else "DepositFeeLocked не найден",
                  json.dumps(lg.get("DepositFeeLocked", {}))[:300])

    # п.14 — у выводов нет записей из внешней сети
    src = Counter(x.get("lifecycleSource") for f in wd for x in f.get("observedSteps", []))
    sp.report("ОШИБКА" if not src.get("SOURCE_RELAYER") else "ОК", g, f"п.14 выводы: записи из внешней сети ({len(wd)})",
              ", ".join(f"{k} {v}" for k, v in src.items()))

    # открытые операции — не висят ли
    for f in L["open"]:
        age_h = (S["taken_at"] * 1000 - int(f.get("startedAtUnixMs", 0))) / 3.6e6
        sp.report("ОШИБКА" if age_h > 1 else "ОК", g, f"открытая {f['flowId']} ({code.get(f.get('polyesterChainId'), '?')})",
                  f"шаг {f.get('currentStep')}, висит {age_h:.1f} ч")
    print("Итог: " + ", ".join(f"{k} {v}" for k, v in sp.COUNTS.items()))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "collect":
        collect()
    else:
        check()
