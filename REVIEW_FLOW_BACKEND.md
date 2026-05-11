# Flujo de Revision de Preguntas (Backend)

Documentacion completa de los endpoints, funciones y logica de S3/DB que soportan el flujo de revision y repeticion de preguntas en OnoratoFarm.

---

## Resumen de Endpoints Involucrados

| Endpoint | Metodo | Funcion | Archivo |
|----------|--------|---------|---------|
| `/bucket/get` | POST | Obtener feedback desde S3 | `buckets.py:159` → `get_json_from_bucket()` |
| `/onorato_farm/feedback` | POST | Guardar nueva respuesta (mode:create) | `app.py:432` → `receive_feedback()` |
| `/onorato_farm/feedback/replace` | POST | Reemplazar respuesta existente (mode:replace) | `app.py:437` → inline handler |
| `/onorato_farm/is_finish` | POST | Consultar si sesion esta finalizada | `app.py:486` → `manage_progres.getisFinish()` |
| `/onorato_farm/set_finish` | POST | Marcar sesion como finalizada | `app.py:492` → `manage_progres.finish_chat()` |

Todos los endpoints estan protegidos con `@require_auth_hybrid`.

---

## Estructura S3

```
{bucket_name}/
└── {user_id}/
    ├── {user_id}_form.json              ← Formulario inicial
    └── feedback_user/
        ├── charla_1.json                ← Feedback sesion 1
        ├── charla_2.json                ← Feedback sesion 2 (restringida)
        └── {user_id}_v1.json            ← Formato legacy (fallback de lectura)
```

Cada `charla_N.json` es un array JSON con esta estructura:
```json
[
    {
        "question": "Texto de la pregunta",
        "response": "Respuesta procesada por el LLM (util_information)",
        "context": {
            "respuesta_llm_1": "respuesta_usuario_1",
            "respuesta_llm_2": "respuesta_usuario_2"
        }
    },
    ...
]
```

---

## Endpoint 1: Obtener Feedback — `POST /bucket/get`

**Archivo:** `Api_Onorato/API/functions/buckets.py:159` — `get_json_from_bucket()`

**Payload del frontend:**
```json
{
    "feedback_user": true,
    "number_version": 1
}
```

**Logica:**
1. Si `number_version` existe → lee directamente `{user_id}/feedback_user/charla_{number_version}.json`
2. Si no existe → busca la version mas alta con `_resolve_version_max()`
3. Si el archivo no existe con formato `charla_N` → intenta formato legacy `{user_id}_vN.json`
4. Retorna el contenido JSON crudo (string) que el frontend parsea

**Acceso a segunda sesion:**
```python
if improved or feedback_user:
    ensure_second_feedback_access(number_version=number_version)
```

Solo emails en `SECOND_FEEDBACK_ALLOWLIST` pueden leer `charla_2.json`.

---

## Endpoint 2: Guardar Feedback (Create) — `POST /onorato_farm/feedback`

**Archivo:** `Api_Onorato/API/functions/buckets.py:384` — `receive_feedback()`

**Payload del frontend:**
```json
{
    "feedback": {
        "question": "Texto de la pregunta",
        "response": "Respuesta util extraida por el LLM",
        "context": {"key": "value"}
    },
    "version": 1
}
```

**Logica:**
1. Extrae `g.user_id` del token autenticado
2. Valida acceso a segunda sesion si `version=2`
3. Llama a `add_json_in_bucket(id_user, version, feedback)`

### Funcion `add_json_in_bucket()` — buckets.py:250-294

```python
def add_json_in_bucket(id_user, version, info):
```

1. Lee documento existente de S3 (`charla_{version}.json`) o inicializa array vacio
2. Normaliza el texto de la pregunta (strip + colapsar espacios)
3. **Si la pregunta ya existe en el documento:**
   - Actualiza `response` y `context` del primer match
   - Elimina duplicados (si hay mas de un match)
4. **Si la pregunta NO existe:**
   - Append al final del array
5. Escribe el documento actualizado a S3

**Comportamiento clave:** Incluso en modo "create", si la pregunta ya existe, se actualiza en lugar de duplicar. Esto actua como un upsert idempontente.

---

