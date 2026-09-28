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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "collect":
        collect()
    else:
        print("check: см. ниже")
