# Cambios en `reply_ai.py` para mejorar Onorato Dataset

## Objetivo

Mejorar la calidad de las respuestas de Onorato en el generador manual de dataset, haciendo que el loro responda de forma mas personalizada, coherente con el historial, emocionalmente adaptativa y util para una futura ronda de fine-tuning.

No se ha tocado el encoding ni se han corregido textos UTF-8 existentes.

## Cambios aplicados

### 1. Personal card convertida en guia accionable

Antes, el prompt recibia la `personal_card` casi en bruto. Ahora `build_personality_context()` transforma esa ficha en una guia compacta con:

- identidad: nombre, apodo, idioma, lugar, trabajo anterior, religion, mascotas;
- familia: hijos, nietos y personas importantes;
- conversacion: temas favoritos, temas a evitar, hobbies, deporte, museos y temas pendientes;
- rutinas: patrones relevantes de comidas, ejercicio, ocio, salud y vida social;
- estilo de recordatorio: ejemplos de mensajes ya personalizados.

Por que es mejor:

- reduce ruido para el modelo;
- evita que Onorato recite la ficha como datos sueltos;
- prioriza lo que realmente sirve para conversar;
- facilita que use detalles personales solo cuando encajan.

### 2. Limpieza de valores vacios

Se anadieron helpers como `clean_profile_value()`, `append_unique()`, `list_profile_values()` y `prune_empty()`.

Por que es mejor:

- elimina valores sin utilidad como `No answer`, `null`, listas vacias o campos sin contenido;
- evita que el prompt se llene de informacion falsa o poco natural;
- mejora la senal que recibe el modelo.

### 3. Mas contexto conversacional real

Antes `reply_ai.py` esperaba un historial con claves tipo `assistant` y `persona`, pero el admin envia mensajes como `{ role, content }`.

Ahora `flatten_conversation_context()` soporta ambos formatos:

- `{ role: "user", content: "..." }`;
- `{ role: "assistant", content: "..." }`;
- `{ assistant: "...", persona: "..." }`;
- `{ onorato: "...", user: "..." }`.

Tambien `format_conversation_context()` usa hasta 8 turnos recientes y limita el texto para no inflar demasiado el prompt.

Por que es mejor:

- Onorato ya no responde solo con los ultimos datos mal parseados;
- reduce contradicciones y repeticiones;
- permite mantener temas abiertos durante una conversacion larga;
- mejora la continuidad narrativa del dataset.

### 4. Eliminacion del mensaje actual duplicado

Cuando el ultimo mensaje del historial coincide con el `reply_user` actual, se elimina del contexto formateado para que el mensaje no aparezca dos veces.

Por que es mejor:

- evita que el modelo sobrepese el ultimo mensaje;
- reduce respuestas repetitivas;
- mantiene la llamada OpenAI mas limpia.

### 5. Deteccion local de intencion

Se anadio `detect_response_intent()` para clasificar el mensaje de la persona antes de construir el prompt.

Intenciones detectadas:

- `closing`;
- `greeting`;
- `autonomy_boundary`;
- `emotional_support`;
- `positive_moment`;
- `memory_sharing`;
- `routine_care`;
- `activity_request`;
- `factual_question`;
- `casual_conversation`.

Por que es mejor:

- el modelo recibe una estrategia clara antes de responder;
- mejora respuestas ante tristeza, cansancio, recuerdos, rutinas o despedidas;
- reduce respuestas genericamente amables que no atienden al contexto real;
- respeta mejor la autonomia de la persona mayor.

### 6. `finish_conversation` conectado al prompt

El parametro `finish_conversation` que llega desde el frontend ahora se guarda en `SupportDependencies` y se usa en la deteccion de intencion.

Por que es mejor:

- si el flujo marca cierre, Onorato responde como cierre;
- evita que abra nuevos temas cuando la conversacion debe acabar;
- mejora la calidad de conversaciones guardadas con cierre manual.

### 7. Prompt fijo separado del prompt dinamico

Se separo el prompt en:

- `ONORATO_STATIC_PROMPT`: identidad, mision, personalidad, tono, reglas generales y limites;
- `build_dynamic_prompt()`: personal card resumida, historial reciente, ultima respuesta e intencion detectada;
- `build_system_prompt()`: compone prompt fijo, ejemplos y parte dinamica.

Por que es mejor:

- hace el codigo mas mantenible;
- permite iterar la personalidad sin tocar la logica de contexto;
- permite ajustar el contexto dinamico sin reescribir la identidad de Onorato;
- facilita futuras pruebas A/B de prompt.

### 8. Ejemplos extraidos del dataset existente

Se reviso `OnoratoFarm/dataset/dataset.json` y se anadieron ejemplos de estilo en `DATASET_STYLE_EXAMPLES`.

Los ejemplos cubren:

- recuerdos personales;
- familia y nietos;
- autonomia de la persona;
- tono calido sin sonar tecnico.

Por que es mejor:

- los few-shot examples aterrizan el tono mejor que reglas abstractas;
- ayudan a que Onorato suene mas parecido al dataset real;
- reducen respuestas tipo asistente;
- refuerzan la brevedad y calidez que se quiere entrenar.

### 9. Reglas mas explicitas contra patrones malos

El prompt ahora insiste en:

- no recitar la ficha personal;
- no repetir literalmente lo que acaba de decir la persona;
- no cerrar siempre con una pregunta;
- no infantilizar;
- no mencionar IA, modelo, software o tecnologia;
- no dar ordenes;
- no generar urgencia salvo riesgo explicito.

Por que es mejor:

- ataca errores que degradan mucho un dataset de fine-tuning;
- evita que el modelo aprenda muletillas;
- mejora la naturalidad para TTS;
- hace que Onorato parezca companero, no chatbot.

## Resultado esperado

Estos cambios deberian mejorar especialmente:

- personalizacion por usuario;
- continuidad entre turnos;
- adaptacion emocional;
- respeto de autonomia;
- naturalidad conversacional;
- utilidad del dataset para fine-tuning.

Estimacion practica de mejora respecto al prompt inicial de esta sesion: 45-55% para el flujo manual de dataset.

## Recomendaciones antes de una ronda grande

Antes de generar muchas conversaciones, conviene hacer una tanda piloto de 5 a 10 conversaciones y revisar:

- si Onorato usa demasiado el nombre de la persona;
- si pregunta al final demasiado a menudo;
- si las respuestas se alargan;
- si respeta temas a evitar;
- si mantiene continuidad sin inventar;
- si los cierres son naturales.

Las siguientes mejoras recomendadas, aun no aplicadas, son:

- parser robusto para normalizar siempre el JSON de salida;
- modo dataset explicito para controlar mejor el estilo durante generacion manual;
- posible evaluador automatico simple para detectar respuestas largas, genericas o con menciones prohibidas.
