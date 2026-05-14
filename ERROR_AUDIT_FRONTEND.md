# Auditoria de errores frontend

Fecha: 2026-05-14  
Alcance: `form_frontend-2/` y `admin_frontend-1/`  
Objetivo: documentar errores posibles y todos los puntos `catch`/`.catch` antes de modificar codigo.

## Resumen ejecutivo

Hay dos modelos de error distintos:

- Frontend publico (`form_frontend-2`): tiene telemetria propia con `reportErrorToAdmin`, `window.onerror`, `window.onunhandledrejection`, `ErrorBoundary`, evento `frontend-silent-error` y evento `session-expired`.
- Frontend admin (`admin_frontend-1`): tiene wrapper API con normalizacion basica, `ErrorProvider` escuchando `api_global_error`, y redireccion por `session-expired`, pero no tiene `window.onerror`, `onunhandledrejection` ni `ErrorBoundary` equivalente al publico.

Inventario por busqueda en codigo propio:

- Ambos frontends: 105 `catch` o `.catch`.
- `form_frontend-2`: 100+ llamadas/ocurrencias de `reportErrorToAdmin` distribuidas en API, paginas, componentes de preguntas y OnoratoFarm.
- `admin_frontend-1`: no usa `reportErrorToAdmin`; muestra errores localmente o con `ErrorProvider`.

## Arquitectura de errores del frontend publico

| Capa | Archivo | Que captura | Que hace |
|---|---|---|---|
| Global JS crash | `src/main.jsx:14` | `window.onerror` | Reporta a `/logs/frontend_error` y dispara toast silencioso |
| Promise crash | `src/main.jsx:26` | `window.onunhandledrejection` | Reporta rechazo no controlado y dispara toast |
| Render crash | `src/components/panels/error_show.jsx:75` | ErrorBoundary React | Muestra modal con `errorId` y opcion recargar/cerrar |
| Toast global | `src/App.jsx:19` | `frontend-silent-error` | Muestra aviso no intrusivo |
| Sesion expirada | `src/App.jsx:54` | `session-expired` | Limpia tokens y navega a `/login` |
| API central | `functions/api_functions.js:169` | HTTP, 401, parsing, retry refresh | Reporta errores API, refresca token, lanza `Error` enriquecido |
| Telemetria | `functions/error_logger.js:11` | Errores reportados manualmente | Dedup 30s, enriquece contexto y POST `/logs/frontend_error` |

## Arquitectura de errores del frontend admin

| Capa | Archivo | Que captura | Que hace |
|---|---|---|---|
| API central | `functions/api_functions.js:26` | HTTP no ok, JSON invalido, red | Lanza `Error` con `status`, `solution`, `error_code`, `error_id` |
| Sesion expirada | `src/App.jsx:17` | `session-expired` | Limpia tokens y navega a `/admin/login` |
| ErrorProvider | `src/context/ErrorProvider.jsx:4` | `api_global_error` | Muestra `ErrorDisplay` durante 8s |
| ErrorDisplay | `src/components/ErrorDisplay.jsx` | Error visual | Mensaje, solucion, codigo, copiar `error_id` |
| ErrorTerminal | `src/components/ErrorTerminal.jsx:18` | Fetch logs frontend | `console.error`, no telemetria |

Riesgo admin: el wrapper no emite `api_global_error`, asi que `ErrorProvider` solo sirve si algun componente emite ese evento manualmente.

## Errores posibles por familia

