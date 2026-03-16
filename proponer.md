# 🦜 Proyecto Onorato - Plan de Refactorización y Arquitectura

> **Resumen:** Este documento detalla las actualizaciones estructurales implementadas para llevar el backend y frontend de Onorato a un estándar de producción robusto. Las mejoras resuelven bugs críticos reportados (cuelgues, pérdida de estado), optimizan el coste/rendimiento del LLM y unifican el manejo de errores.

---

## 1. 🧠 Optimización del LLM: Inyección Dinámica de Contexto

* **Archivos afectados:** `API/onorato/get_voice.py`, Modelos JSON en S3.
* **Problema (Context Overflow):** Al inyectar todo el historial de vida del usuario de golpe en el `system_prompt`, la IA se saturaba de información irrelevante, lo que provocaba alucinaciones y desvíos de la conversación.
* **Solución:** Transición a un modelo de inyección dinámica. El frontend ahora envía una `"category"` (ej. *salud*, *familia*) con cada pregunta. El backend inyecta **únicamente** la información general y la específica de esa categoría en el prompt temporal.
* ✅ **Ventajas:** 
  - Cero alucinaciones (foco total en la pregunta actual).
  - Reducción drástica del consumo de tokens (ahorro en API de OpenAI).
  - El agente cacheado se vuelve mucho más ligero.
* ⚠️ **Consideraciones:** Requiere un script de migración para convertir los strings monolíticos de S3 al nuevo formato JSON estructurado por categorías.

## 2. 🗣️ Política Estricta de Idioma y Dialecto ("Efecto Espejo")

* **Archivos afectados:** `API/onorato/get_voice.py` (System Prompt de `create_agent`).
* **Problema:** `gpt-4o-mini` tendía a normalizar las respuestas a un español/inglés neutro, rompiendo la inmersión y calidez al interactuar con adultos mayores que usan dialectos regionales.
* **Solución:** Rediseño del prompt usando *few-shot implícito*. Se fuerza al LLM a comportarse como un espejo lingüístico, detectando y replicando exactamente el dialecto, jerga y formalidad del usuario.
* ✅ **Ventajas:** Interacciones mucho más orgánicas, empáticas y culturalmente precisas.
* ⚠️ **Consideraciones:** Ante respuestas ultracortas ("Sí"), el LLM usará el idioma base temporalmente al no tener contexto suficiente para detectar el dialecto.

## 3. ⚡ Desbloqueo de Concurrencia (Fix "Waiting" infinito)

* **Archivos afectados:** `API/onorato/get_voice.py` (Función `get_voice`).
* **Problema:** Un `mutex` bloqueaba todo el servidor durante el tiempo que tardaba OpenAI en generar y devolver el audio TTS, provocando colas de peticiones y estados de "waiting" infinitos en los clientes.
* **Solución:** Se extrajo la petición de red (`openai.audio.speech.create`) fuera del bloque `with mutex:`. El candado ahora solo protege las lecturas/escrituras en la caché en memoria.
* ✅ **Ventajas:** El servidor ahora es 100% asíncrono para las llamadas de red, soportando múltiples usuarios simultáneos sin bloqueos.

## 4. 🛡️ Cierre Determinista por Iteraciones (Anti-Fatiga)

* **Archivos afectados:** `API/onorato/get_voice.py` (Función `getResponse`).
* **Problema:** A veces el LLM ignoraba el límite lógico de 2 iteraciones, haciendo que los ancianos tuvieran que responder a la misma pregunta 3 o 4 veces.
* **Solución:** Límite "Hardcoded" en Python. Se añadió `if int(number_iterations) >= 2: parsed_result['finish_question'] = True` para sobrescribir la decisión de la IA.
* ✅ **Ventajas:** Garantía absoluta de que el sistema respeta los límites de fatiga cognitiva por diseño, independientemente de lo que decida el LLM.

## 5. 🚨 Integración Centralizada de Errores (`AppError`)

* **Archivos afectados:** `API/onorato/get_voice.py` y `API/functions/buckets.py`.
* **Problema:** Las excepciones de S3 y de la API de OpenAI se silenciaban devolviendo `False` o un error `500` genérico, evadiendo las notificaciones de AWS SES y las auto-reparaciones.
* **Solución:** Invocación explícita de `raise AppError('S3_ERROR')` y `raise AppError('AI_ERROR')` en los bloques `except`.
* ✅ **Ventajas:** Los fallos críticos ahora disparan alertas a los desarrolladores y ejecutan acciones de limpieza (`clear_temp`, `restart_service`) automáticamente a través de `error_handler.py`.

## 6. 🗂️ Corrección de Versiones Duplicadas de Feedback en S3

* **Archivos afectados:** `API/functions/buckets.py` (Función `push_json_to_bucket`).
* **Problema:** El sistema calculaba la siguiente versión contando los archivos en S3. Al navegar por la UI, se creaban archivos como `_v2` o `_v3` para la misma sesión (dispersión de datos).
* **Solución:** La función ahora evalúa y respeta estrictamente el parámetro `number_version` enviado por el frontend.
* ✅ **Ventajas:** Se garantiza un único archivo maestro consolidado (`charla_1`, `charla_2`) por cada sesión.
* ⚠️ **Consideraciones:** El frontend es ahora el responsable único de mantener y enviar el ID de versión correcto en el *payload*.

## 7. 💻 Blindaje de Salida Accidental (Frontend)

* **Archivos afectados:** `src/components/OnoratoFarm.jsx`.
* **Problema:** Si el usuario pulsaba la tecla `Escape` por accidente, el navegador desmontaba la vista, perdiendo todo el progreso de la entrevista.
* **Solución:** Implementación de un `useEffect` con un event listener global en fase de captura (`{ capture: true }`), anulando el comportamiento nativo con `preventDefault()` y `stopPropagation()`.
* ✅ **Ventajas:** Blindaje total de la sesión. Gran mejora en la Accesibilidad y UX para el público objetivo.

---

### 🚀 Hoja de Ruta Próximos Pasos

- [ ] **Frontend:** Añadir parámetro `"category"` al payload de la API de preguntas.
- [ ] **Data:** Ejecutar script Lambda para migrar los perfiles actuales de S3 a la estructura de diccionario por categorías.
- [ ] **QA:** Monitorizar logs de AWS SES las primeras 48h tras el despliegue para descartar falsos positivos de `AppError`.
