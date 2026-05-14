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

## Politica de alertas por email

Objetivo: evitar spam al equipo dev. Solo deben enviar email los errores que requieren intervencion inmediata o indican que una parte critica del sistema esta caida. Todo lo demas debe registrarse para revision en el admin panel.

Regla principal:

- Enviar email: errores `CRITICAL` que bloquean una feature principal, rompen infraestructura, pueden perder datos, afectan pagos, seguridad, autenticacion global, storage, DB, IA/audio central o impiden observar errores.
- No enviar email: errores esperados de usuario, validaciones 4xx, datos incompletos, codigos incorrectos, cuentas no confirmadas, recursos no encontrados, rutas antiguas, permisos denegados normales, errores recuperables, errores repetidos y fallos parciales no bloqueantes.

Reglas anti-spam obligatorias para la siguiente fase:

- Dedupe por firma: `error_code + endpoint + provider + normalized_message`.
- Cooldown minimo recomendado: 15 minutos por firma critica.
- Escalado por volumen: un 4xx nunca envia email individual; si hay un pico anomalo, se muestra agregado en admin.
- Un fallo de proveedor externo envia email solo si afecta una operacion critica o supera reintentos.
- Los errores de frontend reportados al backend no deben disparar email por defecto; solo los crashes globales repetidos o errores que indiquen caida real de API.

## Errores que si deben enviar email inmediato al equipo dev

| Categoria | Condicion concreta | Codigos/archivos relacionados | Motivo |
|---|---|---|---|
| API no arranca | ImportError, dependencias faltantes, fallo inicial que impide levantar Flask/Gunicorn | `API/app.py` | Servicio completo caido |
| DB inaccesible | Credenciales invalidas, host caido, timeout, database missing | `db_connection.py`, `GENERIC_ERROR`, `DB_TABLE_MISSING` | Bloquea login, formulario, admin y chats |
| Tabla critica ausente | Tablas de usuarios, respuestas, finish form, logs, tickets, roles o permisos no existen | `DB_TABLE_MISSING` | Error de esquema/deploy que requiere accion |
| Corrupcion o fallo de escritura DB | Commit falla despues de operacion de negocio critica | rutas de registro, formulario, pago, tickets | Riesgo de datos inconsistentes |
| Secrets/AWS config rota | Secret no existe, JSON secreto invalido, credenciales AWS denegadas | `secrets_manager.py`, `INTERNAL_AWS_ERROR` | Rompe DB, Cognito, S3, SES o Stripe |
| Cognito/JWKS caido | No se puede obtener JWKS o Cognito rechaza operaciones masivamente | `require_auth_hybrid.py`, `refresh_token.py`, `INTERNAL_AWS_ERROR` | Usuarios no pueden autenticarse |
| Auth global inconsistente | Token valido no se puede validar para muchos usuarios, issuer/audience/kid roto | `require_auth_hybrid.py` | Bloquea todas las rutas protegidas |
| S3 critico caido | Bucket principal inaccesible, AccessDenied, NoCredentials, escritura/lectura de formulario/feedback falla | `buckets.py`, `S3_ERROR` | Puede bloquear formulario, IA y feedback |
| JSON S3 critico corrupto | Datos de formulario, feedback o dataset no parseables y sin fallback seguro | `buckets.py`, `admin/dataset/*.py` | Riesgo de perdida/bloqueo de datos |
| SES sistema caido | Credenciales/region/quota/config fallan de forma sistemica | `SES_EMAIL_ERROR`, `notifyer.py`, `reminders.py`, `recover_password.py` | Recovery, invitaciones y alertas no salen |
| Alertas dev no se pueden enviar | `notifyer.py` falla al notificar un error critico | `FIX_ACTION_FAILED`, `notifyer.py` | Se pierde observabilidad critica |
| Stripe falla | Payment intent, webhook, secret o firma/config falla fuera de errores esperados del cliente | `STRIPE_ERROR`, `stripe/*.py` | Impacto directo en pagos |
| Webhook Stripe no procesa evento valido | Firma valida pero DB/invitacion post-pago falla | `stripe/webhook.py` | Pago confirmado pero onboarding puede no crearse |
| IA principal falla | OpenAI/Nextbit caido, API key invalida, rate limit sostenido, respuesta no usable tras reintentos | `AI_ERROR`, `get_voice.py`, `reply_ai.py`, `OnoratoFarm/*` | Bloquea charla/dataset |
| TTS/STT proveedor falla | TTS/STT no disponible tras reintentos, no por audio invalido de usuario | `VOICE_GENERATION_ERROR`, `transcription.py` | Bloquea OnoratoFarm |
| Cron recordatorios rompe en lote | Ejecucion aborta, canal no soportado, AWS channel config rota, DB events inaccesible | `API/cron/cron_emails.py`, `cron_issue_logger.py` | Usuarios dejan de recibir recordatorios |
| Tickets no se guardan | Error DB al crear ticket o responder | `TICKET_DB_ERROR` | Soporte queda inutilizable |
| Logs frontend/backend no se guardan | Tabla logs ausente o escritura falla de forma sistemica | `frontend_logs.py`, `logs_view.py` | Se pierde trazabilidad |
| Error no clasificado 500 repetido | `GENERIC_ERROR` en endpoint critico, repetido o con stack no esperado | `error_handler.py` | Potencial bug de produccion |
| Seguridad/admin | Bypass, acceso admin indebido, fallo validando admin por error interno | `require_admin.py`, roles/permisos | Riesgo de seguridad |

