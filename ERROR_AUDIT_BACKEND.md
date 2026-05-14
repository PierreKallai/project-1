# Auditoria de errores backend/API

Fecha: 2026-05-14  
Alcance: `Api_Onorato/` y pipeline propio `OnoratoFarm/`  
Objetivo: documentar todos los tipos de error detectables en backend, API, cron y pipeline IA antes de tocar codigo.

## Resumen ejecutivo

El backend tiene tres capas de error:

- Capa global Flask: `API/functions/errors/error_handler.py` registra `404`, `AppError` y `Exception`.
- Capa tipada: `API/functions/errors/error.py` define el catalogo `AppError`.
- Capa historica/manual: muchas rutas devuelven `jsonify({"error": ...})` o `jsonify({"message": ...})` directamente.

Inventario por busqueda en codigo propio:

- `Api_Onorato/API` + `send_second_talk_emails.py`: 231 `except` activos, 170 `raise AppError`.
- `OnoratoFarm` sin `venv`: 29 `except`.
- `API/app_antigua.py`: existe y contiene errores legacy, pero no esta registrado como entrypoint actual.

## Catalogo AppError vigente

Fuente: `Api_Onorato/API/functions/errors/error.py`.

| Codigo | HTTP | Severidad | Accion | Tipo de error |
|---|---:|---|---|---|
| `AUTH_FAILED` | 401 | WARNING | none | Auth fallida, contexto de usuario ausente, credenciales invalidas |
| `USER_NOT_FOUND` | 404 | WARNING | none | Usuario inexistente en DB/Cognito |
| `USER_NOT_CONFIRMED` | 403 | WARNING | none | Cuenta Cognito sin confirmar |
| `USER_EXISTS_CLOUD` | 409 | WARNING | none | Email ya existe en Cognito |
| `INVALID_CODE` | 400 | WARNING | none | Codigo incorrecto o no asociado |
| `EXPIRED_CODE` | 400 | WARNING | none | Codigo caducado |
| `LIMIT_EXCEEDED` | 429 | WARNING | none | Limite Cognito/servicio excedido |
| `TOO_MANY_ATTEMPTS` | 429 | WARNING | none | Bloqueo temporal por intentos |
| `WEAK_PASSWORD` | 400 | WARNING | none | Password no cumple politica |
| `NEW_PASSWORD_REQUIRED` | 405 | WARNING | none | Cognito requiere cambio de password |
| `PASSWORD_RESET_REQUIRED` | 400 | WARNING | none | Password debe restablecerse |
| `INVALID_PARAMETER` | 400 | WARNING | notify_dev | Payload, email, id o parametro invalido |
| `USER_LAMBDA_ERROR` | 500 | CRITICAL | restart_service | Fallo interno Cognito Lambda |
| `INTERNAL_AWS_ERROR` | 500 | CRITICAL | restart_service | Fallo AWS no especifico |
| `MISSING_FIELDS` | 400 | WARNING | none | Campos obligatorios ausentes |
| `AUDIO_TOO_LARGE` | 413 | WARNING | none | Audio supera limite |
| `INVALID_EMAIL` | 400 | WARNING | none | Email invalido |
| `NO_INVITATION` | 403 | WARNING | none | Invitacion inexistente |
| `FEEDBACK_ACCESS_DENIED` | 403 | WARNING | none | Charla/feedback aun no disponible |
| `USER_EXISTS_LOCAL` | 409 | WARNING | none | Usuario duplicado localmente |
| `STRIPE_ERROR` | 500 | CRITICAL | notify_dev | Stripe falla |
| `INVALID_PAYMENT_DATA` | 400 | WARNING | none | Datos de pago invalidos |
| `QUANTITY_EXCEEDED` | 400 | WARNING | none | Cantidad de compra no permitida |
| `DUPLICATE_PURCHASE` | 400 | WARNING | none | Compra ya activa |
| `AI_ERROR` | 500 | CRITICAL | clear_temp | LLM/IA falla |
| `VOICE_GENERATION_ERROR` | 500 | CRITICAL | restart_service | TTS falla |
| `S3_ERROR` | 503 | CRITICAL | restart_service | S3/bucket falla |
| `TICKET_DB_ERROR` | 500 | CRITICAL | restart_service | Sistema tickets falla en DB |
| `TICKET_NOT_FOUND` | 404 | WARNING | none | Ticket inexistente |
| `SES_EMAIL_ERROR` | 503 | CRITICAL | notify_dev | Email SES falla |
| `DB_TABLE_MISSING` | 500 | CRITICAL | fix_db_schema | Tabla o esquema DB inexistente |
| `GENERIC_ERROR` | 500 | CRITICAL | notify_dev | Error no clasificado |

