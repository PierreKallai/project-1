# Catálogo Maestro de Errores de la API

Este documento detalla **todos** los errores posibles en la ejecución de la API. Incluye la ubicación exacta en el código para facilitar la depuración.

---

## 1. Módulo de Identidad (Auth & Cognito)

### Errores de Validación y Entrada
* **Status:** 400
* **Name:** `MissingRequiredFields`
* **Location:** `API/routes/user_identity/register.py` (Línea ~29) / `login.py` (Línea ~40)
* **Description:** El cuerpo de la petición no contiene los campos necesarios (email, password, etc.).
* **Casuistry:** Envío de JSON incompleto desde el frontend.
* **ImportantData:** `['missing_keys']`

* **Status:** 400
* **Name:** `InvalidEmailFormat`
* **Location:** `API/routes/user_identity/login.py` (Línea ~43) / `register.py` (Línea ~31)
* **Description:** El email no cumple con la estructura regex `^[\w\.-]+@[\w\.-]+\.\w+$`.
* **Casuistry:** Error tipográfico en el email.
* **ImportantData:** `['email']`

### Errores de Lógica de Negocio (Local)
* **Status:** 403
* **Name:** `NoInvitationFound`
* **Location:** `API/routes/user_identity/register.py` (Línea ~42)
* **Description:** El email no está en la tabla de invitaciones (Sistema cerrado).
* **Casuistry:** Usuario no invitado intentando registrarse.
* **ImportantData:** `['email']`

* **Status:** 409
* **Name:** `UserAlreadyExistsLocal`
* **Location:** `API/routes/user_identity/register.py` (Línea ~35)
* **Description:** El email ya existe en la base de datos MySQL local.
* **Casuistry:** Intento de duplicar cuenta existente en local.
* **ImportantData:** `['email']`

### Errores de AWS Cognito (Autenticación)
* **Status:** 401
* **Name:** `NotAuthorizedException`
* **Location:** `API/routes/user_identity/login.py` (Línea ~125)
* **Description:** Contraseña incorrecta o usuario no autorizado.
* **Casuistry:** Login fallido por credenciales.
* **ImportantData:** `['email']`

* **Status:** 404
* **Name:** `UserNotFoundException`
* **Location:** `API/routes/user_identity/login.py` (Línea ~127)
* **Description:** El usuario no existe en el User Pool de AWS.
* **Casuistry:** Login con email erróneo o desincronización BD/AWS.
* **ImportantData:** `['email']`

* **Status:** 403
* **Name:** `UserNotConfirmedException`
* **Location:** `API/routes/user_identity/login.py` (Línea ~129)
* **Description:** El usuario no ha verificado su email (estado UNCONFIRMED).
* **Casuistry:** Login antes de verificar el código OTP.
* **ImportantData:** `['email']`

* **Status:** 405
* **Name:** `NewPasswordRequired`
* **Location:** `API/routes/user_identity/login.py` (Línea ~95)
* **Description:** El usuario debe cambiar su contraseña obligatoriamente.
* **Casuistry:** Primer login de un usuario creado administrativamente.
* **ImportantData:** `['session']`

* **Status:** 400
* **Name:** `InvalidPasswordException`
* **Location:** `API/routes/user_identity/register.py` (Línea ~68)
* **Description:** La contraseña no cumple la política de seguridad (Números, Mayúsculas, Símbolos).
* **Casuistry:** Registro o cambio de contraseña débil.
* **ImportantData:** `['password_requirements']`

* **Status:** 409
* **Name:** `UsernameExistsException`
* **Location:** `API/routes/user_identity/register.py` (Línea ~66)
* **Description:** El email ya existe en AWS Cognito.
* **Casuistry:** Usuario existe en la nube pero quizás no en local.
* **ImportantData:** `['email']`

### Errores de Token (Middleware)
* **Status:** 401
* **Name:** `TokenExpiredError`
* **Location:** `API/functions/require_auth_hybrid.py` (Línea ~108)
* **Description:** El JWT ha caducado.
* **Casuistry:** Sesión larga sin refrescar.
* **ImportantData:** `['expired_at']`

* **Status:** 401
* **Name:** `InvalidTokenSignature`
* **Location:** `API/functions/require_auth_hybrid.py` (Línea ~110)
* **Description:** La firma del token no coincide con la clave pública.
* **Casuistry:** Token manipulado o incorrecto.
* **ImportantData:** `['token']`

---

## 2. Módulo de Pagos (Stripe)

