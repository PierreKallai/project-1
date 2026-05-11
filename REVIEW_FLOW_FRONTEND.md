# Flujo de Revision de Preguntas (Frontend)

Documentacion completa del flujo de revision de preguntas del OnoratoFarm antes de enviar/finalizar una sesion de charla.

---

## Resumen General

Cuando el usuario termina de responder todas las preguntas del chat con Onorato, llega a una pantalla de resumen (Page 5 o Page 7/SixthPage). Desde ahi puede:
1. **Revisar** sus respuestas en un modal/pagina (QuestionPage)
2. **Repetir** una pregunta especifica para dar una nueva respuesta
3. **Confirmar** que esta satisfecho y finalizar la sesion

---

## Arquitectura de Paginas Involucradas

```
OnoratoFarm.jsx (Orchestrador principal)
├── Page 3: ThirdPage.jsx      → Onorato pregunta, procesa LLM
├── Page 4: FourPage.jsx       → Usuario graba respuesta de voz
├── Page 5: FivePage.jsx       → Resumen post-chat + boton "Revisar"
├── Page 6: QuestionPage.jsx   → Vista pagina completa (case 6 del switch)
├── Page 7: SixthPage.jsx      → Resumen alternativo + boton "Revisar"
├── Page 8: WaitingPage.jsx    → Pantalla de finalizacion
└── QuestionPage (modal)       → Se superpone sobre cualquier pagina (questionPage=true)
```

---

## Punto de Entrada: Botones que Abren la Revision

### Desde FivePage (Page 5)
**Archivo:** `form_frontend-2/src/pages/onoratoFarm/FivePage.jsx:40`

```jsx
<button onClick={() => {setQuestionPage(true)}}>
    {t('onoratoFarm.page5.review')}  // "Revisar registro"
</button>
```

Este boton abre el QuestionPage como **modal overlay** (con `arrowActivate=true`).

Ademas hay un boton "Finalizar" en el footer:
```jsx
<button className='finish-button-onorato' onClick={onFinishReview || nextPage}>
    {t('onoratoFarm.page5.next')}
</button>
```

### Desde SixthPage (Page 7)
**Archivo:** `form_frontend-2/src/pages/onoratoFarm/SixthPage.jsx:28`

```jsx
<button className='review-button' onClick={() => {setQuestionPage(true)}}>
    {t('onoratoFarm.page6.button2')}  // "Ver preguntas"
</button>
```

Tambien abre el modal. El boton inferior finaliza directamente:
```jsx
<button onClick={() => { onFinishReview ? onFinishReview() : nextPage() }}>
    {t('onoratoFarm.page6.button')}  // "Finalizar"
</button>
```

### QuestionPage como Pagina Directa (Page 6)
**Archivo:** `OnoratoFarm.jsx:758`

En el case 6 del switch, QuestionPage se renderiza como pagina completa (no modal) con `arrowActivate=false` e `isPage=true`.

---

## El Modal / Pagina de Revision: QuestionPage

**Archivo:** `form_frontend-2/src/pages/onoratoFarm/QuestionPage.jsx`

### Dos modos de renderizado:

| Propiedad | Modal (overlay) | Pagina (case 6) |
|-----------|----------------|-----------------|
| `arrowActivate` | `true` | `false` |
| `isPage` | `false` (default) | `true` |
| Flecha atras | Visible (cierra modal) | No visible |
| Boton Confirmar | Cierra modal | Llama `onFinishReview` |

### Carga de datos

Al montarse, QuestionPage ejecuta:
```jsx
const resultResponse = await getFeedbackAnswers(numberSession);
const feedbackItems = normalizeFeedbackItems(resultResponse);
```

- `getFeedbackAnswers(version)` llama `POST /bucket/get` con `{feedback_user: true, number_version: version}`
- Obtiene el JSON de S3 (`charla_{version}.json`) con todas las preguntas/respuestas de esa sesion
- `normalizeFeedbackItems()` normaliza el array asegurando que cada item tiene `question`, `response` y `context`

Si no hay items, redirige a Page 1: `goToSpecificPage?.(1)`

### Renderizado de preguntas

Cada pregunta se muestra como un **acordeon colapsable**:
- Click en el header → toggle expand/collapse via `toggleAnswer(index)`
- Estado de expansion: array `isActive[]`

Cuando esta expandida muestra:
1. El texto de la respuesta (`item.response`)
2. Un boton **"Repetir pregunta"** con icono `<RefreshCw>`

