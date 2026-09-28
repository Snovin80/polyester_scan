---
name: polyester-discord-no-urls
description: "В Discord Polyester автомодерация банит за любые URL, даже в формате кода — в текстах для Discord адресов не давать"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 77e5ac97-cc0f-459a-b298-7d885428f8e3
  modified: 2026-09-25T10:09:51.363Z
---

В Discord-сервере Polyester нельзя отправлять никакие адреса (URL), даже
официальные домены Polyester и даже в обратных кавычках: автомодерация
блокирует сообщение и даёт тайм-аут 24 ч. Автор получил его 25.09.2026
по моему совету («в формате кода пройдёт» — было неправдой).

**Why:** я выдал догадку про обход фильтра за факт, автор пострадал.

**How to apply:** в текстах для их Discord описывать словами без адресов
(«testnet API host from the docs, api-testnet instead of api-devnet»),
не утверждать, как поведёт себя модерация, если не знаю. Отчёты команде
шлются в чат Polyester — тоже без ссылок. См. [[report-style-polyester]].
