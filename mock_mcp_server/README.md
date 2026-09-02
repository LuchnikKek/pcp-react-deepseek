# Моковый MCP-сервер HR-бэкендов

FastMCP-сервер `hr-agent-mock`: 32 тула, имена и параметры которых заморожены (контракт
закреплён тестом `test_tool_contract`). Каждый тул возвращает **тело ответа backend-сервиса**
как есть — реальные ответы дев-стенда из `fixtures/real_data_fixtures.json`.

## Запуск

```powershell
uv run python -m mock_mcp_server --transport stdio
uv run python -m mock_mcp_server --transport streamable-http --host 127.0.0.1 --port 8081
uv run mock-mcp-server --help
```

Транспорт по умолчанию — `stdio` (или `$MOCK_MCP_TRANSPORT`).

## Тесты

```powershell
uv run pytest -q
```

Тесты в `tests/test_mock_server.py` поднимают сервер in-process через `fastmcp.Client`
и проверяют каждый тул на реальных значениях из фикстуры, контракт тулов и семантику ошибок.

## Структура

| Путь | Назначение |
|---|---|
| `server.py` | `build_app()` — сборка FastMCP-приложения, общая инструкция сервера для агента |
| `cli.py`, `__main__.py` | CLI-вход |
| `handlers/*.py` | По одному модулю на backend-сервис; тонкие `@mcp.tool`-обёртки над `data.*` с описаниями для агента |
| `data.py` | Загрузка фикстуры, справочники персон/курсов, lookup-хелперы (одна функция — один endpoint) |
| `fixtures/real_data_fixtures.json` | Реальные ответы дев-стенда, ключи вида `service:arg[:arg]` |
| `../tools/collect_real_data.py` | Справочный сборщик фикстуры (из этого репо не запускается) |

## Как устроены ответы и ошибки

### Описания тулов

Описание — то, по чему агент выбирает тул и читает ответ, поэтому оно на языке предметной
области: что это, какой вход (`employee_id` — табельный номер, `person_id` — UUID), какие поля
читать в `data`, что означает пустой ответ. Служебные поля (`success`, `pagination`, `meta`,
`totalElements`, `__metadata`) в описаниях не перечисляются — про них один раз сказано в
инструкции сервера (`server.INSTRUCTIONS`).

### Пусто vs ошибка

Критерий: вход — идентификатор одной сущности (должна существовать) или фильтр коллекции
(может быть пустой)?

- **Коллекция** → пустой `data` (или `d.results`) — нормальный ответ «данных нет».
- **По ключу** → если сущности нет, тул возвращает ошибку (`isError: true`) с текстом причины,
  например `Сотрудник с табельным номером 00000000 не найден`. В `data.py` это `NotFound`
  (наследник `fastmcp.exceptions.ToolError`).

| Ошибка при неизвестном ключе | Пустой ответ — норма |
|---|---|
| `get_id_mapper_person_id`, `person_profile`, `schedule_info`, `is_chief` (табельный) | `assignment`, `assignments_requirement`, `authorization_groups` |
| `get_health_company_name`, `org_structure_user_info` (person_id) | `item_ids_by_course_names`, `course_available`, `course_progress`, `item_tag` |
| `org_structure_vertex_position` (position_id) | `learning_history`, `learning_requests`, `onsite_activities_registrations` |
| `learning_request_info` (request_id), `onsite_activities_information` (activity_id) | `org_structure_hrbp_info`, `org_structure_subordinate`, `recruiter` |
| `user_request_info_by_number` (номер заявки) | `user_events_info`, `absence_limit`, `user_request_info`, `sicklist_info` |
| `job_info`, `job_application`, `publication_info`, `job_profile` (данных на стенде нет — всегда ошибка) | `publication_info_by_job_requisition_id` |

## Откуда данные

Значения — **реальные ответы дев-стенда**, собранные сборщиком `tools/collect_real_data.py`
по входным данным из таблиц ниже. `data.py` загружает JSON и отдаёт тела как есть; если файла
нет — импорт падает с `FileNotFoundError`. Ничего не выдумывается: где реальных данных нет —
пустой ответ по формату сервиса либо ошибка «не найдено» (см. выше).

### Каноническая связка `employee_id <-> person_id`

Подтверждена ответами `id_mapper`/`person_profile`; переиспользуется во всех API по табельному
(`person_profile`, `EASUP_*`, `id_mapper`) и по UUID.

