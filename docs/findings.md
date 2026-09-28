# Находки: Polyester Scan testnet

Проверено 28.09.2026, 15:40–16:15 UTC, живыми запросами из облачной среды.
Основные находки 1–10 повторяет `python3 scan_probe.py` (п. 5 — только если застанет отставание счётчика).
Сверить с документацией не удалось: `testnet.polyester.com/docs/...` из облака закрыт
проверкой Cloudflare. Ссылки на доки нужно добавить вручную.

Порядок — от важного к мелочам.

---

## 1. Подпись Solana в ссылке шага «Deposit Seen» переведена в нижний регистр — ссылка битая

**Где:** страница операции, список шагов (слева) и «Journey»: шаг `1 Deposit Seen`.

**Запрос:** `GET https://testnet.polyesterscan.com/flow/flow_SMQSpzMh1NM` (депозит 0.01 tSOL из Solana Devnet).

**Сырой ответ (ссылки `href` из HTML):**
```
https://solscan.io/tx/45bqaafmzuhjaawe3xjspdxps8ptja6mlxkmgu31sqyts7h8rqbthtfajeszr4xxkzqpbvtqqstsfw1wlrxfhmhj?cluster=devnet   <- шаг «Deposit Seen» (2 шт.)
https://solscan.io/tx/45bQAAfmzUhjAAwe3XJsPDxPS8PtJa6mLxkMgU31SQYts7H8rQbTHTFajeSZr4XXKZQpbVtQQSTSfW1wLRxfhMHJ?cluster=devnet   <- строка «Source Tx» (верно)
```
Проверка в самой сети Solana (`POST https://api.devnet.solana.com`, `getSignatureStatuses`):
```
45bQAAfmzUhj… -> {"value":[{"confirmationStatus":"finalized","slot":505140632,"err":null,…}]}
45bqaafmzuhj… -> {"error":{"code":-32602,"message":"Invalid param: Invalid"}}
```
API отдаёт подпись правильно (`GetFlowById` → `sourceTxHash`, `milestoneTxRef` = `45bQAAfm…MHJ`).

**Ожидалось:** подпись как есть. В Solana подпись — base58, регистр в нём значимый.
В конфиге сайта у сети стоит `isCaseSensitive:true`.

**Почему ошибка:** ссылка ведёт на несуществующую транзакцию. Причина в коде:
`chunks/B-stKme4.js` — `function I(e){return e.trim().toLowerCase()}` применяется к `txRef` шага
перед построением внешней ссылки. Для hex-хэшей EVM это безвредно, для Solana ломает ссылку.
Та же функция переводит в нижний регистр хэши XRP (в API они в верхнем: `D0B960EF…`) —
принимает ли такие `testnet.xrpl.org`, **не проверено**.

---

## 2. Ссылки «сеть» и «нативный токен» ведут в основную сеть (Solana, Bitcoin, Litecoin)

**Где:** страница операции, строки `Source Chain` / `Destination Chain` и `Token … (Native)`.

**Запросы и сырые ответы (`href` из HTML страниц):**
```
GET /flow/flow_SMQSpzMh1NM  (solana-devnet)    -> href="https://solscan.io"        (x2: Source Chain, Token tSOL (Native))
GET /flow/flow_PtjQaxSbm23  (solana-devnet, вывод) -> href="https://solscan.io"    (Destination Chain, Token tSOL (Native))
GET /flow/flow_frT2okTWCsw  (bitcoin-testnet3) -> href="https://mempool.space"
GET /flow/flow_d2gqpy4RJHc  (litecoin-testnet) -> href="https://litecoinspace.org"
```
Конфиг сети в том же HTML: `explorerUrl:"https://solscan.io/?cluster=devnet"`,
`"https://mempool.space/testnet"`, `"https://litecoinspace.org/testnet"`.

Операции Solana действительно в devnet: 3 подписи депозитов (из `reqDepositZTokens` в сети Polyester
и из `ListFlows`) найдены в `api.devnet.solana.com` и **не найдены** в `api.mainnet-beta.solana.com`:
```
devnet  [{'slot': 505140632, 'status': 'finalized'}, {'slot': 505047642, …}, {'slot': 504950707, …}]
mainnet [None, None, None]
```