## Handlers globales

| Archivo | Handler | Cubre | Riesgo |
|---|---|---|---|
| `API/functions/errors/error_handler.py:26` | `@app.errorhandler(404)` | Ruta inexistente | Devuelve `NOT_FOUND`; no usa `AppError` |
| `API/functions/errors/error_handler.py:37` | `@app.errorhandler(AppError)` | Errores tipados | Ejecuta accion automatica; si la accion falla notifica `FIX_ACTION_FAILED` |
| `API/functions/errors/error_handler.py:51` | `@app.errorhandler(Exception)` | Excepciones no controladas | Envuelve como `GENERIC_ERROR`; no intercepta `HTTPException` |
| `API/app.py:56` | init Redis | Fallo Redis/rate limiting | No rompe API, deja `hash_redis_client=None` |

## Errores criticos transversales

Estos errores pueden romper la API completa o una feature principal.

| Area | Error posible | Impacto | Archivos principales | Tratamiento actual |
|---|---|---|---|---|
| Arranque Flask | Imports rotos, dependencias faltantes, `.env` ausente | API no levanta | `API/app.py` | Solo Redis esta protegido |
| Redis | Host/puerto invalido, conexion rechazada | Rate limiting deshabilitado | `API/app.py`, `API/functions/redis_server.py` | `fail_silent=True`; log warning/error |
| DB MySQL | Credenciales invalidas, host caido, DB inexistente, tabla inexistente, SQL syntax, FK/unique | Endpoints 500 | `API/functions/db_connection.py`, rutas DB | `AppError` parcial; muchas rutas devuelven JSON manual |
| Secrets | Secret inexistente, JSON invalido, AWS denied, fallback `.env` incompleto | Auth/DB/AWS no funciona | `API/functions/secrets_manager.py` | Lanza `Exception`, luego global lo vuelve `GENERIC_ERROR` |
| Auth JWT/Cognito | Token ausente, expirado, kid invalido, JWKS inaccesible, issuer/audience invalido | Rutas protegidas bloqueadas | `require_auth_hybrid.py`, `refresh_token.py` | JSON 401 manual y logs |
| Admin auth | Usuario sin rol admin, fallo al validar permisos | Admin bloqueado o 500 | `require_admin.py` | JSON manual |
| S3 | Credenciales ausentes, bucket/key inexistente, JSON corrupto, permisos denied | Formulario/feedback/dataset/audio fallan | `buckets.py`, dataset routes | `S3_ERROR`, custom errors y manual JSON |
| SES | Email no verificado, quota, reject, credenciales, region | Invitaciones/recordatorios/recovery fallan | `create_invitation.py`, `recover_password.py`, `reminders.py`, `notifyer.py` | Mixto `AppError` y JSON manual |
| Cognito | Username exists, code mismatch, expired code, limit, not confirmed, new password required | Login/register/recovery fallan | `login.py`, `register.py`, `recover_password.py`, `refresh_token.py` | Mixto JSON manual y `AppError` |
| Stripe | Firma webhook invalida, secret ausente, intent falla, DB al crear invitacion | Pagos no confirmados | `stripe/*.py` | JSON manual, no siempre `AppError` |
| OpenAI/Nextbit | API key ausente, timeout, rate limit, respuesta vacia/no JSON, tool call invalida | Chat IA/dataset/voice falla | `get_voice.py`, `reply_ai.py`, `OnoratoFarm/*` | Mayormente `Exception` o `GENERIC_ERROR` |
| Audio STT/TTS | Base64 invalido, audio > limite, extension no soportada, temp file, pydub/ffmpeg, OpenAI TTS/STT | Charla se bloquea | `transcription.py`, `get_voice.py` | `AUDIO_TOO_LARGE`, `VOICE_GENERATION_ERROR`, `GENERIC_ERROR` |
| Cron | Canal no soportado, AWS SESv2/Social/Connect, DB eventos, plantilla | Recordatorios automaticos fallan | `API/cron/cron_emails.py`, `cron_issue_logger.py` | Logging estructurado, excepciones capturadas |
| Logs | Tabla logs ausente, JSON user_progress invalido, delete falla | Observabilidad rota | `frontend_logs.py`, `logs_view.py`, `cron_logs.py` | `AppError` parcial y JSON manual |