| Familia | Errores posibles | Criticidad |
|---|---|---|
| Config/Vite | `VITE_API_BASE_URL` ausente, URL con slash incorrecto, CORS, build env distinto | Critico si apunta mal |
| Red/API | Backend caido, DNS, CORS, timeout, offline, status 5xx, respuesta HTML/no JSON | Critico |
| Auth/sesion | Token ausente, id_token/access_token mezclados, refresh_token ausente, token expirado, reloj cliente desfasado | Critico |
| Storage local | `localStorage` bloqueado, JSON de usuario corrupto, tokens inconsistentes | Medio/critico |
| Contrato API | Endpoint inexistente, payload distinto, campo `message/error/solution` inconsistente, `noJson` mal usado | Critico |
| Render React | Error en render, lazy import falla, props undefined, mapas sobre `undefined` | Critico si no boundary |
| Formularios | Validacion incompleta, dependencias rotas, tipo pregunta no soportado, respuesta no serializable | Medio/critico |
| i18n | Key ausente, idioma no soportado, traducciones no pares | Bajo/medio |
| Audio | Permiso micro denegado, dispositivo ausente, MediaRecorder no soportado, blob pequeno, autoplay bloqueado, base64 invalido | Critico en OnoratoFarm |
| 3D | Modelo no carga, WebGL no disponible, canvas vacio, resize | Medio/critico UX |
| Fechas/horas | Parse invalido, timezone, formato 12h/24h | Medio |
| Dataset admin | Respuesta IA vacia, JSON parse, chat history corrupto, save falla | Medio/critico admin |
| Tickets/admin | Endpoints no registrados, FormData/JSON mismatch | Critico para soporte |
| Observabilidad | Fallo al reportar errores, spam prevention oculta repetidos, tabla backend faltante | Medio |

## Contrato API y endpoints con riesgo

Comparado contra `Api_Onorato/API/app.py`.

| Frontend | Wrapper | Endpoint llamado | Estado |
|---|---|---|---|
| Publico | `deleteProfile` | `DELETE /user/delete` | No registrado |
| Publico | `checkPassword` | `POST /recover/check` | No registrado; backend usa `/recover/password` |
| Publico | `generateForm` | `GET /questions/generate` | No registrado; backend usa `/questions/generate_form` |
| Publico | `getUsers` | `GET /admin/users` | No registrado |
| Publico | `getUserFormStatus` | `GET /admin/users/{id}/status` | No registrado |
| Publico | `deleteUser` | `DELETE /admin/users/{id}` | No registrado |
| Admin | `deleteProfile` | `DELETE /user/delete` | No registrado |
| Admin | `getTicketMessages` | `GET /tickets/{id}/messages` | No registrado en `app.py` |
| Admin | `addReply` | `POST /tickets/reply` | No registrado en `app.py` |
| Admin | `closeTicket` | `PUT /tickets/{id}/status` | No registrado en `app.py` |

Estos son errores funcionales de API aunque no siempre aparezcan como excepcion JS: acaban en `404 NOT_FOUND`, redireccion o UI sin datos.

## Inventario de catches: frontend publico

Resultado de `rg -n "catch\\s*\\(|\\.catch\\(" form_frontend-2`.

| Archivo | Num. catches | Errores cubiertos |
|---|---:|---|
| `functions/api_functions.js` | 2 | Parse error HTTP y `checkUserPermissions` |
| `functions/error_logger.js` | 1 | Fallo transporte logging |
| `functions/permisions.js` | 1 | Permisos |
| `src/main.jsx` | global handlers | `window.onerror`, `onunhandledrejection` |
| `src/App.jsx` | eventos | `frontend-silent-error`, `session-expired` |
| `src/pages/Login.jsx` | 4 | Verificacion, login password, login email, codigo email |
| `src/pages/Register.jsx` | 7 | Guardar respuestas, fetch preguntas, verificacion, login post-register, resend, submit |
| `src/pages/RecoverPassword.jsx` | 2 | Envio recovery, cambio password |
| `src/pages/VerifyPage.jsx` | 1 | Verificacion por URL |
| `src/pages/FormPage.jsx` | 2 | Check finish/form data y carga flujo |
| `src/pages/FormComponent.jsx` | 4 | Submit final, loadForm, loadData, saveQuestionsAsync |
| `src/components/questions/add_option.jsx` | 1 | Parse valor dinamico |
| `src/components/questions/check.jsx` | 1 | Parse checkbox |
| `src/components/questions/date.jsx` | 1 | Parse fecha |
| `src/components/questions/hour.jsx` | 1 | Confirmar hora |
| `src/components/questions/little_text.jsx` | 1 | Layout/resize input |
| `src/components/questions/radio.jsx` | 1 | Layout radio |
| `src/components/questions/select.jsx` | 1 | Label select |
| `src/components/questions/buttons/AskOnoratoButton.jsx` | 1 | Click ask |
| `src/components/questions/buttons/BanQuestionButton.jsx` | 1 | Click ban |
| `src/components/panels/notify.jsx` | 2 | Pregunta activa/respondida |
| `src/components/panels/temporalPassword.jsx` | 1 | Submit password temporal |
| `src/components/panels/user.jsx` | 1 | Logout |
| `src/components/others/SlideBar.jsx` | 1 | Logout |
| `src/components/others/OnboardingV2/Onboarding.jsx` | 1 | Cerrar onboarding |
| `src/pages/onoratoFarm/OnoratoFarm.jsx` | 9 | Audios soporte, bucket, estado charla, user info, finish/review/shipping |
| `src/pages/onoratoFarm/ThirdPage.jsx` | 10 | Base64 audio, TTS, LLM retry, preload, repeat fallback, playback/autoplay |
| `src/pages/onoratoFarm/FourPage.jsx` | 6 | MediaRecorder, getUserMedia, transcripcion, start/stop mic |
| `src/pages/onoratoFarm/QuestionPage.jsx` | 1 | Generar respuesta pregunta |
| `src/pages/onoratoFarm/SevenPage.jsx` | 1 | Promise catch silencioso |
| `src/pages/onoratoFarm/components/ReportPage.jsx` | 1 | Crear ticket/reporte |
| `src/pages/onoratoFarm/OnoratoFarmAntiguo.jsx` | 1 | Flujo antiguo no principal |

