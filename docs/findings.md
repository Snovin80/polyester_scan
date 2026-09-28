# Находки: Polyester Scan testnet

Проверено 28.09.2026, 15:40–18:00 UTC, живыми запросами из облачной среды (+ скрины автора с домашнего ПК).
Повторить: `python3 scan_probe.py` (сайт, Blockscout, API операций) и `python3 flow_audit.py collect` + `check`
(сверка операций); п. 5 ловится, только если застать отставание счётчика; п. 16–18 проверены браузером и API
(запросы — в тексте находок).

**Главное по важности** (номера — порядок, в котором находили):

| Важность | Находка |
|---|---|
| высокая | 3 — комиссия удержана, а показано «None»; у выводов «Settled 100» при полученных 99.6 |
| высокая | 12 — у трети операций потеряны шаги; депозит «висит» 5 суток, хотя прошёл за 10 с |
| высокая | 14 — у выводов нет ссылки на транзакцию доставки |
| средняя | 1 — битая ссылка на транзакцию Solana (нижний регистр) |
| средняя | 2 — ссылки «сеть/нативный токен» BTC/SOL/LTC ведут в основную сеть |
| средняя | 17 — CSV токенов и операций сломаны · 16 — внутренние транзакции не отслеживаются |
| средняя | 4 — заглушки на главной · 5 — счётчики отстают на 30+ мин |
| низкая | 7, 8, 9, 10, 11, 13, 15, 18 — мелочи; 6 — понижена (только код) |

Документация: живые `testnet.polyester.com/docs/...` из облака закрыты Cloudflare, поэтому
цитаты — из сохранённой автором копии от 10.09 (`docs/snapshot_2026-09-10/`, тогда доки были на
`testing.polyester.com`). Перед отправкой команде сверить формулировки с текущими доками.

Уже отправлено команде (по `docs/bot/CLAUDE_bot.md` и журналу): про обозреватель — ничего.
Родственное: адрес альфы `api-devnet.polyester.ai` в доках SDK (25.09) — см. п. 6 (понижен);
`tsSec` в миллисекундах в MCP (28.09) — см. раздел «Дополнения к отправленному».

Ниже находки по номерам (важность — в таблице выше).

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


**XRP — не затронут** (проверено автором 28.09 ~18:03 UTC): обе ссылки на `testnet.xrpl.org` (заглавными и строчными)
открыли транзакцию «Payment · Success · 2.00 XRP» — обозреватель XRP сам понимает хэш в любом регистре.
Поиск на сайте по подписи Solana и по `flow_SMQSpzMh1NM` находит операцию «0.01 tSOL Deposit» (скрины автора).
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


**И на выводах** (28.09 ~18:00 UTC, HTML страниц, по одному выводу на сеть): ссылка «сеть назначения» ведёт на главную
основной сети — `flow_Jhj4Cp6a5ka` (BTC) → `https://mempool.space`, `flow_7uxDcJAdSxB` (SOL) → `https://solscan.io`,
`flow_cjFdKZYSooo` (LTC) → `https://litecoinspace.org`. У остальных 9 сетей с операциями (Sepolia, Base, Arbitrum, BSC, XRP,
Fuji, Robinhood, Tron) ссылки ведут в тестовые сети. На странице самой сети (`/supported-chain/{id}`, вкладка Info) ссылка верная.

---

## 3. Комиссия удержана, а API и обозреватель пишут «Network Fee: None» — депозиты XRP/SOL и 30% выводов во всех сетях

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


