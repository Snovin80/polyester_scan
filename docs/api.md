# Polyester Scan — откуда сайт берёт данные

Разведка 28.09.2026 по JS-бандлам `testnet.polyesterscan.com/_app/immutable/...`
(сборка Sentry release `6d30092c7e02…`, 377 файлов) и живым запросам.

## Коротко

| Что | Адрес | Как устроено |
|---|---|---|
| Сам сайт | `https://testnet.polyesterscan.com` | SvelteKit, часть данных сервер встраивает прямо в HTML |
| Блоки, транзакции, адреса, токены сети Polyester | `https://scan.polyester.live` | **Blockscout** API `/api/v2/...` (JSON, без ключа) |
| Статистика (графики, счётчики) | `https://scan.polyester.live:8080` | Blockscout stats; сайт проксирует через свои `/api/stats/...` |
| Операции ввода/вывода (flows), конфиг сетей, аналитика | `https://api.testnet.polyester.com` | **Connect-RPC** (protobuf; принимает и JSON) |
| Живые обновления | `wss://api.testnet.polyester.com/`, `wss://scan.polyester.live/socket/v2/websocket?vsn=2.0.0` | вебсокеты |
| RPC сети Polyester testnet | `https://rpc.polyester.live` | EVM JSON-RPC, chainId 888169 (`0xd8d69`) |

Где это в бандле:
- `chunks/CfEo7bsQ.js`: `{devnet:"https://scan.polyester.tech", testnet:"https://scan.polyester.live", mainnet:"https://scan.polyester.com"}`,
  `apiBase`, `statsApiBase: apiBase + ":8080"`, `socketUrl: .../socket/v2`, `nativeCurrency: {symbol:"P", decimals:18}`.
- `chunks/BzEt9jPZ.js`: `polyester-testnet`: `apiUrl https://api.testnet.polyester.com`, `rpcUrl https://rpc.polyester.live`, chain id 888169.
- `chunks/B9aJupKk.js`: полный справочник ресурсов Blockscout и сборщик URL.
- `chunks/BN7dtogv.js`: клиент Connect-RPC и описания protobuf в base64 (расшифрованы, см. ниже).

## Доступ (важно для запуска скриптов)

- Cloudflare на `testnet.polyesterscan.com` отвечает **403** на `User-Agent: Python-urllib/…`.
  С любым своим User-Agent отвечает 200. В `scan_probe.py` задан свой.
- На `api.testnet.polyester.com` методы `chain.*` (flows, конфиг сетей, аналитика) закрыты
  проверкой Cloudflare «Just a moment…» **для curl**. Из Python (urllib) в 16:05–16:15 UTC ответы
  шли нормально. Методы `marketdata.*` и `marketoverview.*` открыты для всех.