## Errores no criticos pero a tratar

| Area | Error posible | Impacto |
|---|---|---|
| `language` invalido o ausente | Fallback a idioma por defecto o datos incorrectos |
| Parseo de respuestas tipo lista | Preguntas checkbox/agregar opcion pueden perder formato |
| `number_version` / `number_chat` ausente | Feedback o charla incorrecta |
| No hay datos todavia | Stats, invitaciones, usuarios o dataset devuelven vacio/404 |
| Email con formato valido pero dominio no resoluble | Registro/recovery/invitacion fallan |
| `request.json` vacio | Endpoints con `data.get(...)` pueden lanzar `AttributeError` si no validan |
| Respuesta externa no JSON | Wrappers o rutas que hacen `json.loads` fallan |
| Errores silenciosos en cleanup | Cursores/conexiones pueden ocultar fallos en `finally` |

## Inventario de try/except backend

Resultado de `rg -n "except " Api_Onorato/API Api_Onorato/send_second_talk_emails.py --glob "*.py" --glob "!**/__pycache__/**"`.

| Archivo | Num. `except` | Familias de error cubiertas |
|---|---:|---|
| `API/app.py` | 1 | Redis init |
| `API/functions/actions.py` | 2 | Acciones automaticas de error |
| `API/functions/buckets.py` | 18 | S3 NoSuchKey, credenciales, Boto3, feedback file/replace |
| `API/functions/cron_issue_logger.py` | 4 | Parse JSON, escritura/cleanup logs cron |
| `API/functions/db_connection.py` | 2 | MySQL connector, excepcion generica |
| `API/functions/errors/error_handler.py` | 1 | Fallo de accion automatica |
| `API/functions/errors/notifyer.py` | 3 | SES al notificar errores |
| `API/functions/feedback_access.py` | 1 | Parse fecha/sesion |
| `API/functions/language_check.py` | 3 | Fallback idioma |
| `API/functions/receive_user_id.py` | 3 | Lookup user_id y cleanup |
| `API/functions/redis_server.py` | 5 | Conexion Redis y operaciones hash/string/list |
| `API/functions/require_admin.py` | 1 | Validacion admin |
| `API/functions/require_auth.py` | 2 | JWT expirado/invalido legacy |
| `API/functions/require_auth_hybrid.py` | 4 | JWKS, JWT expirado, JWT invalido, excepcion generica |
| `API/functions/secrets_manager.py` | 3 | JSON secret invalido, ClientError, Exception |
| `API/routes/admin/cron_logs.py` | 3 | Parse int, lectura/resolucion cron logs |
| `API/routes/admin/frontend_logs.py` | 5 | Delete, DB, AppError, generic, list |
| `API/routes/admin/info_users.py` | 11 | Parse fechas/JSON, DB stats/users, cleanup |
| `API/routes/admin/logs_view.py` | 1 | Lectura de logs |
| `API/routes/admin/reminders.py` | 2 | SES single, fallos parciales masivos |
| `API/routes/admin/stats.py` | 3 | DB stats, AppError, generic |
| `API/routes/admin/dataset/information_dataset.py` | 2 | S3/dataset stats/get |
| `API/routes/admin/dataset/reply_ai.py` | 2 | Geocoding/weather, llamada IA |
| `API/routes/admin/dataset/save_dataset.py` | 3 | JSON/OSError local, S3 load, S3 save |
| `API/routes/admin/dataset/send_profiles.py` | 3 | FileNotFound, JSONDecode, generic |
| `API/routes/finish_form/get_json_form.py` | 8 | Parse respuestas, SES, DB, generic, cleanup |
| `API/routes/invitations/check_invitation.py` | 3 | AppError, DB, generic |
| `API/routes/invitations/create_invitation.py` | 3 | SES ClientError, SES generic, DB generic |
| `API/routes/invitations/get_invitations.py` | 2 | AppError, DB/generic |
| `API/routes/onoratoFarm/get_voice.py` | 6 | IA/TTS/audio JSON/archivos/generic |
| `API/routes/onoratoFarm/manage_progres.py` | 2 | DB finish/is_finish |
| `API/routes/onoratoFarm/replace_feedback.py` | 1 | FeedbackReplaceError |
| `API/routes/onoratoFarm/transcription.py` | 3 | Base64, AppError, generic STT |
| `API/routes/permissions_functions/add_permission.py` | 1 | DB |
| `API/routes/permissions_functions/check_user_permissions.py` | 1 | DB |
| `API/routes/permissions_functions/get_permissions.py` | 2 | DB/list |
| `API/routes/permissions_functions/remove_permissions.py` | 1 | DB |
| `API/routes/question_user/add_answer.py` | 3 | JSONDecode, DB bulk, DB single |
| `API/routes/question_user/get_answers.py` | 1 | DB |
| `API/routes/question_user/has_answer.py` | 1 | DB |
| `API/routes/questions/add_question.py` | 3 | AppError, DB, generic |
| `API/routes/questions/delete_question.py` | 3 | AppError, DB, generic |
| `API/routes/questions/form_map.py` | 2 | AppError, DB/generic |
| `API/routes/questions/generate_form.py` | 5 | AppError, DB, generic, helper cleanup/fallback |
| `API/routes/questions/get_onboarding.py` | 4 | AppError, DB, generic, cleanup |
| `API/routes/questions/update_question.py` | 3 | AppError, DB, generic |
| `API/routes/role/assign_role_user.py` | 3 | DB duplicate, AppError, generic |
| `API/routes/role/check_role_user.py` | 2 | AppError, generic |
| `API/routes/role/remove_role_user.py` | 2 | AppError, generic |
| `API/routes/stripe/create_and_check_payment.py` | 2 | DB check email, Stripe/payment intent |
| `API/routes/stripe/webhook.py` | 4 | Firma, DB update, invitacion, generic webhook |
| `API/routes/tickets/send_ticket.py` | 7 | Parse user context, DB ticket, SES, messages, reply, status |
| `API/routes/user_identity/delete_profile.py` | 4 | Cognito delete, AppError, DB, generic |
| `API/routes/user_identity/get_info.py` | 2 | AppError, DB/generic |
| `API/routes/user_identity/login.py` | 8 | Cognito auth, DB login/request/verify, AppError, generic |
| `API/routes/user_identity/migrate_to_cognito.py` | 3 | Cognito create/delete/update, generic migration |
| `API/routes/user_identity/recover_password.py` | 17 | SES, DB, Cognito forgot/confirm, code mismatch, limits, generic |
| `API/routes/user_identity/refresh_token.py` | 3 | Token decode, Cognito refresh, generic endpoint |
| `API/routes/user_identity/register.py` | 12 | Cognito sign-up/confirm/resend/verify, DB rollback, generic |
| `API/routes/user_identity/update_profile.py` | 3 | AppError, DB, generic |
| `API/cron/cron_emails.py` | 10 | Fecha invalida, AWS channel lookups, event handling, per-user failures |
| `API/cron/plantillas_cron.py` | 1 | Render plantilla |
| `send_second_talk_emails.py` | 2 | SES ClientError/generic |