**Ожидалось:** `https://solscan.io/?cluster=devnet`, `https://mempool.space/testnet`,
`https://litecoinspace.org/testnet`.

**Почему ошибка:** ведёт на главную основной сети. Причина: `chunks/Dj4nS8JF.js`,
`function I(e){ return new URL(e).origin }` — от адреса остаётся только домен.

**Что в порядке (важно для отчёта):** ссылки на **транзакции и адреса** Solana содержат
`?cluster=devnet` и работают (`Source Tx`, `Sender Address`, `Deposit Address`). Подозрение
из CLAUDE.md «у Solana основной solscan.io» подтвердилось только для ссылок «сеть/токен».

---

## 3. «Network Fee: None», а сумма уменьшилась на размер комиссии

**Запрос:** `POST https://api.testnet.polyester.com/chain.lifecycle.v1.LifecycleReadService/GetFlowById`
`{"flowId":"flow_4xW7RUSVcPK"}` (депозит tXRP из ripple-testnet).

**Сырой ответ (сокращено):**
```
summary: flowKind=KIND_DEPOSIT, polyesterChainId=9, amountE18={"lo":"2000000000000000000"}, requestFee=<нет поля>
FLOW_STEP_SOURCE     amountE18.lo = 2000000000000000000
FLOW_STEP_REQUEST    amountE18.lo = 2000000000000000000
FLOW_STEP_VALIDATION amountE18.lo = 2000000000000000000
FLOW_STEP_TRANSFER   amountE18.lo = 1800000000000000000
FLOW_STEP_SETTLEMENT amountE18.lo = 1800000000000000000
```
Страница `/flow/flow_4xW7RUSVcPK`: `Principal Amount 2 tXRP … Network Fee None Credited Amount 1.8 tXRP`.
Конфиг сети (HTML): `code:"ripple-testnet" … zippedAssetId:14, isNativeAsset:true, networkFee:"0.2"`.

То же у Solana: `flow_SMQSpzMh1NM` — 0.01 → 0.009 tSOL, `Network Fee None`, в конфиге `networkFee:"0.001"`.

**Ожидалось:** в операции указана удержанная комиссия (0.2 tXRP = 10% депозита), сумма сходится.

**Почему ошибка:** пользователь видит «комиссии нет», но получает меньше.
Удержание при этом ровно равно `networkFee` из конфига. API не заполняет `requestFee`
(поле есть в схеме `FlowSummaryView.request_fee = 28`), а сайт показывает «None».
Скрипт находит 1 такой среди 10 последних завершённых депозитов (16:20 UTC).

---

## 4. Главная: «Total Txns / TPS / TVL (Polyester Exchange)» — числа зашиты в код

**Запрос:** `GET https://testnet.polyesterscan.com/_app/immutable/nodes/7.BTfMU3in.js` (код главной).

**Сырой ответ (фрагменты):**
```
m={txs:11124982,tps:123922};
… label:`TVL (Polyester Exchange)` … K(n,{value:0,minDecimals:2,prefix:`$`, … Oe(e,{percentage:0,decimals:2,…
… label:`Total Txns (Polyester Exchange)` … get value(){return m.txs} … get value(){return m.tps}
```
Что видит пользователь (текст страницы в браузере, 15:56 UTC):
`TVL (Polyester Exchange) $0.00 0.00% (24h)` · `Total Txns (Polyester Exchange) 11,124,982 123,922 (TPS)`.

**Ожидалось:** живые данные из API (или скрытые карточки, пока данных нет).

**Почему ошибка:** это заглушки: они не меняются, TVL всегда $0, а «123 922 TPS» неправдоподобно
(в сети Polyester ~9 000 tx в сутки по `/api/v2/stats/charts/transactions`).

---

## 5. Главная: «Total Txs» и `total_blocks` обновляются с задержкой в полчаса и больше

**Запрос:** `GET https://scan.polyester.live/api/v2/stats` несколько раз.