## Endpoint 3: Reemplazar Feedback (Replace) — `POST /onorato_farm/feedback/replace`

**Archivo:** `Api_Onorato/API/app.py:437-483`

**Payload del frontend:**
```json
{
    "question": "Texto de la pregunta a reemplazar",
    "version": 1,
    "response": "Nueva respuesta del usuario",
    "context": {"nueva_resp_llm": "nueva_resp_usuario"}
}
```

**Validaciones en el handler (app.py):**
1. Verifica campos obligatorios: `question`, `version`, `response`, `context`
2. Verifica que `context` sea un dict
3. Valida acceso a segunda sesion: `ensure_second_feedback_access(number_version=version)`

**Delega a:** `replace_feedback_in_bucket()` en `buckets.py:296-368`

### Funcion `replace_feedback_in_bucket()` — buckets.py:296-368

```python
def replace_feedback_in_bucket(id_user, version, question_text, new_response, new_context):
```

**Validaciones internas:**
- `question_text` debe ser string no vacio
- `version` no puede ser None
- `new_response` debe ser string
- `new_context` debe ser dict

**Logica:**

1. **Lee el documento de S3:**
   ```python
   document, _ = read_feedback_document(s3, bucket, id_user, version)
   ```
   Intenta `charla_{version}.json`, si no existe intenta `{user_id}_v{version}.json` (legacy). Si ninguno existe, `document = []`.

2. **Normaliza y busca la pregunta:**
   ```python
   normalized_question = _normalize_feedback_question(question_text)
   matches = [index for index, item in enumerate(document)
              if _normalize_feedback_question(item.get('question', '')) == normalized_question]
   ```
   La normalizacion colapsa multiples espacios en uno y aplica strip.

3. **Si NO hay matches (pregunta nueva):**
   ```python
   document.append({
       "question": question_text.strip(),
       "response": new_response,
       "context": new_context,
   })
   ```
   Retorna: `{"updated": False, "created": True, "question": ..., "version": ..., "index": ...}`

4. **Si HAY matches:**
   - Toma el primer match como target
   - Si hay duplicados (>1 match): los elimina, manteniendo solo el primero
   - Actualiza `response` y `context` del target:
     ```python
     document[target_index]['response'] = new_response
     document[target_index]['context'] = new_context
     ```
   Retorna: `{"updated": True, "question": ..., "version": ..., "index": ...}`

5. **Escribe el documento actualizado:**
   ```python
   write_feedback_document(s3, bucket, id_user, version, document)
   ```

### Funcion `write_feedback_document()` — buckets.py:87-95

Siempre escribe con el formato nuevo `charla_{version}.json`:
```python
def write_feedback_document(s3, bucket, id_user, version, document):
    object_key = f"{id_user}/feedback_user/charla_{version}.json"
    s3.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=json.dumps(document, indent=4, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json'
    )
```

**Nota importante:** Incluso si se leyo desde formato legacy (`{user_id}_vN.json`), se escribe siempre como `charla_N.json`. Esto migra implicitamente del formato legacy al nuevo.

### Funcion `read_feedback_document()` — buckets.py:72-84

```python
def read_feedback_document(s3, bucket, id_user, version):
    object_key = _feedback_object_key(id_user, version)  # charla_{version}.json
    try:
        response = s3.get_object(Bucket=bucket, Key=object_key)
        return json.loads(response['Body'].read().decode('utf-8')), object_key
    except s3.exceptions.NoSuchKey:
        # Fallback a formato legacy
        legacy_key = _legacy_feedback_object_key(id_user, version)  # {user_id}_v{version}.json
        try:
            response = s3.get_object(Bucket=bucket, Key=legacy_key)
            return json.loads(response['Body'].read().decode('utf-8')), legacy_key
        except s3.exceptions.NoSuchKey:
            raise FeedbackFileNotFoundError("Feedback file not found")
```

---

## Endpoint 4: Consultar Finalizacion — `POST /onorato_farm/is_finish`

**Archivo:** `Api_Onorato/API/routes/onoratoFarm/manage_progres.py:41-81`

**Payload:**
```json
{
    "number_chat": 1
}
```