Nota: `API/app_antigua.py` tiene 2 `except` legacy de JWT; no se debe asumir vigente salvo que se reactive.

## Inventario OnoratoFarm

Resultado de `rg -n "except " OnoratoFarm --glob "*.py" --glob "!**/venv/**"`.

| Archivo | Num. `except` | Familias de error |
|---|---:|---|
| `agent.py` | 1 | Ejecucion IA/push bucket |
| `build_entry_dataset.py` | 1 | Login/token inicial |
| `chat/chat.py` | 4 | Parse JSON de LLM, login/token, loop conversacional |
| `chat/chat_not_tools/chat.py` | 4 | Parse JSON, login/token, carga personal card/dataset, loop |
| `chat/pipeline/test.py` | 2 | Parse JSON audio pipeline |
| `chat/roles/ai.py` | 1 | Login/token al preparar agente |
| `factorial_json/extract_patterns.py` | 2 | Bucket/API y JSON en respuestas |
| `functions/categorization.py` | 4 | Login/token, API bucket, parse bucket, push resultado |
| `functions/check_prompt.py` | 1 | Ejecucion eval prompt |
| `functions/importants_points.py` | 3 | Login/token, parse JSON LLM, push resultado |
| `functions/prompt_generator.py` | 2 | Login/token, ejecucion/push prompts |
| `personal_card/generated_personal_card.py` | 3 | Login/token, API bucket parse, generacion perfil |
| `prueba_entrenamiento.py` | 1 | Prueba IA |