**Сырые ответы:**
```
15:47 UTC  "total_blocks":"2954916", "total_transactions":"86312", "transactions_today":"9050"
15:56 UTC  "total_blocks":"2954916", "total_transactions":"86312"
16:13 UTC  "total_blocks":"2954916", "total_transactions":"86312"
16:17 UTC  "total_blocks":"2966931"                                  <- обновилось
16:19 UTC  "total_blocks":"2966931", "total_transactions":"87087"
```
В 16:13 последний блок (`/api/v2/main-page/blocks`) был 2966744, а `/api/stats/counters` сайта
показывал `totalBlocks 2965334`, `totalTxns 87015`.

**Ожидалось:** счётчики растут вместе с сетью (≈6 tx/мин, ≈2 блока/сек) или хотя бы раз в несколько минут.

**Почему ошибка:** с 15:47 до 16:13 (26+ минут) значения не менялись. Всё это время карточка «Total Txs»
на главной показывала 86,312, а `total_blocks` отставал от высоты сети на ~12 000 блоков.
Потом счётчики обновились разом. Похоже на редкое обновление кэша счётчиков Blockscout
(**не проверено**, как часто). Карточка «Total Blocks» не страдает: она берёт высоту последнего блока.
Скрипт ловит это, только если застанет отставание > 1000 блоков.

---

## 6. Панель «API» у операции ведёт в API сети devnet

**Где:** страница операции → блок с сырыми данными «Lifecycle flow detail».

**Запрос:** бандлы `nodes/30.OrT0EK6-.js` и `nodes/31.yBWar82L.js`.
**Сырой ответ:** `endpoint: https://api-devnet.polyester.ai/v1/chain/flows/${flowId}`

Проверка: `GET https://api-devnet.polyester.ai/v1/chain/flows/flow_SMQSpzMh1NM` (тестнет-операция) →
```
HTTP 404 {"detail":"lifecycle flow not found","code":"not_found",…}
```

**Ожидалось:** адрес API тестнета (сайт — `testnet`, его API — `api.testnet.polyester.com`).

**Почему ошибка:** адрес захардкожен на devnet и другой домен (`polyester.ai`). Показанная
пользователю ссылка на «API» для тестнет-операции отдаёт 404.

---

## 7. Blockscout API: 500 на больших числах и нечисловом `items_count`

**Запросы → сырые ответы:**
```
GET https://scan.polyester.live/api/v2/blocks/99999999999999999999                       -> HTTP 500 "Internal server error"
GET https://scan.polyester.live/api/v2/blocks/9223372036854775808                        -> HTTP 500 "Internal server error"
GET https://scan.polyester.live/api/v2/blocks?type=block&block_number=100000000000000000000&items_count=50 -> HTTP 500 "Internal server error"
GET https://scan.polyester.live/api/v2/blocks?type=block&block_number=2966004&items_count=abc            -> HTTP 500 "Internal server error"
```
Для сравнения: `/api/v2/blocks/-1` → 404, `/api/v2/transactions/0x1234` → 422 `{"message":"Invalid parameter(s)"}`.

**Ожидалось:** 404/422 как на другие кривые значения.
**Почему ошибка:** необработанное переполнение/разбор числа — ошибка сервера вместо ответа
«неверный параметр». Мелко; скорее всего поведение самого Blockscout (не проверено).

---

## 8. `total_gas_used: "0"`, хотя за сегодня газ есть

**Запрос:** `GET https://scan.polyester.live/api/v2/stats`
**Сырой ответ:** `"gas_used_today":"1751274555", … "total_gas_used":"0"` (15:47, 16:07, 16:13 UTC).
**Ожидалось:** всего потрачено газа ≥ потрачено сегодня.
**Почему ошибка:** значение явно не считается. На сайте это поле не выводится (поиск по бандлам) — мелочь.

---

## 9. `<html lang="%lang%">` на всех страницах

**Запрос:** `GET https://testnet.polyesterscan.com/` (и `/tx/…`, `/block/…`, `/address/…`, страница 404).
**Сырой ответ:** `<!doctype html><html lang="%lang%" class="dark">`
**Ожидалось:** `lang="en"`. **Почему ошибка:** незаменённая заглушка шаблона SvelteKit.
Мешает экранным читалкам и переводчику браузера. Мелочь.