| Символическое имя (`data.PERSONS`/`EMPLOYEES`) | employee_id | person_id | Активных назначений |
|---|---|---|---|
| `person_with_data` | `1655480` | `9f219670-8655-4aab-a7b3-fdcf4e732ac6` | 2 |
| `person_empty` | `5581690` | `4cccf617-0447-4d50-b90b-ae45096104b9` | 0 |
| `person_3_assignments` | `4441` | `3339552b-012b-4302-b331-129229c58eee` | 3 |
| `person_0_assignments_2` | `10000543` | `54dcb12a-4e27-415f-aead-30c4f0cb6868` | 0 |

### Каталог

| person_id | item_id |
|---|---|
| `b7ca0d52-18f8-4771-9b1d-6025e6f03a29` (`person_catalog_a`) | `caef115d-f7b0-41bc-88d8-5be35d3782cb` (`COURSE_A1`) |
| `b7ca0d52-18f8-4771-9b1d-6025e6f03a29` | `d7679660-1d8e-4027-8504-8af10a709334` (`COURSE_A2`) |
| `762275f2-aea0-4c06-a31e-521e40c383ea` (`person_catalog_b`) | `bb708aae-94e9-4b3d-83b8-ca387df02e61` (`COURSE_B1`) |
| `762275f2-aea0-4c06-a31e-521e40c383ea` | `03abd3f2-a9a0-4fa4-b493-bad2bd38649d` (`COURSE_B2`) |

Поиск по имени: «Правила пожарной безопасности» → `0f48be8a-4fcf-40b2-b51f-da894969ce59` (`COURSE_FF`),
реальное тело лежит под ключом `catalog:{название}`. `COURSES` (имя → item_id) строится из
реальных ответов `catalog`/`catalog_page`. Доступность (`course_available`) и прогресс
(`course_progress`) есть только для собранных пар персона–курс, для остальных — пустой `data`.

### Health

| person_id | Страховая (ДМС / НС) |
|---|---|
| `4482cbc6-05bf-43cb-9542-5b6a2b71acfb` (`person_health_1`) | АльфаСтрахование / СберСтрахование |
| `7d365279-d209-4e09-bdf2-55b2a1e65f07` (`person_health_nodms`) | без ДМС (`insurance` пустой), город есть |
| `30e7c92e-ee1b-4dd7-aaa6-0ca348c63b2b` | АльфаСтрахование |
| `661ac345-b4d3-4b35-8bf7-23814af7bcce` | АльфаСтрахование / СберСтрахование |
| `d38252c9-0ac4-4d7c-b864-516bf8cfbdbd` | СОГАЗ (Улан-Удэ) / СберСтрахование |
| `585e65dc-7e43-48ab-818e-6dd2bf9c644e` | ИнгосСтрахование / СберСтрахование |
| `dadcea6e-ff19-4156-8ff0-9599053c24e3` | ИнгосСтрахование / СберСтрахование |

«Основная» персона `9f219670-…` на стенде имеет пустой `insurance` — мок возвращает этот реальный ответ.

### EASUP (OData)

Табельные номера в 8-значном SAP-формате (`zfill(8)`, `4441` → `00004441`), как в `easup_repo`.
Реальные `ScheduleSet`/`EventsSet`/`LimitsSet`/`SickListSet` для четырёх табельных есть в фикстуре;
`AsChiefSet`/`StatusReqByPernrSet` на стенде дали 403 → для известных сотрудников `is_chief`
отвечает «не руководитель», `user_request_info` — пустой `results`.

### Что на стенде оказалось пустым

- `assignments_requirement` — `{"data": []}`;
- `learning_requests` (список по персоне) — `data: []`; при этом `learning_request_info`
  по реальным id заявок (63 штуки в фикстуре) возвращает полные данные;
- `onsite_activities_registrations` — `data: []`;
- `job_info`, `job_application`, `publication_info`, `job_profile` — данных нет вовсе, всегда «не найдено».

## Тулы (32)

| Сервис | Тулы |
|---|---|
| assignment | `assignment`, `assignments_requirement` |
| authorization | `authorization_groups` |
| catalog | `item_ids_by_course_names`, `course_available`, `course_progress`, `item_tag` |
| health | `get_health_company_name` |
| id_mapper | `get_id_mapper_person_id` |
| person_profile | `person_profile` |
| learning_history | `learning_history` |
| learning_requests | `learning_requests`, `learning_request_info` |
| onsite_activities | `onsite_activities_registrations`, `onsite_activities_information` |
| organisation_structure | `org_structure_user_info`, `org_structure_vertex_position`, `org_structure_hrbp_info`, `org_structure_subordinate` |
| recruitment | `job_info`, `job_application`, `recruiter` |
| recruitment_publication | `publication_info`, `publication_info_by_job_requisition_id` |
| job_profile | `job_profile` |
| easup | `schedule_info`, `user_events_info`, `absence_limit`, `user_request_info`, `user_request_info_by_number`, `is_chief`, `sicklist_info` |
