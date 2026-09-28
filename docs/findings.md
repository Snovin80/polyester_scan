# Находки: Polyester Scan testnet

Проверено 28.09.2026, 15:40–16:40 UTC, живыми запросами из облачной среды.
Основные находки 1–5, 7–13 повторяет `python3 scan_probe.py` (п. 5 — только если застанет отставание счётчика).

Документация: живые `testnet.polyester.com/docs/...` из облака закрыты Cloudflare, поэтому
цитаты — из сохранённой автором копии от 10.09 (`docs/snapshot_2026-09-10/`, тогда доки были на
`testing.polyester.com`). Перед отправкой команде сверить формулировки с текущими доками.

Уже отправлено команде (по `docs/bot/CLAUDE_bot.md` и журналу): про обозреватель — ничего.
Родственное: адрес альфы `api-devnet.polyester.ai` в доках SDK (25.09) — см. п. 6 (понижен);
`tsSec` в миллисекундах в MCP (28.09) — см. раздел «Дополнения к отправленному».

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

**Документация** (user-docs → Polyester Scan → Asset Flows): «Transaction links take you to the public
record for that stage. External-chain links open the relevant network explorer».

**Почему ошибка:** ссылка ведёт на несуществующую транзакцию. Причина в коде:
`chunks/B-stKme4.js` — `function I(e){return e.trim().toLowerCase()}` применяется к `txRef` шага
перед построением внешней ссылки. Для hex-хэшей EVM это безвредно, для Solana ломает ссылку.
Та же функция переводит в нижний регистр хэши XRP (в API они в верхнем: `D0B960EF…`) —
принимает ли такие `testnet.xrpl.org`, **не проверено**.


**Проверено с домашнего ПК автора (28.09 ~16:55 UTC, Chrome):** ссылка шага «Deposit Seen» открывает Solscan (DEVNET), транзакция не загружается (серые заглушки); ссылка «Source Tx» — транзакция найдена: 0.01 SOL, 11:33:02 UTC, SUCCESS.

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

**Документация** (Asset Flows): «External-chain links open the relevant network explorer… You can also
open the related account, Zipped Asset, Unified Asset, or source chain directly from the Flow»;
(Tokens & Chains): у страницы сети есть «external explorer link».

**Почему ошибка:** ведёт на главную основной сети. Причина: `chunks/Dj4nS8JF.js`,
`function I(e){ return new URL(e).origin }` — от адреса остаётся только домен.

**Что в порядке (важно для отчёта):** ссылки на **транзакции и адреса** Solana содержат
`?cluster=devnet` и работают (`Source Tx`, `Sender Address`, `Deposit Address`). Подозрение
из CLAUDE.md «у Solana основной solscan.io» подтвердилось только для ссылок «сеть/токен».


**Проверено с домашнего ПК автора (28.09 ~16:55 UTC):** ↗ у «Source Chain: Solana Devnet» на `/flow/flow_SMQSpzMh1NM` открывает главную `solscan.io` основной сети (цена SOL, статистика mainnet, переключателя DEVNET нет).

---

## 3. Депозиты XRP и Solana: комиссия удержана, но на обозревателе «Network Fee: None»

Сама комиссия за ввод законная: биржа её объявляет (в окне депозита «Deposit fee 0.00002 BTC»,
в истории депозитов «Fee applied 0.0001 tETH»), размер берётся из `networkFee` в конфиге сети.
Для большинства сетей обозреватель показывает её правильно. Например, депозит tETH из Sepolia
`/flow/flow_W7ZGpHHftaT`: `Principal Amount 0.5 tETH · Network Fee 0.0001 tETH · Credited Amount 0.4999 tETH`,
в API заполнено `requestFee: {amountE18: {lo: "100000000000000"}, status: "REQUEST_FEE_STATUS_SETTLED"}`.