---

## 10. Кривой адрес страницы отдаёт 200 вместо 404

**Запрос:** `GET https://testnet.polyesterscan.com/tx/0xnothex` → `HTTP 200` (≈200 КБ HTML);
для сравнения `/this-page-does-not-exist` → `HTTP 404`.
Так же `/block/-5`, `/address/0xZZ` → 200. Мелочь («мягкая 404»).

---

# Наблюдения — не подтверждены или не воспроизводятся сейчас

- **Счётчики противоречили друг другу** (15:48–15:58 UTC): `/api/stats/counters` →
  `"completedTxns":"86579"` при `"totalTxns":"86262"` (успешных больше, чем всех).
  В 16:07 уже `totalTxns 87015` — сейчас не воспроизводится. Видимо, счётчики обновляются в разное время.
- **Поиск строкой 5000 символов:** в 15:48 `GET /api/v2/search?q=a…(5000)` → `HTTP 500`, пустое тело;
  в 16:05 тот же запрос → `HTTP 414`. Не воспроизводится.
- **Запасная таблица обозревателей** в `chunks/CKgKAkPt.js`: в колонке «testnet» у Tron
  `https://tronscan.org/…`, XRP `xrpscan.com`, Dogecoin `dogechain.info` (основные сети),
  у Polygon `mumbai.polygonscan.com` (сеть закрыта). Сейчас не срабатывает: у всех сетей есть
  `explorerUrl`. Выводится только по коду — **не проверено** на странице.
- **Название «Solana Testnet (tSOL)»** на странице операции (`Token: Solana Testnet (tSOL)`),
  хотя сеть — `Solana Devnet`. У Solana есть и отдельная сеть «testnet», так что название может
  запутать. Мелочь, на усмотрение.
- **Из облачных IP страница «Flows» не грузится:** в headless Chromium `ListFlows` блокируется
  Cloudflare на предварительном запросе (CORS preflight → 403), сайт пишет «Could not load flows».
  Вебсокеты: `wss://api.testnet.polyester.com/` → 403, `wss://scan.polyester.live/socket/v2/…` → 426,
  на главной красные «Error» у «Latest Blocks/Transactions». Может быть связано с прокси этой среды —
  **проверить с домашнего ПК**, прежде чем считать ошибкой.

# Что проверено и в порядке

- Поиск: пустой, кривой хэш, адрес Bitcoin/Solana (чужие сети), 1000/3000 символов — 200 и пусто, без 500.
- `/api/v2/transactions/0x1234` → 422, нулевой хэш → 404, `/api/v2/addresses/0xZZ` → 422.
- Листание Blockscout: блоки и транзакции стр.1→2 — без дублей и пропусков, порядок строго убывает;
  `items_count=0/-1/10^12`, `block_number=-1/0/abc` — без ошибок сервера.
- Листание flows (`ListFlows`): стр.1→2 без дублей; `limit=0` → 100 по умолчанию, `1` → 1, `500` → 500;
  `501`, `-1`, `2^32`, мусорный `pageToken` → 400. `GetFlowById` кривой → 400, несуществующий → 404.
- Время: блок в Blockscout = блок в RPC до секунды, UTC, не 1970; flows — миллисекунды;
  `GetSpotConfig.tsSec` — секунды; `lastTradeTsNs` — наносекунды.
- Суммы: `value` и комиссия tx совпадают с RPC; `supply` 31 актива из конфига сайта совпадает с
  `total_supply` токенов в сети (разница только в отбрасывании знаков после `quantityScale`) —
  **ошибок ×1000 нет**. Первое расхождение (tTRX ровно на 1000) было из-за 15 минут между запросами
  и при одновременных запросах исчезло.
- Ссылки на транзакции/адреса сохраняют тестовую сеть: во всех 16 сетях — по логике сайта, применённой
  к живому конфигу; на живых страницах операций — Solana (`?cluster=devnet`), Bitcoin, Litecoin.