- Документация `testnet.polyester.com/docs/...` из облачной среды закрыта проверкой Cloudflare
  (и для curl, и для headless-браузера). Есть сохранённая копия от 10.09 в `docs/snapshot_2026-09-10/`
  (файлы по 1–3,6 МБ, искать grep'ом; страница начинается строкой `===== адрес =====`).

## 1. Blockscout API — `https://scan.polyester.live`

Ресурсы, которые реально вызывают страницы сайта (имя в коде → путь):

| Ресурс | Путь | Параметры |
|---|---|---|
| general:stats | `/api/v2/stats` | заголовок `updated-gas-oracle: true` |
| general:homepage_blocks | `/api/v2/main-page/blocks` | — |
| general:homepage_txs | `/api/v2/main-page/transactions` | — |
| general:blocks | `/api/v2/blocks` | `type=block|uncle|reorg`, листание |
| general:block | `/api/v2/blocks/:height_or_hash` | — |
| general:block_txs | `/api/v2/blocks/:height_or_hash/transactions` | листание |
| general:block_internal_txs | `/api/v2/blocks/:height_or_hash/internal-transactions` | листание |
| general:txs_validated / txs_pending | `/api/v2/transactions` | `filter=validated|pending`, листание |
| general:txs_stats | `/api/v2/transactions/stats` | — |
| general:tx | `/api/v2/transactions/:hash` | — |
| general:tx_token_transfers | `/api/v2/transactions/:hash/token-transfers` | — |
| general:tx_internal_txs | `/api/v2/transactions/:hash/internal-transactions` | — |
| general:tx_logs | `/api/v2/transactions/:hash/logs` | — |
| general:tx_raw_trace | `/api/v2/transactions/:hash/raw-trace` | — |
| general:tx_state_changes | `/api/v2/transactions/:hash/state-changes` | — |
| general:tx_interpretation | `/api/v2/transactions/:hash/summary` | — |
| general:internal_txs | `/api/v2/internal-transactions` | `transaction_hash` |
| general:addresses | `/api/v2/addresses/` | листание |
| general:address | `/api/v2/addresses/:hash` | — |
| general:address_counters | `/api/v2/addresses/:hash/counters` | — |
| general:address_txs | `/api/v2/addresses/:hash/transactions` | `filter`, листание |
| general:address_token_transfers | `/api/v2/addresses/:hash/token-transfers` | `filter`, `type`, `token` |
| general:address_internal_txs | `/api/v2/addresses/:hash/internal-transactions` | — |
| general:address_tokens | `/api/v2/addresses/:hash/tokens` | `type` |
| general:tokens | `/api/v2/tokens` | `q`, `type` |
| general:token | `/api/v2/tokens/:hash` | — |
| general:token_counters | `/api/v2/tokens/:hash/counters` | — |
| general:token_holders | `/api/v2/tokens/:hash/holders` | — |
| general:token_transfers | `/api/v2/tokens/:hash/transfers` | — |
| general:token_transfers_all | `/api/v2/token-transfers` | `type` |
| general:contract | `/api/v2/smart-contracts/:hash` | — |
| general:verified_contracts | `/api/v2/smart-contracts` | `q`, `filter` |
| general:config_contract_languages | `/api/v2/config/smart-contracts/languages` | — |
| general:advanced_filter | `/api/v2/advanced-filters` | много фильтров |
| general:advanced_filter_methods | `/api/v2/advanced-filters/methods` | `q` |
| general:search | `/api/v2/search` | `q`, листание |
| general:quick_search | `/api/v2/search/quick` | `q` |
| general:search_check_redirect | `/api/v2/search/check-redirect` | `q` → `{redirect, type, parameter}` |
| general:stats_charts_txs | `/api/v2/stats/charts/transactions` | — |
| metadata:info | `/api/v1/metadata` (через сайт: `/api/metadata`) | — |
| contractInfo:token_verified_info | `/api/v1/chains/:chainId/token-infos/:hash` (через сайт: `/api/contract-info`) | — |

**Листание** — «курсором», как в Blockscout: в ответе `next_page_params`
(например `{"block_number":2964676,"items_count":50}` или
`{"block_number":…,"index":0,"items_count":50}` у транзакций). Эти поля целиком
передаются в query следующего запроса. Параметров `limit`/`offset` нет, страница = 50 записей.

**Форматы**: суммы — строки в wei (`value`, `fee.value`, `total_supply`, `coin_balance`),
`decimals` — строка. Время — ISO-8601 в UTC с `Z` (`2026-09-28T15:51:45.000000Z`).
`average_block_time` в `/api/v2/stats` — в миллисекундах (≈450).

### Статистика через сайт (порт 8080 проксируется)
- `GET {BASE}/api/stats/counters` — счётчики (`averageBlockTime` в секундах, `totalTxns`, `completedTxns`, `totalBlocks`, `newTxns24h`…)
- `GET {BASE}/api/stats/lines` — список графиков
- `GET {BASE}/api/stats/lines/{chartId}?from=YYYY-MM-DD&to=YYYY-MM-DD&resolution=DAY|WEEK|MONTH|YEAR`

## 2. Connect-RPC — `https://api.testnet.polyester.com`

Вызов: `POST {API}/{пакет}.{Сервис}/{Метод}`, заголовки
`Content-Type: application/json`, `Connect-Protocol-Version: 1`, тело — JSON
(поля в camelCase). Ошибка — JSON `{"code":"invalid_argument","message":…}` с HTTP 4xx.
Числа `uint64`/`fixed64` приходят строками. Суммы `U128` приходят как `{"hi":"…","lo":"…"}` с масштабом 1e18 (`amountE18`).

Для обозревателя главное:

```
service chain.lifecycle.v1.LifecycleReadService
  rpc GetFlowById(GetFlowByIdRequest{flow_id})            -> GetFlowResponse{flow{summary, observedSteps[…]}}
  rpc ListFlows(ListFlowsRequest)                         -> ListFlowsResponse{flows[], next_page_token}
  rpc ListFlowsByTx(ListFlowsByTxRequest{tx_hash, lookup_kind, limit, page_token}) -> {matches[], next_page_token}

ListFlowsRequest: limit(uint32, по коду сайта 0..500, по умолчанию 100), sort(SORT_NEWEST|SORT_OLDEST),
  flow_kind(KIND_DEPOSIT|KIND_WITHDRAW|KIND_TRANSFER), flow_state, tx_ref, scope(LIST_ALL|LIST_OPEN_ONLY|LIST_TERMINAL_ONLY),
  owner_account_id, smart_account_address, polyester_chain_ids[], zipped_asset_ids[], unified_asset_ids[],
  page_token, order_by(ORDER_BY_LAST_ACTIVITY|ORDER_BY_STARTED_AT)
```

Поле `flowId` имеет вид `flow_<base58>`. Время в flows — `*UnixMs` (миллисекунды).
Полный разбор сообщений — в [`docs/proto/lifecycle_read.txt`](proto/lifecycle_read.txt).

Пример:
```
POST https://api.testnet.polyester.com/chain.lifecycle.v1.LifecycleReadService/ListFlows
{"limit":3,"polyesterChainIds":[3]}
```

Те же методы есть в REST (справочник api-docs, копия 10.09; примеры там на старом адресе альфы
`api-devnet.polyester.ai`, на тестнете — `api.testnet.polyester.com`):

| REST | = RPC | Живьём |
|---|---|---|
| `GET /v1/chain/flows` (flowKind, flowState, limit, orderBy, ownerAccountId, pageToken, polyesterChainIds, scope, sort, txRef, unifiedAssetIds, zippedAssetIds) | ListFlows | не проверял |
| `GET /v1/chain/flows/{flow_id}` | GetFlowById | 200, 28.09 16:36 UTC |
| `GET /v1/chain/flows/by-tx/{tx_hash}/matches` | ListFlowsByTx | не проверял |
| `GET /v1/chain/deposit-withdraw/config` | ZipperService/GetDepositWithdrawConfig | не проверял |
| `GET /v1/chain/analytics/zipped-asset-supply`, `…/group`, `/v1/chain/analytics/unified-asset-balances` | ChainAnalyticsService | не проверял |

`pageToken` в живом API — курсор `base64({"v":2,"s":…,"o":…,"m":<ms>,"f":"flow_…"})`
(в примере справочника старый вид `{"offset":100}`).

Другие сервисы в бандле (публичные, без входа — только часть):

| Сервис | Методы |
|---|---|
| chain.zipper.v1.ZipperService | GetDepositWithdrawConfig (сети, активы, комиссии, лимиты, `explorerUrl`) |
| chain.analytics.v1.ChainAnalyticsService | GetZippedAssetSupply, GetZippedAssetSupplyGroup, GetUnifiedAssetBalances |
| marketdata.v1.MarketDataService | GetSpotConfig (`tsSec` в секундах), GetTrades, GetCandles, GetCandlesColumns |
| marketoverview.v1.MarketOverviewService | ListMarketOverview (`lastTradeTsNs` в наносекундах), GetSpotVolumeHistory, GetCurrencyConversionRates/Config |
| orderbook.v1.OrderbookService | GetOrderBook |
| marketdata.v1.HeatmapService | GetOrderbookHeatmap |
| fees.v1.FeeService, ratelimit.v1.RateLimitService | GetSpotFeeRates, GetRateLimitConfig |

С авторизацией (не трогали): Auth*, Ledger*, Orders*, Withdraw, DepositAddress, Guard*, Triggers, VIP, Claims и т.д.

Вебсокет-каналы flows (в коде): `public:chain:lifecycle:flows:proto`,
`public:chain:lifecycle:flow:{flowId}:proto`, `private:chain:lifecycle:flows:{accountId}:proto`.

## 3. Конфиг сетей и активов, встроенный в HTML

Сервер кладёт в HTML главной (и других страниц) объект `zipper:{chains:[…], assets:[…]}` —
это, по сути, ответ `ZipperService/GetDepositWithdrawConfig`. Для каждой сети:
`chainId` (внутренний номер Polyester), `code`, `name`, `explorerUrl`, подтверждения, длина адресов.
Для каждого актива и сети: `zippedAssetId`, `networkFee`, `depositMinAmount`, `withdrawMinAmount`,
`supply`, `sourceToken{address,decimals}`, `zToken{address,decimals}` (токен в сети Polyester).

Сети-источники testnet (16 шт. + сама Polyester) и `explorerUrl` (снято скриптом 28.09 16:15 UTC):

| chainId | code | explorerUrl |
|---|---|---|
| 1 | bitcoin-testnet3 | https://mempool.space/testnet |
| 2 | ethereum-sepolia | https://sepolia.etherscan.io |
| 3 | solana-devnet | https://solscan.io/?cluster=devnet |
| 4 | base-sepolia | https://sepolia.basescan.org |
| 5 | arbitrum-sepolia | https://sepolia.arbiscan.io |
| 6 | bsc-testnet | https://testnet.bscscan.com |
| 7 | doge-testnet | https://doge-testnet-explorer.qed.me |
| 8 | litecoin-testnet | https://litecoinspace.org/testnet |
| 9 | ripple-testnet | https://testnet.xrpl.org/ |
| 10 | bitcoincash-testnet | https://tbch.loping.net |
| 11 | ethereum-classic-testnet | https://etc-mordor.blockscout.com |
| 12 | polygon-amoy | https://amoy.polygonscan.com |
| 13 | avalanche-fuji | https://testnet.snowtrace.io |
| 14 | hyperevm-testnet | https://explore-testnet.hyperpc.app |
| 15 | robinhood-testnet | https://explorer.testnet.chain.robinhood.com |
| 16 | tron-nile | https://nile.tronscan.org |
| 888169 | polyester-testnet | https://testnet.polyesterscan.com |

Как сайт делает ссылки из `explorerUrl` (`chunks/CKgKAkPt.js`, функция `h`):
- обычные сети: `{explorerUrl}/tx/{hash}`, `/address/{addr}`, `/token/{addr}` (путь и `?…` сохраняются);
- `solscan.io`: `https://solscan.io/tx/{hash}?cluster=devnet` (параметр переносится в конец);
- `tronscan.org`: `…/#/transaction/{hash}`; `xrpl.org`: `…/transactions/{hash}`.
- **Но** ссылки «сеть» и «нативный токен» строятся как `new URL(explorerUrl).origin`
  (`chunks/Dj4nS8JF.js`, функция `I`) — путь и параметры теряются (см. findings).

Ещё есть запасная таблица ссылок по имени сети (`chunks/CKgKAkPt.js`) с колонками testnet/mainnet —
в ней для «testnet» у Tron, XRP, Dogecoin, Optimism, Polkadot, Cosmos, Aptos, Monero стоят
основные сети, у Polygon — закрытый `mumbai`. Используется только если у сети нет `explorerUrl`.

## 4. Прочее из бандла

- Сети сайта: devnet `scan.polyester.tech` / `api.devnet.polyester.com` / `rpc.polyester.tech` (chain 888168),
  testnet `scan.polyester.live` / `api.testnet.polyester.com` / `rpc.polyester.live` (chain 888169),
  mainnet `scan.polyester.com` (в коде есть, сети пока нет).
- Панель «API» на странице расчёта (flow) показывает `https://api-devnet.polyester.ai/v1/chain/flows/{flowId}` —
  это REST API сети **devnet** (см. findings).
- В бандле есть ИИ-помощник: `/api/ai/code/session` (с Cloudflare Turnstile), в коде упомянуты OpenAI/Anthropic/Groq/xAI/DeepSeek/Cloudflare Workers AI (не проверяли).
