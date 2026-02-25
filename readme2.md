# Catálogo Maestro de Errores de la API

Este documento detalla **todos** los errores posibles en la ejecución de la API, incluyendo errores de validación, lógica de negocio, fallos de infraestructura y excepciones de proveedores externos (AWS, Stripe, OpenAI).

---

## 1. Módulo de Identidad (Auth & Cognito)
**Archivos:** `login.py`, `register.py`, `recover_password.py`, `require_auth_hybrid.py`

### Errores de Validación y Entrada
* **Status:** 400
* **Name:** `MissingRequiredFields`
* **Description:** El cuerpo de la petición no contiene los campos necesarios (email, password, etc.).
* **Casuistry:** Envío de JSON incompleto.
* **ImportantData:** `['missing_keys']`

* **Status:** 400
* **Name:** `InvalidEmailFormat`
* **Description:** El email no cumple con la estructura regex `^[\w\.-]+@[\w\.-]+\.\w+$`.
* **Casuistry:** Error tipográfico en el email.
* **ImportantData:** `['email']`

### Errores de Lógica de Negocio (Local)
* **Status:** 403
* **Name:** `NoInvitationFound`
* **Description:** El email no está en la tabla de invitaciones (Sistema cerrado).
* **Casuistry:** Usuario no invitado intentando registrarse.
* **ImportantData:** `['email']`

* **Status:** 409
* **Name:** `UserAlreadyExistsLocal`
* **Description:** El email ya existe en la base de datos MySQL local.
* **Casuistry:** Intento de duplicar cuenta.
* **ImportantData:** `['email']`

### Errores de AWS Cognito (Autenticación)
* **Status:** 401
* **Name:** `NotAuthorizedException`
* **Description:** Contraseña incorrecta o usuario no autorizado.
* **Casuistry:** Login fallido.
* **ImportantData:** `['email']`

* **Status:** 404
* **Name:** `UserNotFoundException`
* **Description:** El usuario no existe en el User Pool de AWS.
* **Casuistry:** Login con email erróneo o usuario borrado en AWS pero no en local.
* **ImportantData:** `['email']`

* **Status:** 403
* **Name:** `UserNotConfirmedException`
* **Description:** El usuario no ha verificado su email (estado UNCONFIRMED).
* **Casuistry:** Login antes de verificar el código OTP.
* **ImportantData:** `['email']`

* **Status:** 405
* **Name:** `PasswordResetRequiredException` / `NewPasswordRequired`
* **Description:** El usuario debe cambiar su contraseña obligatoriamente (creado por admin).
* **Casuistry:** Primer login de un usuario administrativo.
* **ImportantData:** `['session']`

* **Status:** 400
* **Name:** `InvalidPasswordException`
* **Description:** La contraseña no cumple la política de seguridad (Números, Mayúsculas, Símbolos).
* **Casuistry:** Registro o cambio de contraseña débil.
* **ImportantData:** `['password_requirements']`

* **Status:** 429
* **Name:** `TooManyRequestsException`
* **Description:** Bloqueo temporal de AWS por exceso de intentos.
* **Casuistry:** Ataque de fuerza bruta o usuario insistente.
* **ImportantData:** `['retry_after']`

### Errores de Token (Middleware)
* **Status:** 401
* **Name:** `TokenExpiredError`
* **Description:** El JWT ha caducado.
* **Casuistry:** Sesión larga sin refrescar.
* **ImportantData:** `['expired_at']`

* **Status:** 401
* **Name:** `InvalidTokenSignature`
* **Description:** La firma del token no coincide con la clave pública de Cognito o la API Key.
* **Casuistry:** Token manipulado o incorrecto.
* **ImportantData:** `['token']`

---

## 2. Módulo de Pagos (Stripe)
**Archivo:** `create_and_check_payment.py`

### Validaciones Propias
* **Status:** 400
* **Name:** `InvalidPaymentData`
* **Description:** Email vacío o nombre demasiado corto (< 3 caracteres).
* **Casuistry:** Validación previa a Stripe.
* **ImportantData:** `['email', 'name']`

* **Status:** 400
* **Name:** `QuantityLimitExceeded`
* **Description:** Intento de comprar más de 1 unidad (Loro).
* **Casuistry:** Restricción de negocio.
* **ImportantData:** `['quantity']`