## Errores informativos solo para admin panel

Estos errores se deben registrar, agrupar y mostrar en el panel admin, pero no deben enviar email individual.

| Categoria | Ejemplos | Motivo para no enviar email |
|---|---|---|
| Validacion de usuario | `MISSING_FIELDS`, email invalido, password debil, codigo invalido | Son errores esperados de input |
| Auth esperada | Token ausente/expirado, login incorrecto, cuenta no confirmada | Flujo normal de sesion/usuario |
| Limites de usuario | `LIMIT_EXCEEDED`, `TOO_MANY_ATTEMPTS` por usuario concreto | Puede ser normal; agregar si hay pico |
| Recurso inexistente | `USER_NOT_FOUND`, `TICKET_NOT_FOUND`, `NO_INVITATION`, 404 ruta | No requiere accion inmediata salvo volumen |
| Permisos denegados | Usuario no admin o sin permiso | Evento de negocio/seguridad informativo |
| Parametros invalidos | `INVALID_PARAMETER` por payload malo | Hoy tiene `notify_dev`; deberia ser admin-only salvo config rota |
| Audio invalido de usuario | `AUDIO_TOO_LARGE`, base64 corrupto, extension no soportada | El usuario puede corregir/reintentar |
| Feedback no disponible | `FEEDBACK_ACCESS_DENIED`, charla aun no habilitada | Regla de negocio esperada |
| Datos vacios | Sin stats, sin invitaciones, sin dataset todavia | Estado normal al inicio |
| SES por email individual | Email no verificado, address reject para un destinatario | Registrar destinatario; email dev solo si es sistemico |
| S3 key opcional ausente | Audio/frase/feedback opcional no existe y hay fallback | No bloquea el servicio |
| IA respuesta mala aislada | Respuesta vacia/no JSON una vez, recuperada por retry/fallback | No requiere despertar dev |
| Cron fallo parcial | Uno o pocos usuarios fallan pero el lote continua | Admin puede revisar pendientes |
| Endpoints historicos desalineados | Wrappers antiguos que generan 404 conocidos | Corregir en backlog; no alertar cada request |
| Logging de frontend WARN | Layout, parse localStorage, autoplay bloqueado, resize | Ruido de navegador/UX |

## Mapeo recomendado de AppError a canal

