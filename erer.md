# Plan de implementacion: sistema unificado de errores en MySQL

Fecha: 2026-05-14  
Estado: plan documental, sin cambios de codigo aplicados  
Alcance futuro: `Api_Onorato`, `form_frontend-2`, `admin_frontend-1`, cron y `OnoratoFarm`

## Objetivo

Implementar un sistema centralizado de errores, consultable desde MySQL y visible desde el admin panel, usando solo 2 tablas con nombres cortos, claros y en espanol:

- `ERRORES_TIPO`: catalogo maestro de errores posibles.
- `ERRORES_LOG`: errores reales ocurridos en usuarios, API, backend, frontend, cron, pipeline o proveedores externos.

La tabla de logs debe guardar toda la informacion posible sin crear columnas innecesarias. Para conseguirlo:

- Los datos que se filtran mucho van en columnas directas.
- Los datos variables o menos frecuentes van dentro de `contexto` como JSON.
- No se duplican datos que ya estan en `ERRORES_TIPO`, salvo cuando haga falta guardar el valor real del evento.
- Los errores criticos pueden mandar email al equipo dev.
- Los errores no criticos solo aparecen en el admin panel.
- Los logs con mas de 14 dias se eliminan automaticamente.

## Estado actual detectado

El proyecto ya tiene piezas parciales:

- `Api_Onorato/API/functions/errors/error.py`: define `AppError.CATALOGO`.
- `Api_Onorato/API/functions/errors/error_handler.py`: maneja `404`, `AppError` y excepciones genericas.
- `Api_Onorato/API/functions/errors/notifyer.py`: funcion para notificar al equipo dev por SES, actualmente con `return True` temporal para evitar spam.
- `Api_Onorato/API/routes/admin/frontend_logs.py`: guarda errores frontend en `FRONTEND_ERRORS_LOGS`.
- `Api_Onorato/database/schema/frontend_errors_logs.sql`: SQL de la tabla actual `FRONTEND_ERRORS_LOGS`.
- `Api_Onorato/API/functions/cron_issue_logger.py`: crea y usa `CRON_ISSUES_LOGS`.
- `form_frontend-2/functions/error_logger.js`: reporta errores frontend a `/logs/frontend_error`.
- `admin_frontend-1/src/pages/admin-panel/DeveloperLogs.jsx`: pantalla admin de logs.

Problemas actuales:

- No existe una tabla catalogo unica.
- Los errores frontend, cron y backend usan modelos distintos.
- `AppError` no persiste todos los eventos en MySQL.
- Algunas respuestas manuales con `jsonify({"error": ...})` no pasan por una capa comun.
- `INVALID_PARAMETER` no deberia generar email dev por defecto.
- `GENERIC_ERROR` podria spamear si no se agrupa por huella.
- El admin panel no lee una fuente unificada.

Decision:

- Reemplazo total como fuente activa.
- `ERRORES_TIPO` y `ERRORES_LOG` seran la fuente nueva.
- `FRONTEND_ERRORS_LOGS` y `CRON_ISSUES_LOGS` quedaran obsoletas despues de implementar el cambio.
- La limpieza automatica de logs con mas de 14 dias se hara con MySQL Event Scheduler.

## Modelo final de datos

### Tabla 1: `ERRORES_TIPO`

Catalogo maestro. Una fila por cada tipo de error reconocido por el sistema.

