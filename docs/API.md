# API Protokol

Базовый адрес Docker: `http://localhost:8080`; dev: `http://localhost:8000`. Все маршруты ниже начинаются с `/api`. Интерактивная схема FastAPI доступна на `/docs` у dev-сервера. Авторизации нет; сервис предназначен для локального использования.

## Состояние

`GET /api/health` возвращает `status`, `database`, `model`, `domain`, `active_runs`, `version`, `provenance`, `llm_endpoint`, `stt_device`, `models_present`, `api_key_configured`.

```json
{
  "status": "ok",
  "database": "ok",
  "model": "scripted:auto",
  "domain": {"key": "protokol", "title": "Протокол совещания"},
  "provenance": {"enabled": true, "blocked_external_connections": 0},
  "llm_endpoint": "http://localhost:11434/v1",
  "stt_device": "cpu",
  "models_present": true
}
```

Это сокращённый пример. `models_present` проверяет наличие и ненулевой размер ожидаемых файлов; не проверяет качество распознавания. Наличие `llm_endpoint` в scripted-режиме не означает обращение к Ollama. `api_key_configured` также не доказывает наличие облачного подключения.

## Встречи

| Метод и путь | Запрос / результат |
|---|---|
| `POST /api/domain/meetings` | multipart: `file`, `title`, `meeting_date`; `202 {"meeting": ...}` |
| `GET /api/domain/meetings/{id}` | `{meeting, speakers, segments, protocol, action_items}` |
| `POST /api/domain/meetings/{id}/transcribe` | Без тела; `202 {meeting_id, status: "transcribing"}` |
| `PATCH /api/domain/meetings/{id}/speakers/{speaker_id}` | JSON `{"display_name":"Имя"}`; `{speaker: ...}` |
| `GET /api/domain/examples` | `{examples: [...]}` для всех сохранённых встреч, включая загрузки |
| `GET /api/domain/cases/{case_ref}` | Представление встречи для интерфейса, `case_ref` равен ID встречи |
| `POST /api/domain/reset` | Удаляет две встроенные встречи, их запуски и зависимые данные; создаёт записи образцов заново |

Загрузка принимает `.mp3`, `.wav`, `.m4a`, `.mp4`, `.ogg`, `.webm`, `.flac`. Дата — `YYYY-MM-DD`, название — 1–200 символов. Пустой файл отклоняется (422), неподдерживаемое расширение — 415. Ограничение загрузочного HTTP-запроса — 300 MiB вместе с multipart-обрамлением; остальных запросов — 1 MiB. Превышение даёт 413. Принятая загрузка ещё не подтверждает, что файл можно декодировать.

Статусы встречи: `uploaded`, `transcribing`, `ready`, `failed`. Проверяйте `meeting.error`, если обработка завершилась ошибкой. Уже обрабатываемая встреча и встреча с подтверждённым протоколом возвращают 409 при повторном запуске распознавания. Полный CPU-прогон может занимать несколько минут; HTTP-запрос запуска сам распознавания не ждёт.

Основные поля результата:

```text
meeting: id, title, meeting_date, audio_path, status, error,
         duration_s, language_hint, created_at
speakers[]: meeting_id, speaker_id, display_name
segments[]: id, meeting_id, idx, start_s, end_s, speaker_id,
            language, text, words[{start,end,text,prob}]
protocol: null либо id, meeting_id, run_id, summary, decisions[], confirmed_at
action_items[]: id, protocol_id, meeting_id, action_key, text, owner_name,
                owner_speaker_id, deadline_text, deadline_date, urgency,
                status, source_segment_ids[]
```

`GET /cases/{case_ref}` дополнительно содержит верхнеуровневые `case_ref`, `title`, `description`, `status`, `meeting_date`, `duration_s`, `error` и те же данные встречи. `protocol` — последний сохранённый протокол; `action_items` относятся к нему.

`owner_name` — исполнитель, а `owner_speaker_id` — говорящий, давший поручение, либо `null`. Идентификаторы сегментов глобальные в БД: не предполагайте, что новая встреча начинается с сегмента 1. Времена — секунды от начала записи. `deadline_date=null` означает, что календарный срок не установлен; исходная фраза сохраняется отдельно. Относительные сроки рассчитываются от даты встречи; неделя нормализуется к пятнице по соглашению приложения.

## Запуск протоколиста

`POST /api/runs` возвращает `202 {"run": ...}`:

```json
{
  "case_ref": "m-sample-1",
  "goal": "Составь протокол совещания",
  "input": {"meeting_date": "2026-09-23", "language": "auto"},
  "options": {"max_turns": 20}
}
```

В `input` дата обязательна; `language` допускает `ru`, `kk`, `auto`, `notes` — необязательный текст до 2000 символов. Эти поля относятся к запросу протоколиста; `language` не является параметром принудительного выбора ASR-модели в маршруте `/transcribe`.

`GET /api/runs?limit=50` возвращает `{runs: [...]}`. `GET /api/runs/{id}` возвращает:

```text
run: id, case_ref, goal, input, status, outcome, model, max_turns,
     error, stats, created_at, started_at, finished_at, updated_at
proposal: последнее предложение либо null
proposals: все версии предложений
needs_input, infeasible: пояснения при соответствующем исходе либо null
application: результат подтверждения либо null
snapshot_before, snapshot_after, messages
```

Статусы запуска: `queued`, `analyzing`, `needs_input`, `infeasible`, `proposed`, `validation_failed`, `applying`, `applied`, `verified`, `failed`, `interrupted`. `outcome` — `proposal_ready`, `needs_input`, `infeasible` либо `null`.