**Выводы — то же, и хуже: показана неверная полученная сумма** (снимок 28.09 ~17:15 UTC, 200 завершённых выводов):
```
без requestFee в API: 61 из 200 — ethereum-sepolia 34/119, ripple 5/12, bsc 4/13, robinhood 4/13, base 4/13,
                      solana 4/4, avalanche-fuji 3/8, arbitrum 2/12, litecoin 1/3 (bitcoin 0/3)
```
По одному выводу из каждой сети — сожжённая сумма в блокчейне (`ZTokenBurned` в tx шага BRIDGE_FULFILLMENT)
меньше суммы вывода ровно на `networkFee` конфига, а API пишет fee нет и «к отправке» = полная сумма:
```
flow_WmsSrDpe1Ng USDC sepolia : API gross 100,   net 100    | сожжено 99.6    | удержано 0.4
flow_A1dVQD4FPHh tXRP         : API gross 2,     net 2      | сожжено 1.8     | удержано 0.2
flow_7uxDcJAdSxB tSOL         : API gross 0.01,  net 0.01   | сожжено 0.009   | удержано 0.001
flow_FNYMrF8Y4rY tAVAX        : API gross 0.008, net 0.008  | сожжено 0.004   | удержано 0.004
flow_3RJLC8VuPY8 arbitrum     : 0.1 -> 0.09998 · flow_Tc1EyCTyQMe base: 0.002 -> 0.00195 · flow_5PtUV3SHtR7 bsc: 0.0005 -> 0.00049
flow_CJqzMivpmnT robinhood    : 0.0003 -> 0.00028 · flow_iNUSfgD4TVk litecoin: 0.002 -> 0.0019
```
Реальная доставка `flow_WmsSrDpe1Ng`: Sepolia tx `0xc9473e80157a0b0065d0375d87fe4defb88255a8d00e4a927ed5620e286cf705`
(хэш из `commitWithdrawTxHash` в сети Polyester), status 1, ERC-20 Transfer **99.6** USDC на
`0x5a8a788e2efdef6898764a978df3bedcf8425c7a` (= destinationAddress в API).
Страница `/flow/flow_WmsSrDpe1Ng`: «100 USDC Withdraw · Network Fee None · **Settled Amount 100 USDC**» — пользователь
видит 100, получил 99.6.
Для сравнения, вывод с комиссией `flow_czSz3FJSxo8`: страница «Network Fee 0.004 tAVAX · Settled Amount 0.004 tAVAX»,
в Avalanche Fuji tx `0xf516fc83…2f25` — 0.004 AVAX на тот же адрес. Верно.
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

На большом снимке (`flow_audit.py`, 28.09 17:14 UTC, 300 последних завершённых депозитов): **86 из 300 (29%)** с потерянными
шагами в 11 сетях — ethereum-sepolia 52, bsc 7, ripple 7, robinhood 5, base 4, avalanche-fuji 3, litecoin 3, bitcoin 2, arbitrum 1, solana 1, tron 1.

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


*Видимое последствие — «депозиты ниже минимума».* Все 6 депозитов в снимке, у которых сумма меньше минимума
(`flow_D4HPuApD2Sk` 0.009 SOL при минимуме 0.01, `flow_7AUkiS98hSn` 1.8 XRP при 2, `flow_QrMqppQ9Ctc` 0.00028 ETH при 0.0003…),
— операции «только SETTLEMENT», и у всех «сумма + комиссия» = ровно минимум. То есть пришла нормальная сумма, а обозреватель
показывает уже зачисленную и она выглядит как депозит ниже минимума (по докам такие «will be lost»).

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

## 14. У выводов нет ссылки на транзакцию доставки — обозреватель её не отслеживает

**Где:** страница вывода и API операций.

**Сырые данные** (снимок 28.09 ~17:15 UTC, 200 завершённых выводов, `GetFlowById`):
```
источники записей во всех шагах и событиях выводов: SOURCE_POLYESTER_CHAIN 1781, SOURCE_LEDGER 290, SOURCE_RELAYER 0
для сравнения депозиты:                             SOURCE_RELAYER 282 (наблюдение внешней сети), POLYESTER_CHAIN 708, LEDGER 300
```
Пример `flow_WmsSrDpe1Ng` (100 USDC → Sepolia): в ответе API нет хэша доставки `0xc9473e80…f705`, хотя он записан в сети
Polyester (`commitWithdrawTxHash` / событие `WithdrawTxHashCommitted {requestId: 9601, destinationHashTx: 0xc9473e80…}`),
а в Sepolia эта tx есть (status 1, 99.6 USDC на адрес получателя). На страницах выводов всех 9 сетей с операциями —
0 ссылок на транзакции во внешней сети (только адрес и сеть); у депозитов ссылка на исходную tx есть.

**Документация** (Asset Flows): «The Journey shows how the movement progressed… it can include: source-chain confirmations;
Zipper validator approval; a Zipped Asset mint or burn; a Funding or Trading balance update; and destination-chain delivery»;
«Transaction links take you to the public record for that stage. External-chain links open the relevant network explorer».

**Почему ошибка:** пользователь не может открыть транзакцию, которой получил деньги, и проверить доставку; вывод
помечается «Completed» по событию в сети Polyester, а не по факту в сети назначения.

---

## 15. (мелочь) Поиск операции по хэшу: EVM без учёта регистра, BTC и XRP — с учётом