### El boton "Repetir Pregunta"
**Linea 148-157 de QuestionPage.jsx:**

```jsx
<button
    className="question-page-repeat-button"
    disabled={disableRepeat || isFinalizing || repeatingIndex === index}
    onClick={(event) => handleRepeatQuestion(event, item, index)}
>
    <RefreshCw size={16} />
    {t('onoratoFarm.questionPage.repeatQuestion')}
</button>
```

Se deshabilita cuando:
- `disableRepeat=true` (hay un repeat en curso)
- `isFinalizing=true` (se esta finalizando)
- `repeatingIndex === index` (se acaba de clickar ese mismo)

### El boton "Confirmar"
**Linea 161-169:**

Logica de `handleConfirm()`:
1. Si `disableRepeat` → muestra error "repeatPendingError" (no deja confirmar con repeat pendiente)
2. Si `arrowActivate` (es modal) → simplemente cierra: `setQuestionPage(false)`
3. Si tiene `onFinishReview` → lo ejecuta (finaliza la sesion)
4. Si `isPage && nextPage` → avanza de pagina
5. Else → cierra modal

### RefreshKey

La prop `refreshKey` se usa como dependencia del `useEffect` que carga las preguntas. Cuando se completa un repeat, el orchestrador incrementa `feedbackReviewRefreshKey`, forzando una recarga de los datos desde S3 para mostrar la respuesta actualizada.

---

## Flujo de Repeticion de Pregunta

### Paso 1: Usuario clicka "Repetir" en QuestionPage

`handleRepeatQuestion` en QuestionPage (linea 67) propaga al orchestrador:
```jsx
onRepeatQuestion({
    questionText: item.question,
    sessionVersion: numberSession,
    questionIndex: index
});
```

### Paso 2: Orchestrador prepara el repeat

**Archivo:** `OnoratoFarm.jsx:684-697` — `handleRepeatQuestion()`

Resetea todo el estado del chat:
- `contextMapRef.current = new Map()` — limpia contexto de conversacion
- `setText("")` — limpia texto del usuario
- `setLastLLMResponse("")` — limpia ultima respuesta LLM
- `setResponseLLM([])` — limpia array de respuestas
- `setNumberIterations(0)` — reinicia contador de iteraciones
- `setActivateNextQuestion(false)` — desactiva avance automatico
- `setComeToFourPage(false)` — impide navegacion prematura a Page 4
- `setAudioWelcomeUrl(null)` — elimina audio de bienvenida
- `hasConsumedWelcomeRef.current = true` — marca bienvenida como consumida
- `lastAutoplayedQuestionIndexRef.current = null` — resetea autoplay
- `replayQuestionOnBackRef.current = true` — fuerza replay de la pregunta

Finalmente llama:
```jsx
startRepeatQuestion({ questionText, sessionVersion, questionIndex });
```

### Paso 3: Hook `useRepeatQuestionFlow` gestiona la transicion

**Archivo:** `form_frontend-2/src/pages/onoratoFarm/hooks/useRepeatQuestionFlow.js`

`startRepeatQuestion()` (linea 50-66):
1. Persiste estado en localStorage via `saveRepeatQuestionState()`
2. Actualiza estado React: `setRepeatState(storedState)`
3. Cierra el modal: `setQuestionPage(false)`
4. Establece index: `setCurrentQuestionIndex(storedState.questionIndex)`
5. Navega a Page 3: `goToSpecificPage(3)`

### Paso 4: Persistencia en localStorage

**Archivo:** `form_frontend-2/src/pages/onoratoFarm/utils/repeatQuestionStorage.js`

Key: `'onoratoFarm.repeatQuestion'`

Estructura guardada:
```json
{
    "questionText": "Texto de la pregunta original",
    "sessionVersion": 1,
    "questionIndex": 3
}
```

Funciones:
- `saveRepeatQuestionState(state)` — valida y guarda
- `loadRepeatQuestionState()` — lee y normaliza
- `clearRepeatQuestionState()` — elimina
- `hasRepeatQuestionState()` — consulta rapida (boolean)

La persistencia en localStorage asegura que si el usuario refresca la pagina durante un repeat, el estado se recupera automaticamente.

### Paso 5: ThirdPage detecta modo repeat

**Archivo:** `form_frontend-2/src/pages/onoratoFarm/ThirdPage.jsx:79-104`