```sql
CREATE TABLE ERRORES_TIPO (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,

  codigo VARCHAR(120) NOT NULL UNIQUE,
  titulo VARCHAR(180) NOT NULL,
  descripcion TEXT NOT NULL,

  origen ENUM(
    'frontend',
    'backend',
    'api',
    'cron',
    'pipeline',
    'externo'
  ) NOT NULL,

  gravedad ENUM(
    'critico',
    'no_critico'
  ) NOT NULL DEFAULT 'no_critico',

  aviso ENUM(
    'panel',
    'email'
  ) NOT NULL DEFAULT 'panel',

  http SMALLINT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,

  creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_tipo_origen (origen),
  INDEX idx_tipo_gravedad (gravedad),
  INDEX idx_tipo_aviso (aviso),
  INDEX idx_tipo_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Campos:

- `id`: identificador interno.
- `codigo`: codigo estable del error, por ejemplo `AUTH_FAILED`, `S3_ERROR`, `FRONTEND_RENDER_CRASH`.
- `titulo`: nombre corto para el admin.
- `descripcion`: explicacion corta del error.
- `origen`: capa donde normalmente nace el error.
- `gravedad`: `critico` o `no_critico`.
- `aviso`: `panel` o `email`.
- `http`: status HTTP asociado si existe.
- `activo`: permite retirar errores antiguos sin borrar historico.
- `creado` y `actualizado`: auditoria minima del catalogo.

Campos eliminados respecto al primer borrador:

- `proveedor`: se mueve a `ERRORES_LOG.contexto` porque solo aplica a algunos errores.
- `usuario_puede_corregir`: se puede inferir desde `gravedad`, `http` y `descripcion`; si hiciera falta se anade al JSON de contexto del log.
- `canal_por_defecto` separado de `aviso`: `aviso` ya cumple esa funcion.
- `capa_fuente` separado de `origen`: `origen` ya cumple esa funcion.

### Tabla 2: `ERRORES_LOG`

Registro de errores reales. Cada fila representa una ocurrencia agrupada por `huella`. Si el mismo error ocurre varias veces, se incrementa `repeticiones` y se actualiza `visto_ultimo`.

```sql
CREATE TABLE ERRORES_LOG (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  uuid CHAR(36) NOT NULL UNIQUE,
  tipo_id BIGINT NOT NULL,

  gravedad ENUM(
    'critico',
    'no_critico'
  ) NOT NULL,

  origen ENUM(
    'frontend',
    'backend',
    'api',
    'cron',
    'pipeline',
    'externo'
  ) NOT NULL,

  aviso ENUM(
    'panel',
    'email'
  ) NOT NULL DEFAULT 'panel',

  usuario_id VARCHAR(80) NULL,
  email VARCHAR(255) NULL,

  ruta VARCHAR(500) NULL,
  metodo VARCHAR(12) NULL,
  http SMALLINT NULL,

  archivo VARCHAR(255) NULL,
  funcion VARCHAR(255) NULL,
  linea INT NULL,

  accion TEXT NULL,
  mensaje TEXT NOT NULL,
  stack MEDIUMTEXT NULL,
  contexto JSON NULL,

  huella CHAR(64) NOT NULL,
  repeticiones INT NOT NULL DEFAULT 1,
  visto_primero DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  visto_ultimo DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  resuelto TINYINT(1) NOT NULL DEFAULT 0,
  resuelto_por VARCHAR(255) NULL,
  resuelto_en DATETIME NULL,

  email_enviado TINYINT(1) NOT NULL DEFAULT 0,
  email_enviado_en DATETIME NULL,

  CONSTRAINT fk_log_tipo
    FOREIGN KEY (tipo_id)
    REFERENCES ERRORES_TIPO(id),

  UNIQUE KEY uniq_log_huella (huella),
  INDEX idx_log_visto (visto_ultimo),
  INDEX idx_log_tipo (tipo_id),
  INDEX idx_log_gravedad_aviso (gravedad, aviso, visto_ultimo),
  INDEX idx_log_email (email, visto_ultimo),
  INDEX idx_log_origen (origen, visto_ultimo),
  INDEX idx_log_resuelto (resuelto, visto_ultimo),
  INDEX idx_log_ruta (ruta(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Campos:

- `id`: identificador interno.
- `uuid`: identificador publico para soporte o admin.
- `tipo_id`: relacion con `ERRORES_TIPO.id`.
- `gravedad`: gravedad real del evento. Puede copiar la del tipo o sobrescribirse si el contexto lo exige.
- `origen`: lugar real donde ocurrio.
- `aviso`: `panel` o `email`, decidido por backend.
- `usuario_id`: id del usuario si existe.
- `email`: email del usuario si existe.
- `ruta`, `metodo`, `http`: contexto HTTP principal.
- `archivo`, `funcion`, `linea`: ubicacion tecnica principal.
- `accion`: que estaba haciendo el usuario o el proceso.
- `mensaje`: mensaje tecnico seguro.
- `stack`: stack trace completo si existe.
- `contexto`: JSON con informacion variable y reaprovechable.
- `huella`: hash para agrupar duplicados.
- `repeticiones`: numero de veces que se repitio ese mismo error.
- `visto_primero`: primera vez que se vio ese grupo.
- `visto_ultimo`: ultima vez que se repitio ese grupo.
- `resuelto`, `resuelto_por`, `resuelto_en`: gestion desde admin.
- `email_enviado`, `email_enviado_en`: control anti-spam.

### Uso de `contexto`

`contexto` evita llenar la tabla con columnas que solo se usan en casos concretos. Debe ser JSON seguro, sin passwords, tokens, secretos, audio completo, imagenes base64 completas ni datos sensibles innecesarios.

Ejemplo:

```json
{
  "sesion": "abc-123",
  "rol": "admin",
  "request_id": "req-123",
  "ip": "127.0.0.1",
  "user_agent": "Mozilla/5.0",
  "navegador": "Chrome",
  "dispositivo": "desktop",
  "idioma": "es-ES",
  "frontend_version": "1.4.0",
  "proveedor": "aws_s3",
  "proveedor_codigo": "AccessDenied",
  "payload": {
    "question_id": 15,
    "operation": "upload_audio"
  },
  "columna": 22,
  "extra": {
    "retry_count": 2,
    "timeout_ms": 30000
  }
}
```

Datos que van en columnas porque se filtran mucho:

- `gravedad`
- `aviso`
- `origen`
- `email`
- `ruta`
- `http`
- `archivo`
- `funcion`
- `linea`
- `resuelto`
- `visto_ultimo`

Datos que van en `contexto` porque no siempre existen:

- rol
- sesion
- request id
- ip
- user agent
- navegador
- dispositivo
- proveedor
- codigo del proveedor
- payload limpio
- columna frontend
- version frontend/backend
- retry count
- parametros tecnicos secundarios
- duracion de la operacion
- entorno
- trace id externo

## Retencion automatica de 14 dias

`ERRORES_TIPO` se conserva siempre.

`ERRORES_LOG` se elimina automaticamente cuando no se ha visto en mas de 14 dias. Se usa `visto_ultimo`, no `visto_primero`, para no borrar un error que sigue ocurriendo.

```sql
SET GLOBAL event_scheduler = ON;

CREATE EVENT IF NOT EXISTS limpiar_errores_log
ON SCHEDULE EVERY 1 DAY
DO
  DELETE FROM ERRORES_LOG
  WHERE visto_ultimo < (UTC_TIMESTAMP() - INTERVAL 14 DAY);
```

Requisito operativo:

- Confirmar en MySQL: `SHOW VARIABLES LIKE 'event_scheduler';`
- Si esta en `OFF`, activarlo en configuracion persistente de MySQL.

## Politica de gravedad y avisos

Regla base:

- `critico` + `email`: rompe API/backend/pipeline, compromete datos, impide una funcion central, afecta pagos, auth interna, base de datos, S3, SES, OpenAI/Nextbit o genera inconsistencia grave.
- `no_critico` + `panel`: errores esperados, validaciones, credenciales incorrectas, usuario no confirmado, limite de intentos, audio no soportado, permisos de navegador, 404 controlado, 400 controlado, avisos de negocio.

El frontend nunca decide enviar email. Solo envia una sugerencia. El backend decide el valor final de `aviso`.

Condiciones obligatorias para enviar email:

- `gravedad = 'critico'`
- `aviso = 'email'`
- No es un error esperado de usuario.
- No es un 400, 401, 403 o 404 funcional.
- No se ha enviado email recientemente para la misma `huella`.
- El error no se recupero automaticamente con retry.

Anti-spam:

- Agrupar por `huella`.
- Si ya existe la `huella`, incrementar `repeticiones` y actualizar `visto_ultimo`.
- Enviar email solo si `email_enviado = 0` o si `email_enviado_en` tiene mas de 15 minutos.
- Nunca mandar email por cada repeticion.

La `huella` se calcula con:

```text
codigo + origen + ruta + archivo + funcion + linea + mensaje_normalizado
```

## Catalogo inicial para `ERRORES_TIPO`

El seeder inicial debe incluir todos los codigos existentes de `AppError.CATALOGO` y los codigos nuevos de frontend/cron/pipeline.

### Backend/API

| codigo | gravedad | aviso | http | descripcion |
|---|---|---|---:|---|
| `AUTH_FAILED` | no_critico | panel | 401 | Credenciales incorrectas o contexto de usuario ausente |
| `USER_NOT_FOUND` | no_critico | panel | 404 | Usuario no existe |
| `USER_NOT_CONFIRMED` | no_critico | panel | 403 | Cuenta no confirmada |
| `USER_EXISTS_CLOUD` | no_critico | panel | 409 | Email ya existe en Cognito |
| `INVALID_CODE` | no_critico | panel | 400 | Codigo incorrecto |
| `EXPIRED_CODE` | no_critico | panel | 400 | Codigo caducado |
| `LIMIT_EXCEEDED` | no_critico | panel | 429 | Limite excedido por usuario o proveedor |
| `TOO_MANY_ATTEMPTS` | no_critico | panel | 429 | Demasiados intentos |
| `WEAK_PASSWORD` | no_critico | panel | 400 | Password no cumple politica |
| `NEW_PASSWORD_REQUIRED` | no_critico | panel | 403 | Cognito requiere nueva password |
| `PASSWORD_RESET_REQUIRED` | no_critico | panel | 403 | Password debe restablecerse |
| `INVALID_PARAMETER` | no_critico | panel | 400 | Parametros invalidos |
| `VALIDATION_ERROR` | no_critico | panel | 400 | Validacion de entrada fallida |
| `MISSING_REQUIRED_FIELD` | no_critico | panel | 400 | Falta un campo requerido |
| `NOT_FOUND` | no_critico | panel | 404 | Recurso no encontrado |
| `METHOD_NOT_ALLOWED` | no_critico | panel | 405 | Metodo HTTP no permitido |
| `USER_LAMBDA_ERROR` | critico | email | 500 | Fallo interno Cognito/Lambda |
| `INTERNAL_AWS_ERROR` | critico | email | 500 | Fallo critico AWS |
| `DB_CONNECTION_ERROR` | critico | email | 500 | No se puede conectar a MySQL |
| `DB_QUERY_ERROR` | critico | email | 500 | Query SQL falla de forma inesperada |
| `DB_TABLE_MISSING` | critico | email | 500 | Tabla necesaria no existe |
| `DB_MIGRATION_PENDING` | critico | email | 500 | Falta migracion o schema requerido |
| `S3_ERROR` | critico | email | 500 | Error critico S3 |
| `SES_ERROR` | critico | email | 500 | Error critico enviando email |
| `STRIPE_ERROR` | critico | email | 500 | Error critico Stripe |
| `AI_ERROR` | critico | email | 500 | Error critico IA |
| `GENERIC_ERROR` | critico | email | 500 | Excepcion no controlada |

### Frontend publico y admin

| codigo | gravedad | aviso | descripcion |
|---|---|---|---|
| `FRONTEND_RENDER_CRASH` | critico | panel | React rompe render o ErrorBoundary captura fallo |
| `FRONTEND_JS_CRASH` | critico | panel | Error JS no capturado |
| `FRONTEND_PROMISE_CRASH` | critico | panel | Promise rechazada no capturada |
| `FRONTEND_API_5XX` | critico | panel | API devuelve 5xx |
| `FRONTEND_API_NETWORK` | no_critico | panel | Red caida, timeout cliente o navegador offline |
| `FRONTEND_API_4XX` | no_critico | panel | Respuesta 4xx esperada o funcional |
| `FRONTEND_AUTH_MISSING` | no_critico | panel | Falta token o sesion local |
| `FRONTEND_FORM_VALIDATION` | no_critico | panel | Validacion local del formulario |
| `FRONTEND_AUDIO_PERMISSION` | no_critico | panel | Usuario deniega microfono |
| `FRONTEND_AUDIO_UNSUPPORTED` | no_critico | panel | Navegador no soporta API de audio |
| `FRONTEND_MEDIA_ERROR` | no_critico | panel | Error local de reproduccion/grabacion |
| `FRONTEND_STORAGE_ERROR` | no_critico | panel | localStorage/sessionStorage no disponible |
| `FRONTEND_ROUTE_ERROR` | no_critico | panel | Ruta frontend invalida |
| `FRONTEND_ADMIN_LOAD_ERROR` | no_critico | panel | Admin no puede cargar una vista secundaria |
| `FRONTEND_ADMIN_MUTATION_ERROR` | no_critico | panel | Accion admin falla de forma controlada |

Nota: los errores frontend criticos se quedan en `panel` por defecto para no spamear. Si el backend detecta que el fallo frontend corresponde a un 5xx real propio, el email lo genera el backend por el error de API, no el navegador.

### Cron, pipeline y proveedores

| codigo | gravedad | aviso | descripcion |
|---|---|---|---|
| `CRON_JOB_FAILED` | critico | email | Job programado falla completamente |
| `CRON_JOB_PARTIAL` | no_critico | panel | Job termina con incidencias parciales |
| `PIPELINE_BATCH_FAILED` | critico | email | Pipeline batch no puede continuar |
| `PIPELINE_ITEM_FAILED` | no_critico | panel | Item individual del pipeline falla |
| `OPENAI_PROVIDER_ERROR` | critico | email | OpenAI falla en una funcion central |
| `NEXTBIT_PROVIDER_ERROR` | critico | email | Nextbit/Mistral falla en una funcion central |
| `AWS_COGNITO_ERROR` | critico | email | Cognito falla internamente |
| `AWS_S3_ERROR` | critico | email | S3 falla internamente |
| `AWS_SES_ERROR` | critico | email | SES falla internamente |
| `STRIPE_PROVIDER_ERROR` | critico | email | Stripe falla internamente |
| `MYSQL_PROVIDER_ERROR` | critico | email | MySQL falla internamente |

## Payload frontend propuesto

El frontend debe enviar poco en columnas directas y el resto en `contexto`.

```json
{
  "codigo": "FRONTEND_RENDER_CRASH",
  "gravedad_sugerida": "critico",
  "origen": "frontend",
  "aviso_sugerido": "panel",
  "usuario_id": "123",
  "email": "user@example.com",
  "ruta": "/onorato-farm",
  "metodo": "GET",
  "http": null,
  "archivo": "OnoratoFarm.jsx",
  "funcion": "fetchLLMResponse",
  "linea": 298,
  "accion": "Usuario envio mensaje al chat IA",
  "mensaje": "Cannot read properties of undefined",
  "stack": "Error stack...",
  "contexto": {
    "columna": 22,
    "navegador": "Chrome",
    "dispositivo": "desktop",
    "idioma": "es-ES",
    "sesion": "abc-123",
    "payload": {
      "safe": true
    }
  }
}
```

Reglas:

- El frontend no manda `tipo_id`.
- El frontend manda `codigo`.
- El backend busca `ERRORES_TIPO.codigo`.
- Si el codigo no existe, se registra como `GENERIC_ERROR` o `FRONTEND_JS_CRASH`, segun origen.
- El backend decide `gravedad` y `aviso` finales.

## Registro backend propuesto

Funcion central futura:

```python
registrar_error(
    codigo="S3_ERROR",
    gravedad="critico",
    origen="backend",
    aviso="email",
    usuario_id=getattr(g, "user_id", None),
    email=getattr(g, "email", None),
    ruta=request.path,
    metodo=request.method,
    http=500,
    archivo="buckets.py",
    funcion="get_json_from_bucket",
    linea=None,
    accion="Leer JSON desde S3",
    mensaje=str(exc),
    stack=traceback.format_exc(),
    contexto={
        "proveedor": "aws_s3",
        "proveedor_codigo": "AccessDenied",
        "bucket": bucket_name,
        "key": safe_key
    }
)
```

La funcion debe:

1. Buscar `codigo` en `ERRORES_TIPO`.
2. Si no existe, usar `GENERIC_ERROR`.
3. Calcular `huella`.
4. Insertar una nueva fila o actualizar la existente por `huella`.
5. Incrementar `repeticiones` si ya existe.
6. Actualizar `visto_ultimo`.
7. Decidir si toca email.
8. Enviar email solo si cumple politica anti-spam.
9. Marcar `email_enviado` y `email_enviado_en`.

## Plan backend

Crear `Api_Onorato/API/functions/errores_log.py`.

Funciones:

- `asegurar_tablas_errores()`
- `sembrar_errores_tipo()`
- `obtener_tipo_error(codigo)`
- `registrar_error(...)`
- `crear_huella(...)`
- `debe_enviar_email(log)`
- `marcar_email_enviado(id)`
- `listar_errores(filtros)`
- `obtener_error(id)`
- `resolver_error(id, resuelto_por)`

Integraciones:

- `API/functions/errors/error.py`
  - Mantener `AppError.CATALOGO`.
  - Mapear sus codigos a `ERRORES_TIPO`.
  - No duplicar catalogos manuales.

- `API/functions/errors/error_handler.py`
  - En `AppError`, llamar a `registrar_error`.
  - En excepcion generica, registrar `GENERIC_ERROR`.
  - En `404`, registrar solo si conviene para admin, sin email.

- `API/routes/admin/frontend_logs.py`
  - `save_frontend_error()` debe insertar en `ERRORES_LOG`.
  - La respuesta debe mantener compatibilidad con el frontend actual.
  - Las lecturas admin deben consultar `ERRORES_LOG WHERE origen='frontend'`.

- `API/functions/cron_issue_logger.py`
  - Reemplazar escritura en `CRON_ISSUES_LOGS` por `registrar_error(origen='cron')`.
  - Mantener compatibilidad temporal si algun endpoint antiguo lo necesita.

- `API/functions/errors/notifyer.py`
  - Quitar el `return True` temporal solo cuando el anti-spam este implementado.
  - Recibir datos del log ya agrupado.
  - Enviar email solo para `aviso='email'`.

Endpoints admin futuros:

- `GET /admin/errors/tipos`
- `GET /admin/errors/logs`
- `GET /admin/errors/logs/<int:id>`
- `PUT /admin/errors/logs/<int:id>/resolver`

Filtros necesarios:

- `origen`
- `gravedad`
- `aviso`
- `codigo`
- `email`
- `ruta`
- `resuelto`
- `desde`
- `hasta`

## Plan frontend publico

Actualizar `form_frontend-2/functions/error_logger.js` para enviar el payload nuevo.

Capturar:

- ErrorBoundary de React.
- `window.onerror`.
- `window.onunhandledrejection`.
- Fallos de API wrappers.
- Fallos de audio/microfono.
- Fallos de localStorage/sessionStorage.
- Ruta actual.
- Accion del usuario cuando sea posible.

Reglas:

- No enviar secrets.
- No enviar tokens.
- No enviar audio/base64 completo.
- No enviar passwords.
- Truncar `stack` si es demasiado grande.
- Mandar `contexto.payload` solo con datos seguros.

## Plan admin frontend

Actualizar `admin_frontend-1/src/pages/admin-panel/DeveloperLogs.jsx` o el componente equivalente para usar `ERRORES_LOG`.

Vista lista:

- Fecha ultima: `visto_ultimo`.
- Codigo: `ERRORES_TIPO.codigo`.
- Titulo: `ERRORES_TIPO.titulo`.
- Gravedad.
- Aviso.
- Origen.
- Email usuario.
- Ruta.
- Archivo/funcion/linea.
- Repeticiones.
- Estado resuelto.
- Email enviado.

Vista detalle:

- Mensaje.
- Stack.
- Contexto JSON formateado.
- Accion.
- Datos HTTP.
- Historial de repeticiones.
- Boton resolver.

Filtros:

- Criticos sin resolver.
- Solo emails enviados.
- Por usuario.
- Por origen.
- Por ruta.
- Por codigo.
- Ultimas 24 horas.
- Ultimos 7 dias.

## Migracion

Estrategia recomendada: reemplazo total.

Pasos:

1. Crear `ERRORES_TIPO`.
2. Crear `ERRORES_LOG`.
3. Sembrar catalogo inicial.
4. Crear indices.
5. Crear evento `limpiar_errores_log`.
6. Adaptar backend para escribir en `ERRORES_LOG`.
7. Adaptar endpoint frontend logs.
8. Adaptar admin panel.
9. Dejar `FRONTEND_ERRORS_LOGS` y `CRON_ISSUES_LOGS` como legado temporal.
10. Eliminar o ignorar tablas antiguas cuando se confirme estabilidad.

No migrar historico antiguo es aceptable si se quiere evitar complejidad, porque la nueva retencion es de 14 dias. Si se quiere preservar historico reciente, migrar solo las ultimas 2 semanas.

## Consultas SQL para admin panel

### Ultimos errores

```sql
SELECT
  l.id,
  l.uuid,
  t.codigo,
  t.titulo,
  l.gravedad,
  l.origen,
  l.aviso,
  l.email,
  l.ruta,
  l.archivo,
  l.funcion,
  l.linea,
  l.repeticiones,
  l.email_enviado,
  l.resuelto,
  l.visto_ultimo
FROM ERRORES_LOG l
JOIN ERRORES_TIPO t ON t.id = l.tipo_id
ORDER BY l.visto_ultimo DESC
LIMIT 100;
```

### Criticos sin resolver

```sql
SELECT *
FROM ERRORES_LOG
WHERE gravedad = 'critico'
  AND resuelto = 0
ORDER BY visto_ultimo DESC;
```

### Errores por usuario

```sql
SELECT *
FROM ERRORES_LOG
WHERE email = ?
ORDER BY visto_ultimo DESC;
```

### Errores mas repetidos

```sql
SELECT
  t.codigo,
  t.titulo,
  l.origen,
  l.ruta,
  SUM(l.repeticiones) AS total,
  MAX(l.visto_ultimo) AS ultimo
FROM ERRORES_LOG l
JOIN ERRORES_TIPO t ON t.id = l.tipo_id
GROUP BY t.codigo, t.titulo, l.origen, l.ruta
ORDER BY total DESC
LIMIT 50;
```

### Emails enviados

```sql
SELECT *
FROM ERRORES_LOG
WHERE email_enviado = 1
ORDER BY email_enviado_en DESC;
```

### Resolver error

```sql
UPDATE ERRORES_LOG
SET
  resuelto = 1,
  resuelto_por = ?,
  resuelto_en = UTC_TIMESTAMP()
WHERE id = ?;
```

## Pruebas de aceptacion

Backend:

- `python -m py_compile` en archivos modificados.
- Error `AppError` no critico crea log con `aviso='panel'`.
- Error `DB_TABLE_MISSING` crea log con `gravedad='critico'` y `aviso='email'`.
- Excepcion generica crea `GENERIC_ERROR`.
- Dos errores iguales incrementan `repeticiones`.
- No se manda email mas de una vez dentro del cooldown.
- Endpoint frontend guarda en `ERRORES_LOG`.
- Resolver error actualiza `resuelto`, `resuelto_por`, `resuelto_en`.

MySQL:

- FK entre `ERRORES_LOG.tipo_id` y `ERRORES_TIPO.id`.
- Indices creados.
- Seeder idempotente.
- Evento `limpiar_errores_log` activo.
- Se borra solo `ERRORES_LOG`, nunca `ERRORES_TIPO`.

Frontend publico:

- `npm run lint`.
- `npm run build`.
- ErrorBoundary reporta.
- `unhandledrejection` reporta.
- Fallo API reporta sin tokens.
- Audio denegado reporta no critico.

Admin:

- `npm run lint`.
- `npm run build`.
- Lista muestra logs.
- Filtros funcionan.
- Detalle muestra `contexto`.
- Resolver funciona.
- No hay textos largos rompiendo la UI.

## Criterios de aceptacion

- Solo existen 2 tablas activas para el sistema nuevo: `ERRORES_TIPO` y `ERRORES_LOG`.
- Los nombres de tablas y columnas son cortos, claros y en espanol.
- Todo error nuevo apunta a un tipo de `ERRORES_TIPO`.
- Todo error real queda en `ERRORES_LOG`.
- Los datos variables se guardan en `contexto`, no en columnas sueltas innecesarias.
- Los errores criticos pueden enviar email.
- Los errores no criticos solo aparecen en panel.
- Existe deduplicacion por `huella`.
- Existe anti-spam por `email_enviado_en`.
- El admin puede listar, filtrar, ver detalle y resolver.
- Los logs se eliminan automaticamente tras 14 dias sin actividad.

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Spam de emails | `huella`, `repeticiones`, cooldown de 15 minutos |
| Demasiadas columnas | Usar `contexto` JSON para datos variables |
| Falta de informacion para depurar | Columnas directas para lo esencial + `contexto` completo seguro |
| Datos sensibles en logs | Sanitizador obligatorio antes de insertar |
| Errores sin catalogo | Fallback a `GENERIC_ERROR` o `FRONTEND_JS_CRASH` |
| Duplicados excesivos | `huella` unica e incremento de `repeticiones` |
| Admin lento | Indices por `visto_ultimo`, `gravedad`, `aviso`, `origen`, `email`, `resuelto` |
| Perder errores activos por limpieza | Borrar por `visto_ultimo`, no por `visto_primero` |

## Resumen final de diseno

- `ERRORES_TIPO`: que error es, como se llama, de donde viene normalmente, gravedad por defecto y si avisa por email.
- `ERRORES_LOG`: que error ocurrio, a quien, donde, cuando, que hacia, cuantas veces paso y si ya se resolvio.
- `contexto`: celda reutilizable para todo lo variable.
- `huella`: evita duplicados y spam.
- `aviso='email'`: solo criticos reales.
- `aviso='panel'`: informativos o no criticos.
- Retencion: 14 dias desde `visto_ultimo`.