**Ошибка — только у XRP (ripple-testnet) и Solana (solana-devnet):** в большинстве депозитов
API не отдаёт `requestFee`, и обозреватель пишет «None», хотя сумма уменьшилась ровно на комиссию.

**Запрос:** `POST https://api.testnet.polyester.com/chain.lifecycle.v1.LifecycleReadService/GetFlowById`
`{"flowId":"flow_4xW7RUSVcPK"}` (депозит tXRP).

**Сырой ответ (сокращено):**
```
summary: flowKind=KIND_DEPOSIT, polyesterChainId=9, amountE18={"lo":"2000000000000000000"}, requestFee=<нет поля>
FLOW_STEP_SOURCE     amountE18.lo = 2000000000000000000
FLOW_STEP_VALIDATION amountE18.lo = 2000000000000000000
FLOW_STEP_TRANSFER   amountE18.lo = 1800000000000000000
FLOW_STEP_SETTLEMENT amountE18.lo = 1800000000000000000
```
Страница `/flow/flow_4xW7RUSVcPK`: `Principal Amount 2 tXRP … Network Fee None Credited Amount 1.8 tXRP`.
Конфиг: `code:"ripple-testnet" … zippedAssetId:14, isNativeAsset:true, networkFee:"0.2"`.
Solana: `/flow/flow_SMQSpzMh1NM` — 0.01 → 0.009 tSOL, `Network Fee None`, в конфиге `networkFee:"0.001"`.

Обратная проверка через REST из справочника (28.09 16:36 UTC, `Content-Type: application/json`):
```
GET https://api.testnet.polyester.com/v1/chain/flows/flow_4xW7RUSVcPK -> 200, summary.amountE18={"lo":"2000000000000000000"}, requestFee: <нет поля>
GET https://api.testnet.polyester.com/v1/chain/flows/flow_W7ZGpHHftaT -> 200, summary.requestFee={"amountE18":{"lo":"100000000000000"},"assetIds":{"unifiedAssetId":28,"zippedAssetId":2},"recipientAddress":"0x4990534d6bfe03c17caad010931b467cd5fbec3f","status":"SETTLED"}
```

**Документация:**
- Deposit & Withdrawal Fees: «A deposit fee is deducted from the amount credited»; в таблице
  «XRP Ripple Testnet 0.2 XRP», «SOL Solana Devnet 0.001 SOL» — удержание законное и совпадает.
- Asset Flows: «The Summary… includes the asset, principal amount, fee, final amount…».
- Справочник `GET /v1/chain/flows/{flow_id}`: «amountE18 — Gross principal amount for the flow…
  Request fees are exposed separately in request_fee»; «requestFee — Request-scoped fee details
  when a fee applies and should be visible for the current step».

**Масштаб** (все завершённые депозиты сети через `ListFlows` + `GetFlowById`, 28.09 ~16:40 UTC):

| Сеть | Без `requestFee` | С `requestFee` |
|---|---|---|
| ripple-testnet (XRP) | 32 из 50 | 18 |
| solana-devnet (SOL) | 28 из 32 | 4 |
| остальные 9 сетей, попавшие в последние 300 депозитов (ETH и токены на Sepolia, BTC, LTC, BSC, AVAX, Base, Arbitrum, Robinhood, Tron) | 0 | все 288 |

Бывает вперемешку даже в одной сети: tXRP `flow_L58gDDcfYLi` (10:01) — комиссия 0.2 указана,
`flow_Hn4y1vxZXYo` (11:40) — нет, при одинаковом удержании 2 → 1.8.

**Ожидалось:** у каждого депозита с удержанием указана комиссия, как у tETH:
«Principal − Network Fee = Credited».

**Почему ошибка:** на странице XRP/SOL-депозита не сходится арифметика: пришло 2, комиссии нет, зачислено 1.8.
Пользователь не видит, куда ушли 10% (у XRP комиссия 0.2 при минимальном депозите 2).
Похоже, при обработке этих сетей не всегда записывается `requestFee` (**не проверено**, на какой стороне ошибка).
Показывает ли биржа «Fee applied» для таких депозитов в истории — **не проверено** (нужен вход в аккаунт).