| Codigo | Canal recomendado | Nota |
|---|---|---|
| `AUTH_FAILED` | Admin panel | Email solo si hay pico global o validacion Cognito/JWKS rota |
| `USER_NOT_FOUND` | Admin panel | Informativo |
| `USER_NOT_CONFIRMED` | Admin panel | Informativo |
| `USER_EXISTS_CLOUD` | Admin panel | Informativo |
| `INVALID_CODE` | Admin panel | Informativo |
| `EXPIRED_CODE` | Admin panel | Informativo |
| `LIMIT_EXCEEDED` | Admin panel agregado | Email solo si afecta a muchos usuarios o proveedor bloquea globalmente |
| `TOO_MANY_ATTEMPTS` | Admin panel agregado | Posible abuso; email solo por volumen/anomalia |
| `WEAK_PASSWORD` | Admin panel | Informativo |
| `NEW_PASSWORD_REQUIRED` | Admin panel | Informativo |
| `PASSWORD_RESET_REQUIRED` | Admin panel | Informativo |
| `INVALID_PARAMETER` | Admin panel | Cambiar de `notify_dev` general a email solo en configuracion critica |
| `USER_LAMBDA_ERROR` | Email inmediato | Critico AWS/Cognito |
| `INTERNAL_AWS_ERROR` | Email inmediato | Critico si afecta provider/config |
| `MISSING_FIELDS` | Admin panel | Informativo |
| `AUDIO_TOO_LARGE` | Admin panel | Informativo |
| `INVALID_EMAIL` | Admin panel | Informativo |
| `NO_INVITATION` | Admin panel | Informativo |
| `FEEDBACK_ACCESS_DENIED` | Admin panel | Informativo |
| `USER_EXISTS_LOCAL` | Admin panel | Informativo |
| `STRIPE_ERROR` | Email inmediato | Pago critico |
| `INVALID_PAYMENT_DATA` | Admin panel | Informativo |
| `QUANTITY_EXCEEDED` | Admin panel | Informativo |
| `DUPLICATE_PURCHASE` | Admin panel | Informativo |
| `AI_ERROR` | Email inmediato si supera retry | Admin panel si es aislado y recuperado |
| `VOICE_GENERATION_ERROR` | Email inmediato si proveedor/servicio falla | Admin panel si es input/audio concreto |
| `S3_ERROR` | Email inmediato | Critico si afecta bucket principal |
| `TICKET_DB_ERROR` | Email inmediato | Soporte no puede guardar |
| `TICKET_NOT_FOUND` | Admin panel | Informativo |
| `SES_EMAIL_ERROR` | Email inmediato si sistemico | Admin panel si solo falla un destinatario |
| `DB_TABLE_MISSING` | Email inmediato | Esquema roto |
| `GENERIC_ERROR` | Email inmediato solo en 500 real/repetido | Admin panel si esta clasificado como no bloqueante |

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
- Separar canal de notificacion: `email_dev` solo para criticos; `admin_panel` para informativos.
- Revisar `INVALID_PARAMETER` porque hoy tiene `notify_dev` y puede spamear por payloads de usuario.
- Revisar `GENERIC_ERROR` porque hoy notifica siempre; deberia deduplicar y distinguir endpoint critico/no critico.
- No envolver `AppError` dentro de `Exception` generico.
- En cada `except Exception`, registrar contexto minimo: endpoint, user_id/email si existe, payload keys, proveedor externo, operacion.
- Para llamadas externas, separar `ClientError`, timeout, respuesta no JSON y status no 2xx.
- Para DB, separar `mysql.connector.Error` y detectar `errno` conocidos: auth, database missing, table missing, duplicate, FK.
- Para S3, separar `NoSuchKey`, `NoCredentialsError`, `ClientError AccessDenied`, JSON corrupto.
- Para IA/audio, separar timeout/rate limit/invalid output/audio invalido.
- Revisar endpoints frontend desalineados antes de tocar catch UI.
