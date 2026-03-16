# 🦜 Proyecto Onorato: Roadmap de Optimización de Sistemas y Atención Cognitiva

Este documento detalla las mejoras técnicas y arquitectónicas propuestas para fortalecer la proactividad del sistema de recordatorios y la calidad conversacional del agente de IA.

---

## 🚀 1. Sistema de Recordatorios Automatizados (CRON)
**Objetivo:** Automatizar el seguimiento de los usuarios para maximizar la tasa de finalización de las charlas.

### 🛠 Implementación Técnica
* **Ejecución:** Proceso diario programado en el servidor EC2 (08:30 AM).
* **Lógica de Negocio:** Disparo de alertas basado en hitos específicos (0%, 50%, 75% y retraso).
* **Infraestructura:** Integración directa con **AWS SES** para envíos masivos y cumplimiento de normativas de baja (Unsubscribe).

### 🛡 Blindaje de Errores
* **Centralización:** Integrado con el sistema de `AppError` de la API.
* **Trazabilidad:** Cada fallo genera un UUID único y notifica instantáneamente a los desarrolladores (`EMAIL_DEV`).
* **Logs:** Registro dual en base de datos y archivo de contingencia del sistema operativo.

---

## 🧠 2. Optimización del Agente: "Firmeza Amigable"
**Objetivo:** Transformar a Onorato de un "llenador de formularios" a un entrevistador empático que extrae información de calidad.

### 🔄 Cambios en la Estrategia NLP
| Estrategia | Descripción | Impacto |
| :--- | :--- | :--- |
| **Active Probing** | No acepta respuestas superficiales (monosílabos). | Información más rica en la base de datos. |
| **Conversational Bridging** | Valida desvíos de tema antes de redirigir. | Reducción de la frustración del usuario. |
| **Gentle Persistence** | Liderazgo suave de la conversación. | Asegura que todas las sub-preguntas sean respondidas. |

---

## 🎯 3. Arquitectura de Contexto Dinámico (Anti-Alucinaciones)
**Objetivo:** Resolver el problema de "Lost in the Middle" y reducir costes de tokens.



### 🚩 El Problema
Actualmente, el modelo recibe **~300 puntos de datos biográficos** en cada mensaje. Esto provoca:
1.  **Saturación:** La IA pierde atención en las instrucciones de formato.
2.  **Alucinaciones:** Mezcla datos irrelevantes (ej. confunde medicación con aficiones).
3.  **Coste:** Desperdicio de tokens de entrada en cada interacción.

### 🏗 La Solución: Inyección por Bloques
Se propone una lectura modular de los buckets de S3:
1.  **Bloque CORE:** Datos vitales (Nombre, edad, idioma) - *Siempre enviado*.
2.  **Bloques Temáticos:** (Salud, Familia, Pasado, Gustos) - *Solo se envía el bloque que coincide con la charla actual*.

**Resultado:** Reducción del 80% del ruido en el prompt y aumento drástico en la precisión de la respuesta.

---

## 📈 Beneficios para el Negocio
1.  **Escalabilidad:** El sistema podrá manejar miles de usuarios sin intervención manual.
2.  **Calidad del Dato:** La información extraída será mucho más profunda y estructurada.
3.  **Eficiencia de Costes:** Optimización del uso de la API de OpenAI (`gpt-4o-mini`).
4.  **UX Superior:** Interacciones más naturales y humanas para el adulto mayor.

---
*Preparado por el equipo de desarrollo - Marzo 2026*
