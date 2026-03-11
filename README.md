# 📘 Arquitectura de Observabilidad y Gestión de Errores - OnoratoAI (v2.0)

Este documento detalla el ecosistema integral de captura, manejo y reporte de errores en el Frontend de OnoratoAI. Define cómo las validaciones locales y las excepciones del sistema se transforman en datos accionables para el equipo de desarrollo.

---

## 1. Capa de Telemetría Forense (Crítica)
Esta capa registra fallos inesperados directamente en la base de datos de administración para diagnósticos post-mortem.

| Tipo de Fallo | Origen Técnico | Comportamiento en UI | Metadatos Capturados |
| :--- | :--- | :--- | :--- |
| **Render Crash** | `ErrorBoundary.jsx` | Bloqueo total. Muestra **Modal Rojo** con ID de error. | Stack Trace, Componente, Ruta, IP, Email, Device Info. |
| **JS/Logic Crash** | `window.onerror` | **Toast Negro** (4s): "Algo ha fallado en segundo plano". | Línea, Columna, Archivo, Parámetros URL, Estado Red. |
| **Promise Reject** | `unhandledrejection`| **Toast Negro**. Captura fallos de red o promesas no controladas. | Razón del rechazo, URL actual, IP, User Agent. |
| **API Fatal** | `api_functions.js` | El sistema registra el error 5xx antes de lanzar la excepción. | Endpoint, Payload keys, HTTP Status, Raw Response. |

### 🛡️ Mecanismos de Protección
* **Deduplicación (Anti-Spam):** Si un error con la misma firma ocurre en menos de **30 segundos**, el sistema lo silencia para evitar saturar la base de datos.
* **Seguridad de Datos:** Se registran las llaves (`keys`) del payload enviado pero **nunca los valores** sensibles (ej. se sabe que se envió un "password", pero no su contenido).
* **Identificación Única:** Cada reporte genera un `error_id` (Ej: `ERR-A1B2-C3D4`) vinculable en la base de datos.

---

## 2. Autenticación y Registro (Auth & Cognito)
**Rutas:** `/login`, `/register`, `/verify/:code`, `/recover`

### 2.1 Validaciones Locales (UX Preventiva)
| Causa | Clave de Error | Comportamiento UI |
| :--- | :--- | :--- |
| Campos vacíos | `emptyFields` | "Los campos están vacíos". Bloquea el submit. |
| Email inválido | `invalidEmail` | "El formato del correo no es correcto". |
| Password mismatch| `passwordsDoNotMatch`| "Las contraseñas no coinciden". |
| Requisitos PWD | `passwordMinLength` | Check visual (9+ chars, Mayús, Minús, Núm). |
| Nombre incompleto | `nameRequired` | "Debes incluir al menos nombre y primer apellido". |

### 2.2 Respuestas de API (Manejadas)
| Status | Error Backend | Reacción Frontend |
| :--- | :--- | :--- |
| **404** | `Email does not exist` | Mensaje rojo + Redirección automática a `/register`. |
| **403** | `accountNotVerified` | Abre Modal de verificación + Inicio de Polling. |
| **401** | `incorrectPassword` | "Contraseña incorrecta para este usuario". |
| **409** | `user exists` | "Este email ya está registrado". Redirige al login. |

---

## 3. Formularios Dinámicos y Onboarding
**Rutas:** `/form`

| Causa | Componente | Acción UI |
| :--- | :--- | :--- |
| Preguntas obligatorias | `WrongError` | Modal Overlay: "Tiene preguntas obligatorias sin responder". |
| Fallo Carga Form | `loadForm` (Catch) | Muestra botón de "Reintentar" en lugar del formulario. |
| Texto insuficiente | `minChars` | Contador dinámico en rojo bajo el input. |
| Sesión Expirada | `401 Unauthorized` | Ejecuta `removeToken()` y redirige a `/login`. |

---

## 4. Onorato Farm (IA y Multimedia)
**Rutas:** `/onoratoFarm`

### 4.1 Inteligencia Artificial y Audio
| Origen | Error | Comportamiento UI |
| :--- | :--- | :--- |
| **LLM / OpenAI** | Error 500 | "Hubo un error al obtener la respuesta de Onorato..." + Retry. |
| **Micrófono** | Permission Denied | Instrucciones visuales para activar micro en ajustes. |
| **Browser** | Unsupported | Modal: "Tu navegador no soporta grabación de audio". |

---

## 5. Glosario de Identificadores en Base de Datos
Cada log en la tabla `frontend_errors` se categoriza bajo estos tipos:

1.  **`RENDER_CRASH`**: Fallo fatal de la interfaz de React.
2.  **`JS_CRASH`**: Error de ejecución en scripts globales.
3.  **`PROMISE_CRASH`**: Fallo en operaciones asíncronas no controladas.
4.  **`API_CRITICAL_ERROR`**: Respuesta 5xx del servidor (Fallo backend).
5.  **`API_BUSINESS_WARNING`**: Errores 4xx (Lógica de negocio: 404, 400).
6.  **`API_401_WARNING`**: Sesión expirada o token inválido.