**Logica:**
1. Determina columna: `first_feedback` (sesion 1) o `second_feedback` (sesion 2)
2. Query:
   ```sql
   SELECT {feedback_column} FROM FINISH_FORM WHERE id_user = %s LIMIT 1
   ```
3. Si el campo es NULL → `{"isFinish": false}`
4. Si tiene valor → `{"isFinish": true}`

---

## Endpoint 5: Marcar Finalizacion — `POST /onorato_farm/set_finish`

**Archivo:** `Api_Onorato/API/routes/onoratoFarm/manage_progres.py:8-39`

**Payload:**
```json
{
    "number_chat": 1
}
```

**Logica:**
1. Valida acceso a segunda sesion si `number_chat=2`
2. Determina columna: `first_feedback` o `second_feedback`
3. Update:
   ```sql
   UPDATE FINISH_FORM SET {feedback_column} = %s WHERE id_user = %s
   ```
   Con `datetime.now()` como valor.

**Efecto:** Una vez marcada, `is_finish` retornara `true` y el frontend mostrara WaitingPage en lugar de permitir mas ediciones.

---

## Control de Acceso: Segunda Sesion

**Archivo:** `Api_Onorato/API/functions/feedback_access.py`

```python
SECOND_FEEDBACK_ALLOWLIST = {
    'liliana.onoratoai@gmail.com',
    'pierrekallai05@gmail.com',
    'gemavaleropla@gmail.com',
    'vgarciamonguilod@gmail.com',
    'pablo@onoratoai.com',
}
```

La funcion `ensure_second_feedback_access()` se ejecuta en:
- `/onorato_farm/feedback` (al guardar)
- `/onorato_farm/feedback/replace` (al reemplazar)
- `/onorato_farm/set_finish` (al finalizar)
- `/onorato_farm/is_finish` (al consultar)
- `/bucket/get` con `feedback_user=true` (al leer)

Solo valida cuando `version=2` o `number_session=2`. Si el email del usuario (de `g.email`) no esta en la whitelist, lanza `AppError('FEEDBACK_ACCESS_DENIED')`.

---

## Flujo Completo de Datos: Repeat + Replace

```
FRONTEND                                    BACKEND                          S3
────────                                    ───────                          ──

1. Usuario clicka "Repetir"
   │
   ├─ Guarda estado en localStorage
   ├─ Navega a Page 3 (ThirdPage)
   │
2. Usuario graba nueva respuesta
   │
   ├─ STT → texto transcrito
   │
3. Texto enviado al LLM
   │                                   POST /onorato_farm/get_response
   │                                        │
   │                                        ├─ Procesa con OpenAI/Nextbit
   │                                        └─ Retorna: {response, util_information, finish_question}
   │
4. LLM dice finish_question=true
   │
   ├─ persistFeedbackAnswer(mode:'replace')
   │                                   POST /onorato_farm/feedback/replace
   │                                        │
   │                                        ├─ Valida campos
   │                                        ├─ ensure_second_feedback_access()
   │                                        │
   │                                        ├─ replace_feedback_in_bucket()
   │                                        │       │
   │                                        │       ├─ read_feedback_document()
   │                                        │       │       │                    GET charla_1.json
   │                                        │       │       │                         │
   │                                        │       │       └────────────────────────←┘
   │                                        │       │
   │                                        │       ├─ Busca pregunta (normalizada)
   │                                        │       ├─ Actualiza response + context
   │                                        │       ├─ Elimina duplicados si los hay
   │                                        │       │
   │                                        │       ├─ write_feedback_document()
   │                                        │       │       │                    PUT charla_1.json
   │                                        │       │       │                         │
   │                                        │       │       └────────────────────────→┘
   │                                        │       │
   │                                        │       └─ Retorna {updated:true, index:N}
   │                                        │
   │                                        └─ Retorna {success:true, updated:true, ...}
   │
5. Frontend muestra modal "Actualizado"
   │
6. Usuario vuelve a QuestionPage
   │
   ├─ getFeedbackAnswers(1)
   │                                   POST /bucket/get
   │                                        │
   │                                        ├─ get_json_from_bucket(feedback_user=true, number_version=1)
   │                                        │       │                    GET charla_1.json
   │                                        │       │                         │
   │                                        │       └────────────────────────←┘
   │                                        │
   │                                        └─ Retorna JSON con respuesta actualizada
   │
7. QuestionPage muestra nueva respuesta
   │
8. Usuario clicka "Confirmar"
   │
   ├─ finishChat(1)
   │                                   POST /onorato_farm/set_finish
   │                                        │
   │                                        ├─ ensure_second_feedback_access()
   │                                        ├─ UPDATE FINISH_FORM SET first_feedback = NOW()
   │                                        └─ Retorna {message: "Chat marked as finished"}
   │
9. Navega a WaitingPage (Page 8)
```