**Попутно, не разбирал:** в части депозитов XRP/SOL сумма на первом шаге уже «чистая»
(`1.8 → 1.8`, `0.009 → 0.009`), иногда при этом `requestFee` = 0.2 указан (`flow_cVCVUjgoM8a`).


**Проверено с домашнего ПК автора (28.09 ~16:55 UTC):** страница депозита tXRP — «2 tXRP Deposit», «Network Fee None», «Credited Amount 1.8 tXRP».


**Комиссия есть в блокчейне — теряет её только API** (28.09 ~17:40 UTC, Blockscout, логи tx шага REQUEST):
```
flow_4xW7RUSVcPK (tXRP, в API requestFee нет): tx 0x5ca047996bfcaf2331456361210fe45f55015b18aa6e98601448806c3799955f
  DepositFeeLocked {requestId: 9584, chainId: 9, feeZAmount: 200000000000000000, feeRecipient: 0x4990534d6BFE03c17CaaD010931b467Cd5FBEC3F}
flow_SMQSpzMh1NM (tSOL, в API requestFee нет): DepositFeeLocked feeZAmount = 0.001 SOL; в tx чеканки: 0.001 -> 0x4990…, 0.009 -> пользователю
```
Для сравнения: у 18 депозитов из 10 других сетей `requestFee` в API = `DepositFeeLocked` в блокчейне = чеканка получателю комиссий.

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

**Документация** (Polyester Scan → Overview): «The home page also shows live activity and network summaries».

**Ожидалось:** живые данные из API (или скрытые карточки, пока данных нет).

**Почему ошибка:** это заглушки: они не меняются, TVL всегда $0, а «123 922 TPS» неправдоподобно
(в сети Polyester ~9 000 tx в сутки по `/api/v2/stats/charts/transactions`).


**Проверено с домашнего ПК автора (28.09 ~16:46 UTC):** на главной «TVL $0.00 0.00% (24h)», «11,124,982 · 123,922 (TPS)».

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
16:46 UTC  "total_blocks":"2966931", "total_transactions":"87087"   <- снова 27 минут без изменений;
           последний блок в это время 2970015 (2026-09-28T16:46:45Z)
```
Скриншот главной с домашнего ПК автора (~16:46 UTC): «Total Blocks 2,969,972 · Total Txs 87,087» —
блоки идут («just now»), а число транзакций то же, что в 16:19.
В 16:13 последний блок (`/api/v2/main-page/blocks`) был 2966744, а `/api/stats/counters` сайта
показывал `totalBlocks 2965334`, `totalTxns 87015`.

**Ожидалось:** счётчики растут вместе с сетью (≈6 tx/мин, ≈2 блока/сек) или хотя бы раз в несколько минут.

**Почему ошибка:** с 15:47 до 16:13 (26+ минут) и с 16:19 до 16:46 (27 минут) значения не менялись. Всё это время карточка «Total Txs»
на главной показывала 86,312, а `total_blocks` отставал от высоты сети на ~12 000 блоков.
Потом счётчики обновились разом. Похоже на редкое обновление кэша счётчиков Blockscout
(**не проверено**, как часто). Карточка «Total Blocks» не страдает: она берёт высоту последнего блока.
Скрипт ловит это, только если застанет отставание > 1000 блоков.

---

## 6. (ПОНИЖЕНО 28.09 16:55) Адрес альфы devnet зашит для кнопки «API», но кнопки на сайте нет

**Что в коде:** бандлы `nodes/30.OrT0EK6-.js` и `nodes/31.yBWar82L.js` — для страницы шага расчёта
готовится `endpoint: https://api-devnet.polyester.ai/v1/chain/flows/${flowId}`. Этот адрес devnet
тестнет-операцию не знает: `GET https://api-devnet.polyester.ai/v1/chain/flows/flow_SMQSpzMh1NM` →
`404 {"detail":"lifecycle flow not found","code":"not_found",…}`. Правильный адрес есть:
`GET https://api.testnet.polyester.com/v1/chain/flows/flow_4xW7RUSVcPK` → `200 application/json` (16:36 UTC).

