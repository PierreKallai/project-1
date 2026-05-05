# Cambios Backend (Api_Onorato) — Rama 95 vs Main

## Resumen general
- **41 archivos** modificados | **779 inserciones** | **531 eliminaciones**
- Funcionalidad principal: soporte para repetir/reemplazar preguntas de feedback, mejora del sistema de audio (TTS/STT), reorganización de audios de espera

---

## Archivos modificados

### 1. `API/app.py`
**Cambios:**
- Nuevo endpoint `POST /onorato_farm/feedback/replace` — permite reemplazar la respuesta de una pregunta específica en un feedback ya enviado
- Importación de `FeedbackReplaceError`, `replace_feedback_in_bucket`, `ensure_second_feedback_access`
- Eliminada importación de `redis` (no se usa)
- Limpieza de formato (espacios, imports)

### 2. `API/functions/buckets.py`
**Cambios principales:**
- Nueva jerarquía de excepciones: `FeedbackReplaceError`, `FeedbackValidationError`, `FeedbackFileNotFoundError`, `FeedbackQuestionNotFoundError`, `FeedbackDuplicateQuestionError`, `FeedbackInvalidDocumentError`
- Nuevas funciones auxiliares:
  - `_resolve_version_max(contents)` — resuelve la versión máxima del feedback
  - `_feedback_object_key(id_user, version)` — genera la key S3 del documento de feedback
  - `_legacy_feedback_object_key(id_user, version)` — soporte de keys legacy
  - `read_feedback_document(s3, bucket, id_user, version)` — lee un documento de feedback de S3
  - `write_feedback_document(s3, bucket, id_user, version, document)` — escribe un documento de feedback en S3
  - `add_json_in_bucket(id_user, version, info)` — añade JSON al bucket
  - `replace_feedback_in_bucket(id_user, version, question_text, new_response, new_context)` — reemplaza una respuesta específica en el feedback existente en S3
- Refactorización de `push_json_to_bucket` y `get_json_from_bucket`

### 3. `API/functions/feedback_access.py`
**Cambios:**
- Eliminadas funciones obsoletas: `_normalize_user_id`, `is_second_feedback_allowlisted`, `is_second_feedback_allowlisted_user_id`, `has_completed_second_feedback`
- Eliminada `SECOND_FEEDBACK_ALLOWLIST_USER_IDS`
- Simplificada la lógica de acceso al segundo feedback (se delega en `ensure_second_feedback_access`)

### 4. `API/routes/finish_form/get_json_form.py`
**Cambios menores** de formato/limpieza

### 5. `API/routes/onoratoFarm/generate_audios.py`
**Cambios:**
- Refactorizado para ser ejecutable como script CLI (`argparse`)
- Eliminadas frases de espera hardcodeadas `WAITING_PHRASES_ES` — se leen ahora de `waiting_phrases.json`
- Nueva constante `SUPPORTED_KINDS = {"waitings"}`
- Nueva función `get_openai_client()` — centraliza la inicialización del cliente OpenAI
- Soporte para cargar `.env` local para ejecución standalone

### 6. `API/routes/onoratoFarm/get_voice.py`
**Cambios:**
- Nueva función `_fallback(lang)` — fallback cuando no hay audio disponible
- Nueva función `_resolve_audio_language(requested_language)` — resuelve idioma del audio
- Nueva función `_list_audio_files(folder_path)` — lista archivos de audio en un directorio
- Refactorización de `getResponse()` y `return_audios()` — mejora manejo de idiomas y fallback

### 7. `API/routes/onoratoFarm/transcription.py`
**Cambios:**
- Nueva función `_empty_transcription_response(reason, **details)` — respuesta estandarizada para audio vacío/inválido
- Nueva función `_is_invalid_audio_format_error(error)` — detecta errores de formato de audio
- Importación de `binascii` para validación de audio
- Limpieza de comentarios extensos y reorganización de constantes de alucinaciones de Whisper
- Mejor manejo de errores: audio corrupto, formato inválido, archivos muy pequeños

### 8. `API/routes/onoratoFarm/waiting_phrases.json` (NUEVO)
- Archivo JSON con frases de espera en español e inglés para TTS
- Reemplaza las frases hardcodeadas que estaban en `generate_audios.py`

### 9. Archivos de audio (mp3)
- **Eliminados:** 11 archivos `waitings_X.mp3` en inglés (nombre con "s" final)
- **Añadidos:** 11 archivos `waiting_X.mp3` en inglés (nombre corregido sin "s")
- **Reemplazados:** 11 archivos `waiting_X.mp3` en español (nuevas grabaciones TTS más cortas/naturales)
- Nuevo archivo `waiting_1.mp3` para español

---

## Nuevos endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/onorato_farm/feedback/replace` | Reemplaza la respuesta de una pregunta en un feedback existente |

---

## Dependencias eliminadas
- `redis` — ya no se importa en `app.py`