Al montarse/actualizarse con `repeatMode=true`:
1. Busca el indice real de la pregunta: `findQuestionIndexByText(answers, repeatQuestionState.questionText)`
2. Si no la encuentra → llama `onRepeatQuestionMissing()` (limpia estado)
3. Si la encuentra → establece el indice como `currentQuestionIndex`
4. Resetea contexto y estado de procesamiento LLM
5. Muestra el texto de la pregunta en pantalla

La referencia `wasRepeatRef` se marca como `true` cuando hay `repeatMode`, y persiste durante todo el procesamiento del buffer.

### Paso 6: Usuario re-responde la pregunta

El flujo normal de ThirdPage se ejecuta:
1. Se reproduce el audio de la pregunta
2. Se navega a Page 4 (FourPage) donde el usuario graba su voz
3. El audio se transcribe (STT)
4. Se vuelve a Page 3 con la transcripcion
5. Se envia al LLM para procesamiento

### Paso 7: Persistencia de la nueva respuesta

**Archivo:** `ThirdPage.jsx:475-498`

Cuando el LLM marca `finish_question=true`:
```jsx
await persistFeedbackAnswer({
    mode: wasRepeatRef.current ? 'replace' : 'create',
    version: numberSession,
    ...feedbackPayload
});
```

Si es un repeat → `mode: 'replace'` → llama a `POST /onorato_farm/feedback/replace`
Si es respuesta nueva → `mode: 'create'` → llama a `POST /onorato_farm/feedback`

### Paso 8: Modal de confirmacion de actualizacion

Despues de persistir con exito en modo repeat:
```jsx
setShowRepeatUpdateModal(true);
await generateAudio(t('onoratoFarm.questionPage.repeatUpdatedModalText'), true);
```

Se muestra un `ModalOnoratoFarm` confirmando que la respuesta fue actualizada, con audio TTS.

### Paso 9: Completar el repeat

Cuando el modal se cierra, se ejecuta `handleRepeatQuestionCompleted()` (OnoratoFarm.jsx:699-709):

1. Resetea todo el estado del chat (igual que al iniciar)
2. Incrementa `feedbackReviewRefreshKey` → fuerza recarga de QuestionPage
3. Llama `completeRepeatQuestion()` del hook

`completeRepeatQuestion()` (useRepeatQuestionFlow.js:73-78):
1. Limpia localStorage: `clearRepeatQuestionState()`
2. Limpia state: `setRepeatState(null)`
3. Navega a Page 5: `goToSpecificPage(5)`
4. Abre el modal: `setQuestionPage(true)`

El usuario vuelve a ver QuestionPage con la respuesta actualizada y puede repetir otra pregunta o confirmar.

### Paso 10: Fallback si el LLM falla

**Archivo:** `ThirdPage.jsx:509-533`

Si durante un repeat el LLM falla (error 500 o "Empty LLM"):
1. Se guarda la respuesta cruda del usuario (sin procesamiento LLM) como fallback:
   ```jsx
   await persistFeedbackAnswer({
       mode: 'replace',
       version: numberSession,
       question: currentItem.question,
       response: currentItem.userAnswer,  // texto raw del usuario
       context: buildFeedbackContext(contextMapRef.current)
   });
   ```
2. Llama directamente a `onRepeatQuestionCompleted()` sin pasar por el modal

---

## Flujo de Finalizacion

### `handleFinishReview()` — OnoratoFarm.jsx:711-743

1. **Validacion:** Verifica que no hay repeat pendiente
   ```jsx
   if (repeatMode || hasRepeatQuestionState()) {
       setError({ message: t('onoratoFarm.questionPage.repeatPendingError') });
       return false;
   }
   ```

2. **API call:** `await finishChat(numberSession)` → `POST /onorato_farm/set_finish`

3. **Limpieza:**
   - `clearRepeatQuestion()` — limpia localStorage
   - `clearFlowState()` — resetea estado del flow
   - `setQuestionPage(false)` — cierra modal

4. **Navegacion:** `goSpecificPage(8)` → WaitingPage

5. **Estado global:** Marca sesion como completada en `completedFeedbacks`

---

## Diagrama de Flujo Completo