**Почему понижено:** компонент кнопки «API» в этой сборке пустой (`chunks/DWDKMQYN.js`:
`function Hn(t,n){…c(()=>Ee.currentNetworkConfig.apiBase);var r=e(),i=g(r);u(i,e=>{}),m(t,r),b()}` —
ничего не рисует). В браузере на `/tx/207834882979839228429806718939153843491?flow=flow_SMQSpzMh1NM`
(страница шага расчёта) кнопки «API» нет — только вкладка «Overview». Пользователь неверный адрес
сейчас не видит. Проверено только в коде — поэтому не ошибка, а наблюдение.

**Что всё же можно сказать:** доки (Contracts & Tools) описывают «The API button on a supported page
shows the exact read URL used by the current environment» — кнопки на страницах нет; а если её
включат как есть, для расчётов покажет адрес альфы (родственно тикету 25.09 про адрес альфы в доках SDK).
Слабый пункт; в отчёт — разве что одной строкой как дополнение к тикету 25.09.

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


**Проверено с домашнего ПК автора (28.09 ~16:55 UTC):** `scan.polyester.live/api/v2/blocks/99999999999999999999` в браузере → `"Internal server error"`.

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

## 11. Отладочная страница разработчиков открыта всем

**Запрос:** `GET https://testnet.polyesterscan.com/dev/sentry-test-client` (28.09 16:42 UTC)
**Сырой ответ:** `HTTP/2 200`, `content-type: text/html`, `<title>Client Sentry Test</title>`, текст страницы:
`Development Client Sentry Test Trigger a browser-side exception for validating Sentry client capture and source maps. Throw client exception`
Для сравнения соседняя `/dev/og-images` → 404 (закрыта).

**Ожидалось:** 404, как у `/dev/og-images`; служебные страницы не выкладывают на публичный сайт.
**Почему ошибка:** любой посетитель может слать тестовые исключения в их Sentry (шум в мониторинге,
расход квоты). Кнопку не нажимал. Мелочь, но показательная.


**Проверено с домашнего ПК автора (28.09 ~16:55 UTC):** страница открывается («Development · Client Sentry Test»), кнопку не нажимали.

---

## 12. У трети депозитов потеряны шаги операции, хотя в блокчейне они есть

**Где:** API операций (`GetFlowById`, `observedSteps`) и страница операции — шаги без хэша
(на скрине автора у депозита tXRP шаг «4 Minted and Transferred» без ссылки).

**Масштаб** (28.09 ~17:05 UTC, последние завершённые депозиты, `GetFlowById` по каждому):
```
XRP 22 из 50 · SOL 4 из 32 · Sepolia 8 из 20 · BTC 4 из 10 · BSC 4 из 10  — всего 42 из 122
нет шага TRANSFER (чеканка)                          — 17
нет REQUEST, VALIDATION, TRANSFER                    — 11
есть только SETTLEMENT (нет SOURCE…TRANSFER)         — 14
```
`progressTimeline` при этом у всех 300 последних депозитов полный (5 шагов) — теряются именно наблюдённые шаги.

**Пример 1 — шаг есть в блокчейне, а в API нет.**
`GetFlowById {"flowId":"flow_ab1QeSbCqcE"}` → депозит 0.05 из Sepolia (chain 2), `sourceTxHash 0xfb353d95…6deb`,
`startedAt 16:39:35 UTC`, `observedSteps`: только `FLOW_STEP_SOURCE`, `FLOW_STEP_SETTLEMENT`.
В сети Polyester запрос на этот депозит есть: Blockscout, контракт приёма депозитов `0x5BCd…9AE2`,
tx `0x338bbc1e0daf8621638aa4fa4371f8e469417568d0cc6a5a14467bde9b546751` (2026-09-28T16:39:48Z),
`reqDepositZTokens`, в запросе chainId `2`, сумма `50000000000000000`, txHash = `0xfb353d95…6deb`.

