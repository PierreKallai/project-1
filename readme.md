# Documentación de Errores de la API

Este documento cataloga todos los errores controlados por la API, organizados por módulo funcional.

---

## 1. Módulo de Identidad (Auth & Usuarios)

### Registro (Sign Up)
* **Status:** 400
* **Name:** `MissingFields`
* **Description:** Faltan campos obligatorios en el registro (email, password, name, last_name).
* **Casuistry:** Error de validación de formulario.
* **ImportantData:** `['missing_field']`

* **Status:** 409
* **Name:** `UserExists`
* **Description:** El usuario ya existe en la base de datos local o en Cognito.
* **Casuistry:** Intento de registro duplicado.
* **ImportantData:** `['email']`

* **Status:** 403
* **Name:** `NoInvitationFound`
* **Description:** El email no tiene una invitación válida en el sistema. El registro es solo por invitación.
* **Casuistry:** Usuario no invitado intentando registrarse.
* **ImportantData:** `['email']`

### Login
* **Status:** 401
* **Name:** `NotAuthorizedException`
* **Description:** Credenciales incorrectas (email o contraseña).
* **Casuistry:** Fallo de autenticación.
* **ImportantData:** `['email']`

* **Status:** 404
* **Name:** `UserNotFoundException`
* **Description:** El usuario no existe.
* **Casuistry:** Login con email erróneo.
* **ImportantData:** `['email']`

* **Status:** 403
* **Name:** `UserNotConfirmedException`
* **Description:** El usuario no ha verificado su email mediante el código OTP.
* **Casuistry:** Intento de login antes de verificar cuenta.
* **ImportantData:** `['email']`

### Recuperación de Contraseña
* **Status:** 400
* **Name:** `CodeMismatchException`
* **Description:** El código de recuperación introducido es incorrecto.
* **Casuistry:** Error tipográfico del usuario.
* **ImportantData:** `['code']`

* **Status:** 400
* **Name:** `LimitExceededException`
* **Description:** Demasiados intentos de solicitud de código. Bloqueo temporal de AWS.
* **Casuistry:** Spam de botón "Reenviar código".
* **ImportantData:** `['email']`

---

## 2. Módulo de Pagos (Stripe)

### Datos de Compra Inválidos
* **Status:** 400
* **Name:** `InvalidPaymentData`
* **Description:** El email es inválido o el nombre es demasiado corto (< 3 caracteres).
* **Casuistry:** Validación inicial antes de contactar con Stripe.
* **ImportantData:** `['email', 'name']`

### Límite de Cantidad Excedido
* **Status:** 400
* **Name:** `QuantityLimitExceeded`
* **Description:** Se intenta comprar más de 1 unidad por transacción (limitado por lógica de negocio).
* **Casuistry:** Usuario manipula el frontend para comprar más.
* **ImportantData:** `['quantity']`

### Compra Duplicada
* **Status:** 400
* **Name:** `DuplicatePurchase`
* **Description:** Este email ya tiene una compra finalizada (`status='succeeded'`) en la base de datos.
* **Casuistry:** Usuario intentando comprar de nuevo con el mismo correo.
* **ImportantData:** `['email']`

### Error en Pasarela de Pago
* **Status:** 500
* **Name:** `StripePaymentError`
* **Description:** Fallo al crear el `PaymentIntent` en Stripe.
* **Casuistry:** Problema de conexión con Stripe o configuración de API Keys inválida.
* **ImportantData:** `['stripe_error_message']`

---

## 3. Módulo IA y Voz (OnoratoFarm)

### Error de Generación de Respuesta (LLM)
* **Status:** 500
* **Name:** `LLMProcessingError`
* **Description:** Error al procesar la respuesta del modelo GPT (OpenAI). Puede ser un fallo de parsing JSON o timeout.
* **Casuistry:** La IA devuelve texto plano en lugar de JSON o la API de OpenAI falla.
* **ImportantData:** `['openai_error']`

### Error de Generación de Voz (TTS)
* **Status:** 500
* **Name:** `VoiceGenerationError`
* **Description:** Fallo al convertir texto a voz usando el modelo `gpt-4o-mini-tts`.
* **Casuistry:** Error en la API de Audio de OpenAI.
* **ImportantData:** `['text_input']`

---

## 4. Módulo de Almacenamiento (S3)

### Credenciales AWS Faltantes
* **Status:** 403
* **Name:** `NoCredentialsError`
* **Description:** El servidor no tiene configuradas las claves de acceso a S3.
* **Casuistry:** Error de despliegue o variables de entorno (`.env`).
* **ImportantData:** `['AWS_ACCESS_KEY_ID']`

### Archivo No Encontrado
* **Status:** 200 (Devuelve lista vacía)
* **Name:** `NoSuchKey`
* **Description:** Se solicita un JSON o recurso que no existe en el Bucket del usuario.
* **Casuistry:** Primer acceso de un usuario nuevo.
* **ImportantData:** `['s3_key']`

---

## 5. Errores Generales

### Error Interno del Servidor
* **Status:** 500
* **Name:** `InternalServerError`
* **Description:** Excepción no controlada en cualquier parte del código.
* **Casuistry:** Bug imprevisto. Se registra en `app-errors.log`.
* **ImportantData:** `['traceback', 'timestamp']`
