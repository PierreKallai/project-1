# Plan de implementacion: fallos de audio en iPhone/Safari

## Contexto

En iPhone/Safari, durante la charla con Onorato, algunas usuarias llegan al modal:

> Por favor, di o escribe algo antes de enviar tu respuesta.

Esto no implica necesariamente que la usuaria no haya hablado. En el flujo actual, ese mensaje tambien aparece cuando la grabacion no produce audio valido, cuando Safari genera un blob vacio/corrupto, cuando OpenAI rechaza el audio o cuando la transcripcion vuelve vacia.

El objetivo es distinguir esos casos, evitar el bucle y permitir continuar la charla aunque falle el microfono.

## Archivos principales

- `form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`
- `form_frontend-2/src/locales/es/translation.json`
- `form_frontend-2/src/locales/en/translation.json`
- `Api_Onorato/API/routes/onoratoFarm/transcription.py`

## 1. Mejorar deteccion de formato de audio

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Codigo actual

```js
if (isMobile) {
    return MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '';
}
```

### Cambio propuesto

Usar deteccion real de formatos soportados, sin asumir que mobile siempre debe usar `audio/mp4`.

```js
const getAudioMimeType = () => {
    const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4;codecs=mp4a.40.2',
        'audio/mp4',
        'audio/aac',
        'audio/ogg;codecs=opus',
        'audio/ogg'
    ];

    return types.find(type => MediaRecorder.isTypeSupported(type)) ?? '';
};
```

### Soluciona

- Evita forzar `audio/mp4` por ser mobile.
- Permite usar el mejor formato soportado por el navegador.
- Reduce fallos por formato especifico de Safari/iOS.

## 2. Separar MIME type de extension

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Codigo actual

```js
const ext = mimeType.includes('webm') ? 'webm'
        : mimeType.includes('ogg')  ? 'ogg'
        : mimeType.includes('mp4')  ? (isMobile ? 'm4a' : 'mp4')
        : isMobile ? 'm4a' : 'mp4';
```

### Cambio propuesto

Crear helper explicito.

```js
const getExtensionFromMimeType = (mimeType) => {
    if (mimeType.includes('webm')) return 'webm';
    if (mimeType.includes('ogg')) return 'ogg';
    if (mimeType.includes('mp4')) return 'mp4';
    if (mimeType.includes('aac')) return 'aac';
    return 'mp4';
};
```

Y usar:

```js
const ext = getExtensionFromMimeType(mimeType);
```

### Soluciona

- Evita convertir `audio/mp4` a `m4a` solo por ser mobile.
- Hace mas coherente la extension enviada al backend.
- Facilita depuracion de errores por formato.

## 3. Anadir soporte backend para AAC

### Archivo

`Api_Onorato/API/routes/onoratoFarm/transcription.py`

### Cambio propuesto

Ampliar `EXT_TO_MIME`.

```py
EXT_TO_MIME = {
    'webm': 'audio/webm',
    'ogg': 'audio/ogg',
    'mp4': 'audio/mp4',
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
}
```

### Soluciona

- Si el navegador devuelve `audio/aac`, backend no lo rechaza.
- Amplia compatibilidad sin romper formatos actuales.

## 4. Devolver razon cuando la transcripcion vuelve vacia

### Archivo

`Api_Onorato/API/routes/onoratoFarm/transcription.py`

### Codigo actual

```py
def _empty_transcription_response(reason, **details):
    logger.info("Empty/invalid audio ignored: %s | %s", reason, details)
    return jsonify({'ok': True, 'text': ''}), 200
```

### Cambio propuesto

```py
def _empty_transcription_response(reason, **details):
    logger.info("Empty/invalid audio ignored: %s | %s", reason, details)
    return jsonify({
        'ok': True,
        'text': '',
        'reason': reason,
        'details': details
    }), 200
```

### Soluciona

- Permite distinguir `too_short`, `openai_invalid_audio`, `unsupported_extension`, `invalid_base64`, etc.
- El frontend puede mostrar mensajes especificos.
- Evita esconder todos los fallos bajo "di o escribe algo".

## 5. Anadir debug de audio en frontend

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Cambio propuesto

Crear objeto de debug antes de validar/transcribir.

```js
const audioDebug = {
    isMobile,
    mimeType,
    recorderMimeType: recorder.mimeType,
    ext,
    blobSize: blob.size,
    blobType: blob.type,
    chunkCount,
    recordedDuration,
    chunkSizes: chunksRef.current.map(chunk => chunk.size),
    trackStates: streamRef.current?.getTracks().map(track => ({
        kind: track.kind,
        enabled: track.enabled,
        muted: track.muted,
        readyState: track.readyState
    })),
    userAgent: navigator.userAgent
};
```