Errores posibles especificos de `OnoratoFarm`:

- Login contra `https://api.onoratoai.com/login` falla o no devuelve token.
- Token hardcoded/obtenido expira durante pipeline.
- `/bucket/get` devuelve status no 2xx, payload no JSON o estructura inesperada.
- Archivos `categories/*.json`, `personal_card/*.json`, `dataset/*.json` faltan o tienen JSON corrupto.
- OpenAI/Nextbit rechaza credenciales, rate limit, timeout o devuelve texto no parseable.
- Pydantic/pydantic-ai falla por schema mismatch, output_type invalido o tool call mal formado.
- `requests.post` sin timeout puede colgar ejecuciones batch.
- `json.load(open(...))` sin context manager puede dejar recursos abiertos si falla en medio.

## Errores por grupo de endpoints

| Grupo | Endpoints | Errores que pueden ocurrir |
|---|---|---|
| Health/dataset | `/health`, `/dataset` | Auth ausente en `/dataset`, JSON no serializable, ruta inexistente |
| Auth login | `/login`, `/login/email/request`, `/login/email/verify` | Campos ausentes, email invalido, usuario no existe, password invalida, no confirmado, Cognito ClientError, DB missing, token generation |
| Refresh | `/auth/refresh` | Header `x-refresh-token` ausente, token invalido/expirado, email mismatch, Cognito refresh denied, rate limit |
| Register | `/register`, `/confirm_account`, `/verify_account`, `/resend_confirmation` | Email duplicado, invitacion ausente, password debil, rollback Cognito fallido, codigo invalido/caducado, DB inconsistente |
| Recovery | `/recover/send_message`, `/recover/password`, `/recover/temporaly` | Email ausente, usuario inexistente, SES reject, codigo invalido/caducado, password historica/debil, Cognito limit |
| User | `/user/info`, `/user/update`, `/admin/delete` | `g.user_id` ausente, email invalido, usuario no encontrado, intento borrar admin, Cognito delete falla despues de DB |
| Questions | `/questions`, `/questions/delete`, `/questions/generate_form`, `/questions/form_map`, `/onboarding` | Payload incompleto, pregunta/opcion no existe, SQL, idioma invalido, dependencias corruptas |
| Answers/form | `/question_user`, `/question_user/get`, `/question_user/has`, `/finish_form/get`, `/finish_form/check` | JSON invalido, respuesta no lista, campos ausentes, email invalido, S3/SES/DB, formulario incompleto |
| Buckets | `/bucket/get`, `/bucket/push` | S3 key missing, bucket missing, credenciales, JSON corrupto, payload de modo incompatible |
| Permissions/roles | `/permissions*`, `/role/*` | Falta rol/url, rol/funcion no existe, usuario sin contexto, permisos insuficientes, DB |
| Invitations | `/invitation/create`, `/invitation/check`, `/invitation/get` | Campos ausentes, email invalido, invitacion inexistente, SES, DB |
| Admin stats/users | `/admin/info_users`, `/user/stats`, `/admin/stats` | Sin datos, usuario no encontrado, tablas missing, parse fechas |
| Reminders | `/admin/reminders`, `/admin/reminders/single` | `array_info` ausente, SES parcial, email reject, lenguaje/nombre ausente |
| OnoratoFarm | `/onorato_farm/*` | IA falla, TTS/STT falla, audio invalido/grande, feedback inaccesible, version/sesion incorrecta, S3 |
| Tickets | `/tickets`, `/tickets/create` | Mensaje ausente, FormData/JSON mismatch, SES alert falla, DB |
| Dataset admin | `/admin/dataset/*` | Profiles missing, dataset S3 corrupto, id_user ausente, OpenAI/tool call/weather/geocoding falla |
| Logs | `/logs/frontend_error`, `/admin/logs*` | Tabla logs missing, payload incompleto, archivo log ausente, JSON user_progress invalido |
| Stripe | `/stripe-webhook`, `/check-email`, `/create-payment-intent` | Secret ausente, firma invalida, Stripe API, DB/invitacion post-pago |
| Test access | `/access-page` | Password incorrecta, cookie/test route |