**Пример 2 — только последний шаг.** `flow_7MKXJSBiZNM` (26.09 21:56 UTC): в `observedSteps` один шаг
`FLOW_STEP_SETTLEMENT 4.999`; «сумма депозита» показана уже за вычетом комиссии. Исходная транзакция
`SxFAycz7…Q6K` в Solana devnet существует: `finalized`, slot 504555022. Соседний депозит `flow_VsydZL4efQm`
(5 SOL, 9 с спустя) — без шага TRANSFER.

**Ожидалось:** все стадии, которые произошли, есть в операции — доки (Asset Flows): «A Flow… can link an external
transaction, one or more Polyester Chain transactions, validator activity, and a private ledger settlement into one
understandable record»; «Transaction links take you to the public record for that stage».

**Почему ошибка:** у трети операций журнал неполный навсегда (есть примеры 2-дневной давности): нет ссылок
на чеканку/проверку, а у операций «только SETTLEMENT» сумма депозита и комиссия показаны неверно
(principal = уже зачисленная сумма). С пропажей комиссии (п. 3) не связано: у SOL 24 полных операции тоже без `requestFee`.


**Дополнительно (28.09 ~17:30–17:45 UTC):**

*Крайний случай — операция «висит» 4,7 суток, хотя в блокчейне прошла за 10 секунд.* `flow_6DSDcV3jmMw`
(0.002 ETH из Sepolia, единственная открытая операция в API): `currentStep FLOW_STEP_SOURCE`, `isOpen true`,
`lifecycleReason/zipperReason` пустые, `startedAt 2026-09-24 00:21:52 UTC`. В Sepolia tx `0x8c3d3af9…f7a0` — блок 11768401
(00:22:00 UTC), 0.002 ETH на адрес депозита. В сети Polyester: tx `0x1f7e991e…4ae5` (00:22:07, success) —
`RequestDepositCreated requestId 6099`, `DepositFeeLocked 0.0001`; tx `0x1b1125c2…` (00:22:10) — чеканка 0.0001 получателю
комиссий и 0.0019 → перевод на `0x57D15F…` (Polyester Funding). Обозреватель показывает «ожидает» уже почти 5 суток.

*Голоса валидаторов теряются так же.* У 25 обрезанных депозитов в шаге VALIDATION `approveCount` меньше `requiredApprovals`
(например `flow_4xW7RUSVcPK`: 1 из 3). В блокчейне по запросу 9584 — 4 одобрения от 4 разных отправителей
(`validateRequestsBySig`, 16:09:51–16:09:52 UTC, tx `0x25a9f823…`, `0x96da723f…`, `0xfe3447a9…`, `0x5531c34c…`).
То есть мост проверил правильно, API записал только первый голос. Угрозы безопасности нет — это потеря данных.

*«0 подтверждений» — тоже только запись.* У 29 обрезанных депозитов в шаге SOURCE `currentConfirmations 0` при нужном 1.
Проверка на примере `flow_ab1QeSbCqcE`: исходная tx попала в блок Sepolia 11801768 в 16:39:36 UTC, запрос в Polyester —
16:39:48 UTC, т.е. после подтверждения. Зачисления раньше подтверждения нет.

---

## 13. (мелочь) Статистика: «сервис недоступен» вместо «неверный параметр», нет ограничения диапазона