* **Status:** 400
* **Name:** `DuplicatePurchase`
* **Description:** El usuario ya tiene una compra finalizada (`succeeded`) en BD.
* **Casuistry:** Evitar cobros dobles.
* **ImportantData:** `['email']`

### Errores de la API de Stripe (Potenciales)
*(Estos errores ocurren dentro del `try/except` general de pagos)*

* **Status:** 402
* **Name:** `CardError`
* **Description:** La tarjeta fue rechazada (fondos insuficientes, caducada, bloqueo de banco).
* **Casuistry:** Fallo en el pago.
* **ImportantData:** `['stripe_decline_code']`

* **Status:** 429
* **Name:** `RateLimitError`
* **Description:** Demasiadas peticiones a la API de Stripe en poco tiempo.
* **Casuistry:** Pico de tráfico de ventas.
* **ImportantData:** `[]`

* **Status:** 500
* **Name:** `StripeAPIError`
* **Description:** Error interno en los servidores de Stripe.
* **Casuistry:** Caída del servicio de Stripe.
* **ImportantData:** `['stripe_status']`

---

## 3. Módulo de IA (OpenAI)
**Archivo:** `get_voice.py`

* **Status:** 500
* **Name:** `ContextLengthExceeded`
* **Description:** La conversación es demasiado larga para el modelo (token limit).
* **Casuistry:** Chats muy extensos sin limpieza de contexto.
* **ImportantData:** `['token_usage']`

* **Status:** 429
* **Name:** `OpenAIRateLimitError`
* **Description:** Se ha excedido la cuota de uso de la API Key o el límite de RPM (Requests Per Minute).
* **Casuistry:** Cuenta de OpenAI sin saldo o sobrecargada.
* **ImportantData:** `['api_key_status']`

* **Status:** 500
* **Name:** `LLMOutputParsingError`
* **Description:** El modelo no devolvió un JSON válido como se le instruyó.
* **Casuistry:** "Alucinación" del modelo devolviendo texto plano.
* **ImportantData:** `['raw_response']`

* **Status:** 500
* **Name:** `VoiceGenerationError`
* **Description:** Fallo al generar el audio (TTS) o guardar el archivo.
* **Casuistry:** Error en API de Audio o sistema de archivos lleno/protegido.
* **ImportantData:** `['text_input']`

---

## 4. Módulo de Almacenamiento (S3)
**Archivo:** `buckets.py`

* **Status:** 403
* **Name:** `NoCredentialsError`
* **Description:** No se encuentran las claves AWS_ACCESS_KEY_ID en las variables de entorno.
* **Casuistry:** Error de configuración del servidor.
* **ImportantData:** `['env_vars']`

* **Status:** 404 / 200 (Empty)
* **Name:** `NoSuchKey`
* **Description:** El archivo solicitado no existe en el bucket.
* **Casuistry:** Usuario nuevo sin historial.
* **ImportantData:** `['s3_path']`

* **Status:** 500
* **Name:** `S3ConnectionError`
* **Description:** Fallo de red al intentar conectar con AWS S3.
* **Casuistry:** Problemas de DNS o red en el servidor.
* **ImportantData:** `['endpoint_url']`

---

## 5. Base de Datos (MySQL)
**Archivo:** `db_connection.py` (y todos los endpoints)

* **Status:** 500
* **Name:** `OperationalError`
* **Description:** No se puede conectar a la base de datos MySQL.
* **Casuistry:** Base de datos caída, credenciales incorrectas o firewall bloqueando.
* **ImportantData:** `['db_host']`

* **Status:** 500
* **Name:** `IntegrityError`
* **Description:** Violación de restricciones SQL (Foreign Key no existe, campo único duplicado no controlado).
* **Casuistry:** Error de integridad de datos.
* **ImportantData:** `['sql_query']`

---

## 6. Error General (Catch-All)
**Archivo:** `app.py` (Global Handler)

* **Status:** 500
* **Name:** `InternalServerError`
* **Description:** Cualquier excepción no controlada por los casos anteriores.
* **Casuistry:** Bugs de código, librerías faltantes, errores de sintaxis en runtime.
* **ImportantData:** `['stack_trace', 'timestamp']`