### Validaciones Propias
* **Status:** 400
* **Name:** `InvalidPaymentData`
* **Location:** `API/routes/stripe/create_and_check_payment.py` (Línea ~55 y ~134)
* **Description:** Email vacío o nombre demasiado corto (< 3 caracteres).
* **Casuistry:** Validación previa a llamada a Stripe.
* **ImportantData:** `['email', 'name']`

* **Status:** 400
* **Name:** `QuantityLimitExceeded`
* **Location:** `API/routes/stripe/create_and_check_payment.py` (Línea ~137)
* **Description:** Intento de comprar más de 1 unidad.
* **Casuistry:** Restricción de negocio.
* **ImportantData:** `['quantity']`

* **Status:** 400
* **Name:** `DuplicatePurchase`
* **Location:** `API/routes/stripe/create_and_check_payment.py` (Línea ~150)
* **Description:** El usuario ya tiene una compra finalizada en BD.
* **Casuistry:** Evitar cobros dobles.
* **ImportantData:** `['email']`

### Errores de la API de Stripe
* **Status:** 500
* **Name:** `PaymentCreationError` (Genérico)
* **Location:** `API/routes/stripe/create_and_check_payment.py` (Línea ~215)
* **Description:** Fallo al crear el PaymentIntent. Actualmente capturado como Exception genérica.
* **Casuistry:** Error de conexión o claves inválidas.
* **ImportantData:** `['stripe_error']`

---

## 3. Módulo de IA (OpenAI)

* **Status:** 500
* **Name:** `LLMProcessingError`
* **Location:** `API/routes/onoratoFarm/get_voice.py` (Línea ~280)
* **Description:** Error al procesar/parsear el JSON de respuesta de OpenAI.
* **Casuistry:** La IA devuelve texto plano o formato inválido.
* **ImportantData:** `['openai_response']`

* **Status:** 500
* **Name:** `VoiceGenerationError`
* **Location:** `API/routes/onoratoFarm/get_voice.py` (Línea ~335)
* **Description:** Fallo al generar el audio (TTS).
* **Casuistry:** Error en API de Audio de OpenAI.
* **ImportantData:** `['text_input']`

* **Status:** 500
* **Name:** `AudioFileError`
* **Location:** `API/routes/onoratoFarm/get_voice.py` (Línea ~370)
* **Description:** Error al leer/guardar archivos de audio locales.
* **Casuistry:** Problema de permisos o disco.
* **ImportantData:** `['file_path']`

---

## 4. Módulo de Almacenamiento (S3)

* **Status:** 403
* **Name:** `NoCredentialsError`
* **Location:** `API/functions/buckets.py` (Línea ~108)
* **Description:** No se encuentran las claves AWS en variables de entorno.
* **Casuistry:** Error de configuración del servidor.
* **ImportantData:** `['env_vars']`

* **Status:** 200 (Empty List)
* **Name:** `NoSuchKey`
* **Location:** `API/functions/buckets.py` (Línea ~112)
* **Description:** El archivo solicitado no existe en el bucket.
* **Casuistry:** Usuario nuevo sin historial.
* **ImportantData:** `['s3_path']`

---

## 5. Auditoría de Mejoras (Errores No Contemplados)

Esta sección lista los errores que **actualmente** caen en bloques `except Exception` genéricos pero que **deben implementarse** en el futuro para una gestión más precisa.

### Archivo: `API/routes/stripe/create_and_check_payment.py` (Línea ~215)
Se recomienda sustituir el `except Exception` por:
1. **`stripe.error.CardError`** (Status 402): Tarjeta rechazada o sin fondos.
2. **`stripe.error.RateLimitError`** (Status 429): Demasiadas peticiones a la pasarela.
3. **`stripe.error.InvalidRequestError`** (Status 400): Datos mal formados enviados a Stripe.

### Archivo: `API/routes/onoratoFarm/get_voice.py` (Línea ~335)
Se recomienda capturar específicamente:
1. **`openai.APITimeoutError`** (Status 504): La API tarda en responder.
2. **`openai.RateLimitError`** (Status 429): Cuota de OpenAI excedida.

### Archivo: `API/routes/user_identity/login.py` (Global try/except)
Se recomienda añadir:
1. **`client.exceptions.TooManyRequestsException`** (Status 429): Bloqueo de seguridad AWS.
2. **`client.exceptions.PasswordResetRequiredException`** (Status 405): Flujo de reseteo obligatorio.

### Archivo: `API/functions/buckets.py` (Línea ~112)
Se recomienda añadir:
1. **`botocore.exceptions.EndpointConnectionError`** (Status 503): Fallo de red al conectar con S3.