Puntos sin catch explicito pero cubiertos globalmente:

- Errores de render bajo `ErrorBoundary`.
- Rechazos de promesa no capturados por `window.onunhandledrejection`.
- Crashes sincronos por `window.onerror`.

## Inventario de catches: frontend admin

Resultado de `rg -n "catch\\s*\\(|\\.catch\\(" admin_frontend-1`.

| Archivo | Num. catches | Errores cubiertos |
|---|---:|---|
| `functions/api_functions.js` | 2 | JSON invalido de respuesta y red/API |
| `functions/permisions.js` | 1 | Permisos |
| `src/components/ErrorTerminal.jsx` | 1 | Fetch logs frontend |
| `src/pages/admin-panel/AdminLogin.jsx` | 3 | Login password/email/code |
| `src/pages/admin-panel/DashboardStats.jsx` | 1 | Carga stats |
| `src/pages/admin-panel/DatasetManager.jsx` | 4 | Parse JSON inline, perfiles/dataset, respuesta IA, save |
| `src/pages/admin-panel/DependencyManager.jsx` | 1 | Guardar dependencias |
| `src/pages/admin-panel/DeveloperLogs.jsx` | 2 | Carga/borrado logs |
| `src/pages/admin-panel/InfoDebug.jsx` | 1 | Carga debug |
| `src/pages/admin-panel/QuestionManager.jsx` | 6 | Cargar, crear, actualizar, eliminar, dependencias, orden |
| `src/pages/admin-panel/TicketManager.jsx` | 5 | Cargar tickets, mensajes, crear, responder, cerrar |
| `src/pages/admin-panel/UserManager.jsx` | 10 | Carga usuarios/stats/invitaciones, reminders, delete, bulk invite |

## Errores criticos por pantalla publica

| Pantalla/componente | Error critico | Tratamiento actual |
|---|---|---|
| `Login.jsx` | Backend caido, credenciales invalidas, cuenta no confirmada, codigo email invalido | Catch local + `reportErrorToAdmin`; diferencia WARN/ERROR |
| `Register.jsx` | Invitacion invalida, usuario duplicado, password debil, fallo guardar onboarding | Catch local + reporte |
| `RecoverPassword.jsx` | Email inexistente, codigo invalido/caducado, password rechazada | Catch local + reporte |
| `FormPage.jsx` | No puede consultar estado de formulario o feedback | Catch local |
| `FormComponent.jsx` | No carga preguntas, no guarda respuestas, no envia formulario, dependencias corruptas | Catch local + reporte |
| Preguntas `L/C/R/S/D/A/H` | Parse de valor invalido, layout/resize falla, fecha/hora invalida | Catch WARN |
| `OnoratoFarm.jsx` | No carga preguntas S3, no carga audios, no comprueba finish, no obtiene usuario | Catch + reporte |
| `ThirdPage.jsx` | LLM no responde, TTS falla, audio base64 invalido, autoplay bloqueado | Retry + catch + reporte |
| `FourPage.jsx` | Micro denegado, MediaRecorder no soportado, audio insuficiente, STT falla | Catch + reporte |
| `ReportPage.jsx` | No crea ticket | Catch + reporte |
| Global | Crash render/runtime | Boundary/global listeners + telemetria |