Предложение содержит `id`, `version`, `status`, `content`, `validation`, `basis_fingerprint`. В `content` находятся `summary`, `decisions`, `actions`, `evidence`, `assumptions`, `expected_effects`. Каждое действие:

```json
{
  "action_id": "a1",
  "type": "action_item",
  "text": "Подготовить отчёт",
  "owner_name": "не назначен",
  "owner_speaker_id": "S1",
  "deadline_text": "до пятницы",
  "deadline_date": "2026-09-25",
  "urgency": "средний",
  "source_segment_ids": [123]
}
```

Пример показывает форму, а не данные конкретной встречи. `text` — 1–500 символов; `source_segment_ids` непустой; `urgency` — `высокий`, `средний`, `низкий`. Пустой список действий допустим. `validation.ok=true` подтверждает прохождение программных правил, а не смысловую точность каждого поручения.

## Подтверждение и экспорт

`POST /api/runs/{id}/apply`:

```json
{"proposal_id":"UUID из proposal.id","version":1}
```

Используйте фактические ID и версию последнего предложения. Успех: `200 {run, application}` с результатами применения и проверки. Завершённый успешный статус — `verified`. Типовые конфликты (409): `duplicate_apply`, `stale_proposal`, `invalid_state`. Изменение говорящего после предложения может сделать его устаревшим; создайте новый запуск.

| Экспорт | Тип ответа |
|---|---|
| `GET /api/domain/meetings/{id}/protocol.pdf` | `application/pdf` |
| `GET /api/domain/meetings/{id}/protocol.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

Оба маршрута возвращают файл с заголовком `Content-Disposition: attachment`; при отсутствии подтверждённого протокола — 404. Экспорт включает название, дату, участников, саммари, решения, поручения и стенограмму. API редактирования текста/срока поручения и изменения его статуса пока нет.

## События и ошибки

`GET /api/runs/{id}/events/list?after=0` возвращает `{events: [...]}`. `GET /api/runs/{id}/events` открывает SSE: сначала воспроизводит сохранённые события, затем передаёт новые. Продолжение — `Last-Event-ID` или `?after=<номер>`.

Событие содержит `id`, `run_id`, `type`, `ts`, `run_status`, `payload`. Основные типы: `run_started`, `tool_started`, `tool_finished`, `tool_failed`, `agent_output`, `proposal_ready`, `validation_failed`, `revision_started`, `apply_started`, `apply_rejected`, `action_applied`, `verification_finished`, `run_finished`, `run_failed`. Аргументы и результаты инструментов ограничены по размеру; поле `truncated` указывает обрезание. Это события протоколиста, а не непрерывный прогресс ASR.

Прикладные ошибки обычно имеют форму `{"error":{"code":"...","message":"...","details":{}}}`. Ошибки параметров FastAPI и отдельные HTTP-ошибки загрузки/экспорта могут иметь `detail`; клиент должен проверять HTTP-статус и тело ответа.

## Проверка через curl

Команды выполняются из корня репозитория в Bash; нужны `curl` и `jq`. Стек должен быть запущен. Создаётся отдельная встреча, существующие протоколы не удаляются. Дата 2026-09-23 задаётся явно для демонстрации; исходные записи не устанавливают год совещания.

```bash
set -euo pipefail
API=http://localhost:8080
MEETING=$(curl -fsS "$API/api/domain/meetings" \
  -F 'file=@backend/samples/sovechanie_2.mp3' \
  -F 'title=Проверка Protokol' -F 'meeting_date=2026-09-23' | jq -er '.meeting.id')
curl -fsS -X POST "$API/api/domain/meetings/$MEETING/transcribe"
STATUS=transcribing
for i in $(seq 1 240); do
  STATUS=$(curl -fsS "$API/api/domain/meetings/$MEETING" | jq -r '.meeting.status')
  case "$STATUS" in ready|failed) break ;; esac
  sleep 5
done
if [ "$STATUS" != ready ]; then
  curl -fsS "$API/api/domain/meetings/$MEETING" | jq '.meeting'
  exit 1
fi
REQUEST=$(jq -nc --arg id "$MEETING" \
  '{case_ref:$id,goal:"Составь протокол совещания",input:{meeting_date:"2026-09-23"}}')
RUN=$(curl -fsS "$API/api/runs" -H 'Content-Type: application/json' \
  -d "$REQUEST" | jq -er '.run.id')
STATUS=queued
for i in $(seq 1 180); do
  DETAIL=$(curl -fsS "$API/api/runs/$RUN")
  STATUS=$(jq -r '.run.status' <<< "$DETAIL")
  case "$STATUS" in queued|analyzing) sleep 2 ;; *) break ;; esac
done
jq '{status:.run.status,proposal:.proposal.content,validation:.proposal.validation}' <<< "$DETAIL"
test "$STATUS" = proposed
# Перед следующим запросом просмотрите выведенные поручения и цитаты.
APPROVAL=$(jq -c '.proposal | {proposal_id:.id,version:.version}' <<< "$DETAIL")
curl -fsS -X POST "$API/api/runs/$RUN/apply" \
  -H 'Content-Type: application/json' -d "$APPROVAL" | jq -e '.run.status == "verified"'
curl -fsS "$API/api/domain/meetings/$MEETING/protocol.pdf" -o protocol.pdf
curl -fsS "$API/api/domain/meetings/$MEETING/protocol.docx" -o protocol.docx
curl -fsS "$API/api/health" | jq '.provenance'
```

В проверенном Docker-прогоне запись №2 распозналась за 472 секунды, получен один scripted-кандидат, статус `verified` и PDF: [фактический результат](../evaluation/docker-smoke.json). Это демонстрация процесса, не оценка полноты извлечения.