```
┌──────────────────────────────────────────────────────────┐
│  Chat completado (todas las preguntas respondidas)       │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  PAGE 5 (FivePage) — Resumen                             │
│                                                          │
│  [Revisar registro]  →  Abre modal QuestionPage          │
│  [Finalizar]         →  handleFinishReview()             │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  MODAL: QuestionPage (arrowActivate=true)                │
│                                                          │
│  ┌─────────────────────────────────┐                     │
│  │ Pregunta 1 (colapsable)         │                     │
│  │  > "Tu respuesta aqui..."       │                     │
│  │  [🔄 Repetir pregunta]          │                     │
│  ├─────────────────────────────────┤                     │
│  │ Pregunta 2 (colapsable)         │                     │
│  │  > "Tu respuesta aqui..."       │                     │
│  │  [🔄 Repetir pregunta]          │                     │
│  ├─────────────────────────────────┤                     │
│  │ ...                             │                     │
│  └─────────────────────────────────┘                     │
│                                                          │
│  [← Volver]              [Confirmar]                     │
└──────────┬─────────────────────┬─────────────────────────┘
           │                     │
     Click "Repetir"       Click "Confirmar"
           │                     │
           ▼                     ▼
┌─────────────────┐    ┌────────────────────┐
│ Save state      │    │ Cierra modal       │
│ localStorage    │    │ (vuelve a Page 5)  │
│ Navega a Page 3 │    └────────────────────┘
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│  PAGE 3 (ThirdPage) — Modo Repeat                        │
│                                                          │
│  - Detecta repeatMode=true                               │
│  - Posiciona en la pregunta correcta                     │
│  - Reproduce audio de la pregunta                        │
│  - Navega a Page 4 para grabar respuesta                 │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  PAGE 4 (FourPage) — Grabar nueva respuesta              │
│                                                          │
│  - Usuario habla / graba audio                           │
│  - Transcripcion STT                                     │
│  - Vuelve a Page 3 con texto                             │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  PAGE 3 — Procesamiento LLM                              │
│                                                          │
│  - Envia respuesta al LLM                                │
│  - LLM evalua y puede pedir mas info (max 2 iter.)      │
│  - Cuando finish_question=true:                          │
│    → persistFeedbackAnswer(mode:'replace')               │
│    → Muestra modal "Respuesta actualizada"               │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  handleRepeatQuestionCompleted()                         │
│                                                          │
│  - Limpia localStorage                                   │
│  - Incrementa refreshKey                                 │
│  - Navega a Page 5                                       │
│  - Abre modal QuestionPage (con datos actualizados)      │
└──────────────────────┬───────────────────────────────────┘
                       │
          (Ciclo: puede repetir otra pregunta)
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  FINALIZACION                                            │
│                                                          │
│  handleFinishReview():                                   │
│  1. Verifica no hay repeat pendiente                     │
│  2. POST /onorato_farm/set_finish                        │
│  3. Limpia todo el estado                                │
│  4. Navega a Page 8 (WaitingPage)                        │
└──────────────────────────────────────────────────────────┘
```

---

## Archivos Clave

| Archivo | Responsabilidad |
|---------|----------------|
| `OnoratoFarm.jsx` | Orchestrador: gestiona estado global, conecta repeat con QuestionPage |
| `QuestionPage.jsx` | Renderiza lista de preguntas/respuestas, botones de repeat y confirmar |
| `ThirdPage.jsx` | Pagina de pregunta: detecta modo repeat, llama LLM, persiste respuesta |
| `FourPage.jsx` | Grabacion de voz del usuario |
| `FivePage.jsx` | Resumen con botones "Revisar" y "Finalizar" |
| `SixthPage.jsx` | Resumen alternativo con mismos botones |
| `useRepeatQuestionFlow.js` | Hook que gestiona transiciones del repeat |
| `repeatQuestionStorage.js` | Persistencia localStorage del estado repeat |
| `feedbackItems.js` | Utilidades de normalizacion y busqueda de preguntas |
| `api_functions.js` | Funciones API: `persistFeedbackAnswer`, `getFeedbackAnswers`, `finishChat` |

---

## Reglas de Negocio

1. **No se puede finalizar con un repeat pendiente** — el boton Confirmar se deshabilita y muestra error
2. **Las respuestas no se borran, se reemplazan** — modo `replace` actualiza en S3 in-place
3. **El contexto LLM se resetea** en cada repeat (nueva conversacion limpia)
4. **Maximo 2 iteraciones LLM** por pregunta (si insiste, se fuerza `finish_question`)
5. **Si el LLM falla en repeat** — se guarda la transcripcion cruda del usuario como respuesta
6. **El estado de repeat sobrevive a refresh** — localStorage como fuente de verdad
7. **La segunda sesion (charla 2) esta restringida** — solo emails en whitelist pueden acceder