**Запросы** `ListFlowsByTx {"txHash": …, "lookupKind": "TX_LOOKUP_KIND_ANY"}` (28.09 ~17:55 UTC):
```
0xfb353d95…6deb (EVM, строчные)  -> flow_ab1QeSbCqcE      0xFB353D95…6DEB (заглавные) -> flow_ab1QeSbCqcE
fbad40756ea8… (BTC, как в сети)  -> flow_frT2okTWCsw      FBAD40756EA8… (заглавные)   -> []
D0B960EF4BC2… (XRP, как в сети)  -> flow_4xW7RUSVcPK      d0b960ef4bc2… (строчные)    -> []
45bQAAfmzUhj… (Solana)           -> flow_SMQSpzMh1NM      45bqaafmzuhj… (строчные)    -> []  (верно: base58)
```
**Почему ошибка:** хэши BTC и XRP шестнадцатеричные, регистр в них не значим; для EVM API это учитывает, для BTC/XRP — нет.
Хэш XRP в нижнем регистре сайт сам выдаёт в ссылке шага (п. 1). Сайт при поиске регистр не меняет (проверено в браузере). Мелочь.

---

## 16. Внутренние транзакции не отслеживаются: «No internal transactions», хотя они есть

**Сырые данные** (28.09 ~17:55 UTC):
```
GET https://scan.polyester.live/api/v2/internal-transactions                -> {"items":[],"next_page_params":null}  (во всей сети — ни одной)
GET .../api/v2/transactions/{hash}/raw-trace                                  -> 500 "Error while raw trace fetching"
POST https://rpc.polyester.live debug_traceTransaction                        -> {"error":{"code":-32601,"message":"the method debug_traceTransaction does not exist/is not available"}}
```
Пример — tx `0x10c5d7a58a06c72835251cb24f2509b9b60797201ca2763fb3ab2e4ae6477c14` (шаг TRANSFER депозита `flow_j6JnzHHeK68`):
вызван `0xD439270f881b56727EaaB878CE4e80eB08A25BEB` (TransparentUpgradeableProxy, `executeRequests`), а события в ней выпустили
5 контрактов — `0x4b41…0f38` (ZToken), `0x57D1…12D1`, `0x730D…CfAD`, `0xD439…5BEB`, `0xee59…3A75`. Значит, внутренние вызовы были;
Blockscout по этой tx отдаёт 0 внутренних. Страница `/tx/…?tab=internal-txns`: «No internal transactions for this transaction.»

**Ожидалось:** внутренние вызовы видны (вкладка Internal Txns есть на сайте) или честное «трассировка недоступна».
**Почему ошибка:** почти все операции моста идут через прокси — вкладка вводит в заблуждение («нет»), а переводы монеты
сети внутри контрактов не видны вовсе. Причина — у ноды нет методов трассировки (`debug_*`). Вкладка «summary» тоже
отключена: `/summary` → 403 `{"message":"Transaction Interpretation Service is disabled"}`.

---

## 17. Выгрузки CSV сломаны: токены (все колонки — один адрес) и операции (пустой актив)

**Как:** `testnet.polyesterscan.com/tokens` → «Export Data» (браузер, 28.09 ~17:52 UTC), файл `export-Tokens-page-1.csv`:
```
#,Token,Source Chain,Polyester Chain Contract Address,Source Chain Token Address,Type,price,supply
,0x4b412f2a93f55551BF5DcF216EaEAbC84C4C0f38,0x4b412f2a93f55551BF5DcF216EaEAbC84C4C0f38,0x4b412f2a93f55551BF5DcF216EaEAbC84C4C0f38,0x4b412f2a93f55551BF5DcF216EaEAbC84C4C0f38,ERC-20,,
,0x3b1ba6D40Ca7C7a4ad44F6F0d3cE0fFB73D268f8,0x3b1ba6D40Ca7C7a4ad44F6F0d3cE0fFB73D268f8,0x3b1ba6D40Ca7C7a4ad44F6F0d3cE0fFB73D268f8,0x3b1ba6D40Ca7C7a4ad44F6F0d3cE0fFB73D268f8,ERC-20,,
```
Во всех 40 строках: в «Token», «Source Chain», «Polyester Chain Contract Address» и «Source Chain Token Address» один и
тот же адрес контракта в сети Polyester; «#» и «supply» пустые. Тот же токен в API: `tETH`, «Ethereum Testnet»,
`total_supply 103213936215401999216`, на странице — сеть Ethereum Sepolia и адрес в исходной сети.

**Документация** (Contracts & Tools): «Download Page Data is available on many populated tables, including transactions,
blocks, flows, accounts, contracts, tokens… The download includes the current page and active filters».
**Почему ошибка:** выгрузка не содержит ни названия, ни сети, ни выпуска — бесполезна. Выгрузки блоков и транзакций рабочие.