**Запросы → сырые ответы** (28.09 ~17:25 UTC, прокси статистики сайта):
```
GET /api/stats/lines/newTxns?from=2026-09-20&to=2026-09-27&resolution=HOURX -> 400 {"error":"Stats service temporarily unavailable"}
GET /api/stats/lines/noSuchChart?from=2026-09-20&to=2026-09-27&resolution=DAY -> 404 {"error":"Stats service temporarily unavailable"}
GET /api/stats/lines/newTxns?from=1900-01-01&to=2999-12-31&resolution=DAY   -> 200, 2 638 885 байт (точки с 1900-01-01, значения 0)
```
**Ожидалось:** сообщение о неверном параметре; разумный предел диапазона.
**Почему ошибка:** текст вводит в заблуждение (сервис работает), а один запрос без предела отдаёт 2,6 МБ.
Запрос с большим диапазоном сделан один раз, не повторял. Мелочь.

---

# Дополнения к отправленному

## tsSec в миллисекундах — и на обозревателе тоже

28.09 команде уже отправлено: в MCP `get_spot_markets` поле `tsSec` в миллисекундах, а в REST — в секундах.
То же значение в миллисекундах сервер обозревателя встраивает в HTML каждой страницы (конфиг рынков):
```
28.09 16:36:53 UTC  GET https://testnet.polyesterscan.com/  -> ...],tsSec:1790613412000}
28.09 16:36:54 UTC  POST https://api.testnet.polyester.com/marketdata.v1.MarketDataService/GetSpotConfig {}
                    -> application/json, "tsSec": 1790613414
```
Видимо, один источник у MCP и обозревателя. Видимых последствий на страницах не нашёл, поэтому
только как дополнение к уже отправленному, не отдельная находка. (В копии доков от 10.09 то же: `tsSec:1789038188000`.)

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
- ~~Страница «Flows» не грузится~~ — **не ошибка**: у автора дома (28.09 ~17:00 UTC) таблица операций есть,
  «Showing the Latest 25 Flows». Из облака мешал Cloudflare (CORS preflight → 403).
- ~~Вебсокеты и красные «Error» на главной~~ — **не ошибка**: с домашнего ПК автора (28.09 ~16:46 UTC)
  блоки и транзакции обновляются вживую, «Error» нет. Из облака мешала среда (прокси).

# Что проверено и в порядке

Сверка трёх источников (28.09 ~17:15–17:45 UTC, снимок 300 депозитов + 200 выводов + 100 переводов, `flow_audit.py collect`):
- **Сумма депозита = сумма в исходной сети** — 6 сетей из 6: BTC (mempool, vout), Sepolia (RPC, value), Solana devnet
  (getTransaction, лампорты), LTC (litecoinspace), XRP (testnet.xrpl-labs.com, 2 000 000 drops), Tron Nile (trongrid, sun).
- **Начеканено = сумма − комиссия, комиссия = `DepositFeeLocked` = чеканка получателю** — 20 депозитов из 11 сетей.
  (Пакетные tx чеканят за несколько депозитов — сверял по конкретной сумме нужного токена.)
- Дублей по исходному хэшу нет (500 операций); Settlement Ref уникальны (500); порядок времени шагов соблюдён.
- Сайт показывает большие суммы (U128 с `hi`) верно: `flow_eZEWrVjnqed` — «1,000 tTRX», комиссия 1.5, зачислено 998.5.
- Отражение ввода безопасно: поиск (страница и окно в шапке), `/flow/…`, `/tx/…` и др. выводят `<b>…</b>` текстом.
- Ссылки «Explorer» на странице сети (`/supported-chain/{id}`, вкладка Info) — тестовые (с `?cluster=devnet`, `/testnet`).
- Исходники (source maps) закрыты (404); `/showroom/*` — «Error 404» на экране (мягкая 404, как п. 10);
  `/external/*` — только картинки логотипов; `check-redirect` на внешний адрес не уводит.
- Статистика на будущие даты не выдумывает точки: заканчивается сегодняшним днём с `is_approximate: true`.


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