---

## Normalizacion de Preguntas

La funcion `_normalize_feedback_question()` es critica para el matching:

```python
def _normalize_feedback_question(value):
    if not isinstance(value, str):
        return ''
    return re.sub(r'\s+', ' ', value).strip()
```

Esto permite que preguntas con diferencias menores de espaciado se reconozcan como la misma pregunta. Se usa tanto en `add_json_in_bucket()` como en `replace_feedback_in_bucket()`.

---

## Manejo de Errores

### Excepciones Personalizadas (buckets.py:11-42)

| Excepcion | Status | Cuando |
|-----------|--------|--------|
| `FeedbackValidationError` | 400 | Payload invalido (campos faltantes/tipo incorrecto) |
| `FeedbackFileNotFoundError` | 404 | No existe `charla_N.json` ni formato legacy |
| `FeedbackQuestionNotFoundError` | 404 | (Definida pero no usada actualmente en replace) |
| `FeedbackDuplicateQuestionError` | 409 | (Definida pero no usada actualmente en replace) |
| `FeedbackInvalidDocumentError` | 500 | Documento existente no es una lista |

### Respuestas de Error del Endpoint Replace

```json
// Campos faltantes (400)
{
    "success": false,
    "error": "missing_fields",
    "fields": ["question", "context"]
}

// Context invalido (400)
{
    "success": false,
    "error": "invalid_context",
    "message": "context must be an object"
}

// Error de reemplazo (variable status)
{
    "success": false,
    "error": "invalid_feedback_replace_payload",
    "message": "question is required",
    "question": "...",
    "version": 1
}
```

---

## Tabla de Base de Datos: FINISH_FORM

```sql
FINISH_FORM
├── id_parrot VARCHAR(20) PK
├── id_user VARCHAR(50)
├── form JSON                    -- Formulario inicial completo
├── send_date DATETIME           -- Cuando se envio el formulario
├── first_feedback DATETIME      -- Cuando se completo charla 1 (NULL = no completada)
├── second_feedback DATETIME     -- Cuando se completo charla 2 (NULL = no completada)
└── third_feedback TEXT          -- Notas adicionales
```

**Ciclo de vida de un usuario:**
1. Completa formulario → `send_date` se llena
2. Completa charla 1 (con posibles repeats) → `first_feedback` se llena
3. Completa charla 2 (restringida) → `second_feedback` se llena

---

## Notas Tecnicas Importantes

1. **No hay versionado de respuestas en S3** — cada replace sobreescribe el archivo completo. No hay historial de versiones anteriores de una respuesta.

2. **Deduplicacion automatica** — tanto `add_json_in_bucket` como `replace_feedback_in_bucket` eliminan preguntas duplicadas encontrando multiples matches.

3. **Migracion transparente de formato** — la lectura soporta formato legacy (`{user_id}_vN.json`) pero la escritura siempre usa el nuevo formato (`charla_N.json`). Un replace migra automaticamente el archivo.

4. **Idempontencia** — llamar replace multiples veces con la misma pregunta y respuesta produce el mismo resultado (actualiza in-place sin crear duplicados).

5. **El context del frontend es un Map serializado** — `contextMapRef.current` es un `Map<respuesta_llm, respuesta_usuario>` que se convierte a objeto plano via `buildFeedbackContext()` antes de enviar al backend. Representa el historial de la conversacion LLM para esa pregunta.

6. **Sin transacciones S3** — la operacion read-modify-write no es atomica. Si dos requests concurrentes intentan modificar el mismo archivo, podria haber race conditions. En la practica no ocurre porque un usuario solo puede estar en un flujo a la vez.
