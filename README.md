# README_ERRORES_FRONTEND.md

Este documento detalla la arquitectura exhaustiva de captura, manejo y renderizado de errores en el Frontend de OnoratoAI. Define cómo las validaciones locales (antes de consumir la API) y las respuestas del servidor se traducen en mensajes y comportamientos específicos en la interfaz de usuario.

---

## 1. Autenticación, Registro y Verificación (Auth & Cognito)

**Rutas Principales:** `/login`, `/register`, `/verify/:code`, `/recover`

### 1.1 Validaciones Locales Previas (Pre-Petición HTTP)
El frontend bloquea peticiones al servidor si no se cumplen estos requisitos.

| Causa / Lógica Local | Clave de Error | Comportamiento UI / Mensaje | Archivo |
| :--- | :--- | :--- | :--- |
| Campos vacíos en Login | `emptyFields` | "Los campos están vacíos". Frena el submit. | `Login.jsx` |
| Email falla Regex (`^[^\s@]+@[^\s@]+\.[^\s@]+$`) | `invalidEmail` | "El formato del correo no es correcto" / "Formato de correo incorrecto". | `Login.jsx` / `Register.jsx` |
| `password !== confirmPassword` | `passwordsDoNotMatch` | "Las contraseñas no coinciden". | `Register.jsx` |
| Contraseña `< 9` caracteres | `passwordMinLength` | "La contraseña debe tener al menos 9 caracteres". Check visual (❌/✔️). | `Register.jsx` |
| Contraseña sin minúsculas | `passwordNeedsLowercase` | "Al menos una letra minúscula". Check visual (❌/✔️). | `Register.jsx` |
| Contraseña sin mayúsculas | `passwordNeedsUppercase` | "Al menos una letra mayúscula". Check visual (❌/✔️). | `Register.jsx` |
| Contraseña sin números | `passwordNeedsNumber` | "Al menos un número". Check visual (❌/✔️). | `Register.jsx` |
| Nombre con menos de 2 palabras (`validateName`) | `nameRequired` | "Debes incluir al menos nombre y primer apellido". | `Register.jsx` |
| Checkbox de privacidad no marcado | `acceptPolicy` | "Debes aceptar la política de datos". | `Register.jsx` |
| Preguntas de Onboarding sin responder | `requiredQuestions` | "No has contestado todas las preguntas obligatorias". Frena acceso a `/form`. | `Register.jsx` |

### 1.2 Errores de API (AWS Cognito / Backend)
Mapeo de respuestas de la API en el manejo de autenticación.

| Código / Excepción Backend | Clave de Error (JSON) | Acción / Comportamiento en UI | Archivo |
| :--- | :--- | :--- | :--- |
| **404** / `Email does not exist` | `emailNotExists` | Muestra error y redirige automáticamente a `/register` en 4 segundos. | `Login.jsx` / `RecoverPassword.jsx` |
| **403** / `User not confirmed` | `accountNotVerified` | Abre Modal (`showVerificationModal`) e inicia *polling* de verificación. | `Login.jsx` |
| **405** / `New password required` | (Abre componente) | Oculta Login y despliega `<TemporalPassword />` obligatorio. | `Login.jsx` |
| **401** / `Invalid password` | `incorrectPassword` | Muestra: "Contraseña incorrecta para este usuario". | `Login.jsx` / `Register.jsx` |
| **409** / `user exists` | `userExists` | "Este email ya está registrado". Redirige al login tras 1.5 seg. | `Register.jsx` |
| **403** / `no invitation found` | `noInvitationFound` | "No se ha encontrado una invitación para este correo". | `Register.jsx` |
| `LimitExceededException` | `limitExceeded` | Frena el modal/botón. En `VerifyPage` muestra vista de "Demasiados intentos". | `Login.jsx` / `VerifyPage.jsx` |
| `Invalid verification code`| `invalidCode` | "Código de recuperación inválido o expirado". | `Login.jsx` / `RecoverPassword.jsx` |
| Excepción desconocida | `generic` / `unknown` | En verificación muestra: "Error en la verificación... contacta con soporte." | `VerifyPage.jsx` / `Register.jsx` |