**Операции (Flows)** — выгрузка сделана автором с домашнего ПК (28.09 ~18:03 UTC), файл `export-flows-page-1.csv`
(копия: `docs/evidence_export-flows-page-1.csv`):
```
Type,Account,Asset,Amount,Status,Flow ID,Created (UTC)
Transfer,0xbdc30e542a5c1333f071be7aec342dae8578063c,,1000,settlement,flow_5z1o1Vm7yST,2026-09-28T18:02:59.350Z
Transfer,0xbdc30e542a5c1333f071be7aec342dae8578063c,,14.2,settlement,flow_VKAGfQej5DK,2026-09-28T18:02:59.350Z
Withdraw,0x7db0a74e84b8a245928d691358a9fe8bc3e15eef,,0.0005,settlement,flow_CqhhhDwtkkJ,2026-09-28T18:01:27.000Z
Deposit,0x7db0a74e84b8a245928d691358a9fe8bc3e15eef,,2,settlement,flow_GQfBFybaG5g,2026-09-28T18:01:06.757Z
```
Во всех 25 строках колонка **Asset пустая** — «1000», «14.2», «2» без указания, чего; на странице в той же строке
«1,000 USDT Tether USD», «14.2 LTC Litecoin». В «Status» — внутреннее имя шага `settlement`, а на странице «Completed».
Хэшей транзакций в выгрузке нет (на странице есть Source tx / Completion tx).
---

## 18. (мелочи интерфейса)

- Номер страницы берётся из адреса и не проверяется: `/blocks?page=999999` показывает «Page 999999» и самые свежие блоки
  (данные первой страницы); `/blocks?page=2&next_page_params=not%20json` — «Page 2» и данные первой страницы.
- В CSV транзакций колонка «Age» — число миллисекунд (`1790617900000`), в CSV блоков та же «Age» — дата
  (`2026-09-28T17:51:45.000000Z`); заголовок `transactionHash` в другом стиле, чем остальные.

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

- Счётчик транзакций адреса (`/addresses/{a}/counters`) при первом обращении отдаёт 0 (у `0x01E4…eEC7` — 0 при nonce 10189),
  через несколько секунд — верное число (10190). Штатная ленивая подсчётка Blockscout; для пользователя — «0 транзакций»
  при первом открытии адреса. Мелочь.
- В доках от 10.09 (Deposit & Withdrawal Fees) USDT доступен в 6 сетях (Sepolia, Solana, Base, Arbitrum, BSC, Tron), USDC —
  в 3; в текущем конфиге сайта USDT и USDC — только через Ethereum Sepolia (страница unified-актива: «Networks 1»).
  Сверить с текущими доками — возможно, доки устарели.

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
- Выводы доставлены: `flow_czSz3FJSxo8` — 0.004 AVAX на Fuji, `flow_WmsSrDpe1Ng` — 99.6 USDC на Sepolia, на адреса из API.
- Список (`ListFlows`) = карточка (`GetFlowById`) у всех 500 операций; REST = RPC (6 из 6).
- Зачисления раньше подтверждения нет; голоса валидаторов в сети — 4 из 4 при нужных 3 (п. 12 — только запись).
- Обеспечение: необходимое условие выполнено (выпуск исходных токенов в Sepolia ≥ выпуску в Polyester, 15 маршрутов).
  Полное 1:1 **не проверено** — адреса хранилищ неизвестны (в кошельках выводов 2–4 % выпуска).
- Приватность: показ аккаунта у операций и публичный фильтр `ownerAccountId` описаны в доках (Asset Flows, справочник) —
  так задумано.
- Поиск сайта передаёт хэш как введён (без `toLowerCase`) — ошибки п. 1 в поиске нет.
- Фильтры `ListFlows` (сеть, актив, unified-актив, аккаунт, тип, открытые/завершённые, сортировка) возвращают только
  подходящее; несуществующие значения — пустой список; кривой адрес — понятная 400.
- Глобальный поиск: без учёта регистра, обрезает пробелы, адрес в любом регистре, номер блока → блок, символы `tsol/TSOL/USDT`.
- Счётчики сети сходятся: 28 unified-активов, 16 сетей, 31 маршрут; zSupply tETH 112.77 = сумма 4 маршрутов (112.7787, с
  отбрасыванием знаков); выпуск SOL/USDT на странице = Blockscout; выпуск и decimals 12 токенов = RPC; держатели сходятся.
- Блок по хэшу = по номеру; будущий блок → 404. Выгрузки CSV блоков и транзакций рабочие.
- Страница `/unit-converter` не существует (404) — не ошибка.
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
