# Resumen de Correcciones Técnicas - Frontend

A continuación se detalla la causa raíz y la solución implementada para cada uno de los bugs reportados. Este documento sirve como guía técnica para explicar los cambios durante la reunión.

## 1. Bug: El error "Unauthorized" no redirigía al Login (Punto 4)
**Causa raíz:** 
El componente padre (`FormPage.jsx`) estaba preparado para redirigir al login únicamente si recibía de forma literal el mensaje de error `'Unauthorized: token missing or expired'`. Sin embargo, dentro de `OnoratoFarm.jsx`, las funciones de la API (`loadQuestionsAndAudio`, `finishChatCheck`, `getInfoUser`) estaban interceptando el error de red (401) en sus bloques `try/catch` y sobrescribiéndolo con mensajes de error genéricos y traducidos (ej. "Error al generar el audio") antes de propagarlo hacia arriba.

**Solución implementada:** 
Se implementó un *guard* al principio de los `catch` en las llamadas afectadas. Antes de establecer el mensaje de error genérico, se verifica si el error original es de tipo *Unauthorized*. Si lo es, se propaga el mensaje exacto mediante un *early return*, lo que permite a `FormPage.jsx` capturarlo correctamente y forzar la redirección a la ruta de `/login`.

---

## 2. Bug: La pantalla de carga "Loro" desaparecía antes de que el modelo 3D renderizase (Punto 6)
**Causa raíz:**
En `FormPage.jsx`, la visibilidad del componente `<LoadingScreen />` estaba acoplada erróneamente a la variable de estado `loading` de las llamadas a la API. Como los datos de la API resolvían muy rápido, el estado pasaba a `false` y desmontaba la pantalla de carga de inmediato, mucho antes de que React Three Fiber (el motor 3D) terminase de cargar y renderizar los assets pesados del modelo del loro.

**Solución implementada:**
Se ha desacoplado la lógica de montado en el padre. Ahora `FormPage.jsx` mantiene vivo el `<LoadingScreen />` con la condición `showFeedbackOnoratoFarm`, que significa que siempre que exista el canvas 3D, la pantalla de carga existirá. Hemos delegado la responsabilidad de ocultarse al propio `<LoadingScreen />`, que utilizando el hook `useProgress()` interno del motor 3D, se encarga de vigilar el progreso de carga y se oculta automáticamente solo cuando el progreso es del 100%.

---

## 3. Bug: Pantalla en blanco en charlas al volver de la página 4 a la 3 (Punto 7)
**Causa raíz:** 
Existía una inconsistencia en la lógica de navegación interna hacia atrás en `FourPage.jsx`. Al pulsar en el botón de confirmar grabación/texto, el sistema levantaba un flag (`setComeToFourPage(true)`) antes de volver; sin embargo, al pulsar la flecha nativa de "Atrás" en la cabecera, se volvía a la página 3 sin levantar dicho flag. Debido a esto, cuando `ThirdPage.jsx` procesaba el buffer secuencial para decidir qué renderizar o qué reproducir, al no ver el flag activo asumía que no debía regenerar nada y la pantalla quedaba colgada en blanco.

**Solución implementada:** 
Se modificó el evento del botón de "Atrás" (flecha del `HeaderOnoratoFarm`) en `FourPage.jsx` para homogeneizar este flujo. Ahora también ejecuta consistentemente `setComeToFourPage(true)` antes de llamar a la función que retrocede en la paginación de los formularios, forzando correctamente al montado de `ThirdPage.jsx` a identificar de dónde proviene la visita para relanzar la pregunta y su audio.

---

## 4. Bug: Incoherencia en los Porcentajes de Carga Visualizados (Punto 1)
**Causa raíz:** 
Había introducida una "Condición de carrera" (Race condition) de estados. En el nivel superior `FormPage.jsx`, un *useEffect* se dedicaba a monitorear y calcular automáticamente el porcentaje de estado global, promediando matemáticamente el avance de las 4 categorías del cuestionario, y sobrescribiendo la llave estática de estado de finalización del usuario. En el nivel inferior `OnoratoFarm.jsx`, un código nativo también luchaba para hacer visible el avance correcto haciendo ($Respondidas/Totales * 100$). En el combate entre ambos flujos de datos el `FormPage.jsx` ganaba las actualizaciones resultando en visualizaciones corruptas.

**Solución implementada:**
Se implementó un patrón de salvaguarda defensiva mediante retorno primario (`if(showFeedbackOnoratoFarm) return;`) al comienzo del hook sobreescribiente del componente global que calcula el promedio cuaternario. Mediante este fix se garantiza que los cambios reactivos del nivel nativo OnoratoFarm tengan delegada la posesión absoluta del render en ese momento.

---

## 5. Mejora de Integración: Sintaxis rota en closure JSX (Código visualmente transparente)
**Causa raíz:** 
En el archivo `OnoratoFarm.jsx`, existía un error de sintaxis ("syntax leakage") heredado, en el closure y llaves de la función asíncrona de parseo `generateAudio()`. Esta función abría su llave nativa, iniciaba su Try/Catch transaccional y cerraba con `};` el Try/Catch erróneamente en vez del control padre, lo cual introducía un error severo en el analizador estático o AST. El intérprete asumía que la mayoría del código subyacente de todo el componente quedaba lógicamente mal anidado como closure descendiente.

**Solución implementada:**
Se restauró el balance y acople tipográfico, insertando la clausura original para la finalización transaccional y desplazando la llave madre `};` debajo. Esto restaura los warnings del *linter* y garantiza que el comportamiento del ámbito del runtime y variables de Javascript recupere su formato óptimo.