## Errores criticos por pantalla admin

| Pantalla | Error critico | Tratamiento actual |
|---|---|---|
| `AdminLogin.jsx` | Login falla, codigo email invalido, sesion no guardada | Catch local |
| `DashboardStats.jsx` | Stats no cargan | Catch local |
| `UserManager.jsx` | Usuarios, invitaciones, recordatorios o borrado fallan | Catch local; muchos puntos |
| `QuestionManager.jsx` | CRUD preguntas/dependencias falla | Catch local |
| `DatasetManager.jsx` | Profiles/dataset/IA/save fallan | Catch local |
| `TicketManager.jsx` | Endpoints ticket no registrados o fallan | Catch local |
| `DeveloperLogs.jsx` | No se leen/borran logs | Catch local |
| Global admin | Crash render/runtime | No hay ErrorBoundary ni `window.onerror` en admin |

## Errores minimos/no criticos que tambien hay que tratar

- `JSON.parse` de valores de preguntas guardados como string.
- `atob` de JWT malformado en publico.
- `URLSearchParams` con parametros inesperados en logger.
- `navigator.clipboard.writeText` puede fallar en admin `ErrorDisplay`.
- `audio.play()` puede fallar por politica de autoplay.
- `setTimeout` de toasts sobre componente desmontado puede generar warnings.
- `localStorage.getItem('user')` con JSON corrupto ya se ignora en logger publico.
- `res.json()` de admin puede fallar y devuelve `{ message: 'Respuesta invalida del servidor', error_code: 'BAD_GATEWAY' }`.
- `noJson=true` devuelve `Response`; consumidores deben convertir blob/text correctamente.
- Errores de lazy imports en publico pueden caer en ErrorBoundary, pero no siempre se reportan con detalle de chunk.
- Falta de soporte de `MediaRecorder`, `getUserMedia`, WebGL o permisos bloqueados por navegador.

## Riesgos de normalizacion actuales

| Riesgo | Detalle |
|---|---|
| Tokens inconsistentes | Publico lee `id_token` como token principal, admin lee `access_token`. Backend acepta Cognito/legacy, pero la mezcla puede producir 401 intermitentes. |
| Refresh parcial | Publico refresca si expira pronto; admin no refresca tokens. |
| Evento admin no usado | `api_global_error` existe, pero wrapper admin no lo dispara. |
| Telemetria solo publica | Admin no reporta errores frontend a `/logs/frontend_error`. |
| Formatos backend mixtos | Frontends reciben `message`, `error`, `solution`, `error_code`, `status`, segun ruta. |
| Endpoints desalineados | Algunos wrappers llaman rutas no registradas y convierten problemas de contrato en errores de usuario. |
| Catch silencioso | Varios `.catch(() => {})` evitan recursion/log spam, pero pueden ocultar fallos reales de audio/logging. |

## Recomendaciones para la siguiente fase

No se ha escrito codigo en esta fase. Cuando se actualicen catches:

- Crear una matriz comun de errores frontend: `NETWORK`, `AUTH`, `VALIDATION`, `API_4XX`, `API_5XX`, `PARSE`, `MEDIA`, `AUDIO`, `RENDER`, `UNKNOWN`.
- Publico: mantener `reportErrorToAdmin`, pero evitar reportar como `ERROR` los 400/401/403/404 esperados.
- Admin: decidir si se añade telemetria igual que publico o si se dispara `api_global_error` desde el wrapper.
- Corregir primero endpoints desalineados; si no, los catches ocultaran errores reales de contrato.
- En cada catch local, guardar contexto util: pantalla, accion, endpoint/wrapper, payload keys, user/session/version, browser media support.
- Diferenciar errores recuperables de errores bloqueantes: retry/backoff para red/audio/IA; mensaje claro para validacion.
- Revisar todos los `.catch(() => {})` y documentar cuales deben seguir silenciosos.
- Evitar que errores de logging generen nuevos errores de logging.
- Hacer paridad de mensajes entre `es/translation.json` y `en/translation.json` si se muestran nuevos errores.