## Lugares con respuesta JSON manual

Estos puntos no pasan siempre por `AppError`, por lo que el frontend puede recibir formatos distintos:

- `login.py`, `register.py`, `refresh_token.py`, `migrate_to_cognito.py`.
- `question_user/*.py`.
- `permissions_functions/*.py`.
- `stripe/*.py`.
- `admin/dataset/*.py`.
- `admin/cron_logs.py`, `admin/logs_view.py`.
- `onoratoFarm/manage_progres.py`, `replace_feedback.py`.
- `tickets/send_ticket.py` usa `AppError` en errores DB/SES, pero algunos endpoints no estan registrados en `app.py`.

Riesgo: el frontend espera a veces `message`, a veces `error`, a veces `error_code`, `solution`, `status`. Antes de actualizar catches conviene normalizar a `AppError` o un contrato unico.

## Errores de contrato detectados

Estos no son necesariamente excepciones Python, pero causan errores frontend/API:

- Frontend publico llama `DELETE /user/delete`; backend registrado: no existe, existe `/admin/delete`.
- Frontend publico llama `POST /recover/check`; backend registrado: `/recover/password`.
- Frontend publico llama `GET /questions/generate`; backend registrado: `/questions/generate_form`.
- Frontend publico expone wrappers admin antiguos: `/admin/users`, `/admin/users/{id}/status`, `/admin/users/{id}` no estan en `app.py`.
- Admin frontend llama endpoints de tickets no registrados: `/tickets/{id}/messages`, `/tickets/reply`, `/tickets/{id}/status`.
- `app.py` registra solo `/tickets` y `/tickets/create`, aunque `send_ticket.py` contiene funciones para messages/reply/status.

## Checklist para actualizar catches despues

No se ha escrito codigo en esta fase. Para la siguiente fase:

- Convertir respuestas manuales 4xx/5xx a `AppError` donde sea backend propio.
- Mantener excepciones de negocio 4xx como `WARNING`, no como `CRITICAL`.
- No envolver `AppError` dentro de `Exception` generico.
- En cada `except Exception`, registrar contexto minimo: endpoint, user_id/email si existe, payload keys, proveedor externo, operacion.
- Para llamadas externas, separar `ClientError`, timeout, respuesta no JSON y status no 2xx.
- Para DB, separar `mysql.connector.Error` y detectar `errno` conocidos: auth, database missing, table missing, duplicate, FK.
- Para S3, separar `NoSuchKey`, `NoCredentialsError`, `ClientError AccessDenied`, JSON corrupto.
- Para IA/audio, separar timeout/rate limit/invalid output/audio invalido.
- Revisar endpoints frontend desalineados antes de tocar catch UI.