Usarlo en `reportErrorToAdmin` cuando falle la captura o la transcripcion.

### Soluciona

- Confirma si iPhone genera blobs vacios.
- Permite distinguir permisos, formato, duracion, chunks y stream muerto.
- Da trazabilidad real del problema.

## 6. Validar que el stream sigue vivo antes de grabar

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Cambio propuesto

Anadir helper:

```js
const isUsableAudioStream = (stream) => {
    const tracks = stream?.getAudioTracks?.() ?? [];
    return tracks.some(track => track.readyState === 'live' && track.enabled);
};
```

Cambiar en `startRecording`:

```js
if (!stream) {
```

por:

```js
if (!isUsableAudioStream(stream)) {
```

### Soluciona

- Evita grabar con un `streamRef` viejo o muerto.
- Reduce bucles cuando Safari conserva una referencia JS pero el micro ya no funciona.

## 7. Reiniciar stream completo en mobile al repetir o fallar

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Cambio propuesto

Anadir helpers:

```js
const stopCurrentStream = () => {
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    if (parentMicStreamRef) parentMicStreamRef.current = null;
};

const requestFreshMicStream = async () => {
    stopCurrentStream();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    if (parentMicStreamRef) parentMicStreamRef.current = stream;
    setHasMicPermission(true);
    return stream;
};
```

En mobile/iPhone, al pulsar `Repetir` o tras fallo de audio, pedir un stream nuevo en vez de reutilizar `streamRef.current`.

```js
const stream = isMobile
    ? await requestFreshMicStream()
    : streamRef.current;

startRecording(stream);
```

### Soluciona

- Evita quedar atrapado con un stream roto.
- Cada retry en mobile parte de una captura fresca.
- Ayuda si iOS corta el track del microfono.

## 8. Contador de fallos de audio y fallback a texto

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Cambio propuesto

Anadir estados:

```js
const [audioFailureCount, setAudioFailureCount] = useState(0);
const [manualTextMode, setManualTextMode] = useState(false);
```

Cuando falle la senal de audio o la transcripcion vuelva vacia:

```js
setAudioFailureCount(prev => prev + 1);
```

Si en mobile falla dos veces:

```js
setManualTextMode(true);
setConfirmationInfo(true);
setText('');
```

### Soluciona

- Rompe el bucle.
- Permite continuar la charla aunque falle el microfono.
- Reduce bloqueo en iPhone/Safari.

## 9. Cambiar mensajes del modal

### Archivos

- `form_frontend-2/src/locales/es/translation.json`
- `form_frontend-2/src/locales/en/translation.json`

### Cambio propuesto ES

```json
"audio_capture_error": "No hemos podido captar el audio del microfono. Pulsa Repetir o escribe tu respuesta manualmente.",
"audio_capture_retry_error": "El microfono sigue sin captar audio. Puedes escribir tu respuesta para continuar."
```

### Cambio propuesto EN

```json
"audio_capture_error": "We couldn't capture audio from the microphone. Tap Repeat or type your answer manually.",
"audio_capture_retry_error": "The microphone still isn't capturing audio. You can type your answer to continue."
```

### Soluciona

- Mensaje mas honesto.
- Deja claro que la usuaria pudo haber hablado.
- Evita que soporte confunda fallo de micro con falta de respuesta.

## 10. Usar la razon del backend en frontend

### Archivo

`form_frontend-2/src/pages/onoratoFarm/FourPage.jsx`

### Cambio propuesto

Cuando `cleanedText` este vacio:

```js
reportErrorToAdmin(
    new Error('Empty transcription'),
    'FourPage.jsx',
    'transcription_empty',
    'WARN',
    {
        reason: transcribedText.reason,
        details: transcribedText.details,
        audioDebug
    }
);
```

### Soluciona

- Diferencia fallo frontend vs backend.
- Permite saber si OpenAI recibio audio invalido o si Safari no grabo.

## Orden recomendado

1. Anadir debug frontend y `reason` backend.
2. Cambiar mensajes del modal.
3. Validar stream vivo.
4. Reiniciar stream completo en mobile.
5. Cambiar deteccion MIME/extension.
6. Anadir fallback a texto tras dos fallos.

## Resultado esperado

- Si iPhone genera blob vacio, quedara registrado.
- Si OpenAI rechaza el audio, el frontend sabra la razon.
- Si el micro queda en estado inconsistente, se pedira un stream nuevo.
- Si el problema persiste, la usuaria podra escribir y continuar.
- El flujo dejara de quedarse atrapado en el modal generico.