---

## 2. Formularios Dinámicos y Notificaciones

**Rutas Principales:** `/form`
**Componentes:** `FormComponent.jsx`, `NotifyPanel.jsx`

### 2.1 Validaciones Locales y Estados de UI
| Causa | Clave / Componente | Acción / Comportamiento en UI | Archivo |
| :--- | :--- | :--- | :--- |
| Enviar sin completar obligatorias (`obligatory === '1'`) | `WrongError = true` | Despliega modal (Overlay) central: "Tiene preguntas obligatorias sin responder". | `FormComponent.jsx` |
| Fallo general al cargar el formulario (`loadForm`) | Estado `error` | Reemplaza la UI por: `<div className="error"><p>Error: {error}</p> <button>Reintentar</button></div>` | `FormComponent.jsx` |
| Límite de texto no cumplido | `minChars` / `maxChars` | Muestra el recuento en rojo. | `little_text.jsx` |

### 2.2 Respuestas de la API al Guardar
| Estado API / Excepción | Método | Acción / Comportamiento en UI | Archivo |
| :--- | :--- | :--- | :--- |
| **400** | `sendFinishForm` | Lanza alerta nativa (`alert()`): "Error: El servidor no pudo procesar la solicitud. Contacta con soporte." | `FormComponent.jsx` |
| **Error Genérico / Red** | `sendFinishForm` | Lanza alerta nativa (`alert()`): "Error de conexión. Inténtalo de nuevo." | `FormComponent.jsx` |
| **401** / `Unauthorized` | `checkTokenMissing` | Interceptado a nivel componente. Fuerza redirección a `/login`. | `FormComponent.jsx` / `FormPage.jsx` |

---

## 3. Experiencia Onorato Farm (IA, 3D y Media)

**Rutas Principales:** `/onoratoFarm/*`
**Componentes:** `ModelOnorato3D.jsx`, `ThirdPage.jsx`, `FourPage.jsx`

### 3.1 Errores de Inteligencia Artificial (OpenAI / TTS)
| Estado API | Método / Excepción | Comportamiento UI | Componente |
| :--- | :--- | :--- | :--- |
| **500** | `errorLLM` / Fallo en `get_response` | Muestra un texto indicando: "Hubo un error al obtener la respuesta de Onorato..." y permite reintentar el fetch. | `ThirdPage.jsx` |

### 3.2 Errores de Hardware, Media y WebGL
| Origen | Clave | Comportamiento / Causa | Componente |
| :--- | :--- | :--- | :--- |
| **API Web** | `unsupported_browser` | La API de MediaRecorder falla (Navegador antiguo/sin soporte). Muestra modal de aviso. | `FourPage.jsx` |
| **API Web** | `microphone_permission_denied` | El usuario rechaza los permisos o iOS los bloquea. Muestra instrucciones para activar el micro en ajustes. | `FourPage.jsx` |
| **Local** | `empty_text_error` | Intento de enviar audio/texto vacío. Bloquea y pide escribir/hablar algo. | `FourPage.jsx` |
| **Motor 3D** | `Canvas / WebGL` | Si `Onorato3D.glb` falla al cargar, el componente `<Suspense>` lo maneja y se detiene (No hay render explícito de error, simplemente queda colgado el fallback). | `ModelOnorato3D.jsx` / `FormPage.jsx` |

---

## 4. Red Global y Excepciones Base

Centralizado en el contenedor global de peticiones.

**Archivo:** `functions/api_functions.js`

| Código de Estado HTTP | Tipo de Error Inyectado | Consecuencia en el Frontend |
| :--- | :--- | :--- |
| **0** (Sin Red) | `NetworkError` | Falla el bloque `fetch` por falta de internet o rechazo CORS. Lanza un throw procesado como "Error de conexión". |
| **401** | `Unauthorized` | Ejecuta limpieza: `removeToken()`. Genera evento global o en su defecto los componentes lo atrapan y ejecutan `Maps('/login')`. |
| **Respuestas No-JSON**| `ParseError` | Si el servidor devuelve un 502/504 en HTML, la app evita crashear y empaqueta el texto como un `Error(errorMessage)` estructurado. |
