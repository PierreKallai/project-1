Aquí tienes el Catálogo Maestro de Errores con el formato exacto que has solicitado, integrando la ubicación de cada error en el campo "Otra info".

Copia y pega este contenido en tu README.md.

Catálogo Maestro de Errores de la API
Este documento detalla todos los errores posibles en la ejecución de la API. Incluye la ubicación exacta en el código para facilitar la depuración.

1. Módulo de Identidad (Auth & Cognito)
Errores de Validación y Entrada
Status: 400

Nombre: MissingRequiredFields

Descripción: El cuerpo de la petición no contiene los campos necesarios (email, password, etc.).

Causa: Envío de JSON incompleto desde el frontend.

Data_importante: ['missing_keys']

Otra info: API/routes/user_identity/register.py (Línea ~29) / login.py (Línea ~40)

Status: 400

Nombre: InvalidEmailFormat

Descripción: El email no cumple con la estructura regex ^[\w\.-]+@[\w\.-]+\.\w+$.

Causa: Error tipográfico en el email.

Data_importante: ['email']

Otra info: API/routes/user_identity/login.py (Línea ~43) / register.py (Línea ~31)

Errores de Lógica de Negocio (Local)
Status: 403

Nombre: NoInvitationFound

Descripción: El email no está en la tabla de invitaciones (Sistema cerrado).

Causa: Usuario no invitado intentando registrarse.

Data_importante: ['email']

Otra info: API/routes/user_identity/register.py (Línea ~42)

Status: 409

Nombre: UserAlreadyExistsLocal

Descripción: El email ya existe en la base de datos MySQL local.

Causa: Intento de duplicar cuenta existente en local.

Data_importante: ['email']

Otra info: API/routes/user_identity/register.py (Línea ~35)

Errores de AWS Cognito (Autenticación)
Status: 401

Nombre: NotAuthorizedException

Descripción: Contraseña incorrecta o usuario no autorizado.

Causa: Login fallido por credenciales.

Data_importante: ['email']

Otra info: API/routes/user_identity/login.py (Línea ~125)

Status: 404

Nombre: UserNotFoundException

Descripción: El usuario no existe en el User Pool de AWS.

Causa: Login con email erróneo o desincronización BD/AWS.

Data_importante: ['email']

Otra info: API/routes/user_identity/login.py (Línea ~127)

Status: 403

Nombre: UserNotConfirmedException

Descripción: El usuario no ha verificado su email (estado UNCONFIRMED).

Causa: Login antes de verificar el código OTP.

Data_importante: ['email']

Otra info: API/routes/user_identity/login.py (Línea ~129)

Status: 405

Nombre: NewPasswordRequired

Descripción: El usuario debe cambiar su contraseña obligatoriamente.

Causa: Primer login de un usuario creado administrativamente.

Data_importante: ['session']

Otra info: API/routes/user_identity/login.py (Línea ~95)

Status: 400

Nombre: InvalidPasswordException

Descripción: La contraseña no cumple la política de seguridad (Números, Mayúsculas, Símbolos).

Causa: Registro o cambio de contraseña débil.

Data_importante: ['password_requirements']

Otra info: API/routes/user_identity/register.py (Línea ~68)

Status: 409

Nombre: UsernameExistsException

Descripción: El email ya existe en AWS Cognito.

Causa: Usuario existe en la nube pero quizás no en local.

Data_importante: ['email']

Otra info: API/routes/user_identity/register.py (Línea ~66)

Errores de Token (Middleware)
Status: 401

Nombre: TokenExpiredError

Descripción: El JWT ha caducado.

Causa: Sesión larga sin refrescar.

Data_importante: ['expired_at']

Otra info: API/functions/require_auth_hybrid.py (Línea ~108)

Status: 401

Nombre: InvalidTokenSignature

Descripción: La firma del token no coincide con la clave pública.

Causa: Token manipulado o incorrecto.

Data_importante: ['token']

Otra info: API/functions/require_auth_hybrid.py (Línea ~110)

Recuperación de Contraseña
Status: 400

Nombre: CodeMismatchException

Descripción: El código OTP de recuperación es incorrecto.

Causa: Error al teclear el código recibido por email.

Data_importante: ['confirmation_code']

Otra info: API/routes/user_identity/recover_password.py (Línea ~211)

Status: 400

Nombre: LimitExceededException

Descripción: Excedido el límite de intentos de envío de códigos.

Causa: Spam o demasiados reintentos en poco tiempo.

Data_importante: ['email']

Otra info: API/routes/user_identity/recover_password.py (Línea ~193)

2. Módulo de Pagos (Stripe)
Validaciones Propias
Status: 400

Nombre: InvalidPaymentData

Descripción: Email vacío o nombre demasiado corto (< 3 caracteres).

Causa: Validación previa a llamada a Stripe.

Data_importante: ['email', 'name']

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~55 y ~134)

Status: 400

Nombre: QuantityLimitExceeded

Descripción: Intento de comprar más de 1 unidad.

Causa: Restricción de negocio.

Data_importante: ['quantity']

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~137)

Status: 400

Nombre: DuplicatePurchase

Descripción: El usuario ya tiene una compra finalizada en BD.

Causa: Evitar cobros dobles.

Data_importante: ['email']

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~150)

Errores de la API de Stripe
Status: 500

Nombre: PaymentCreationError (Genérico)

Descripción: Fallo al crear el PaymentIntent. Actualmente capturado como Exception genérica.

Causa: Error de conexión o claves inválidas.

Data_importante: ['stripe_error']

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~215)

3. Módulo de IA (OpenAI)
Status: 500

Nombre: LLMProcessingError

Descripción: Error al procesar/parsear el JSON de respuesta de OpenAI.

Causa: La IA devuelve texto plano o formato inválido.

Data_importante: ['openai_response']

Otra info: API/routes/onoratoFarm/get_voice.py (Línea ~280)

Status: 500

Nombre: VoiceGenerationError

Descripción: Fallo al generar el audio (TTS).

Causa: Error en API de Audio de OpenAI (Timeout/Quota).

Data_importante: ['text_input']

Otra info: API/routes/onoratoFarm/get_voice.py (Línea ~335)

Status: 500

Nombre: AudioFileError

Descripción: Error al leer/guardar archivos de audio locales.

Causa: Problema de permisos o disco.

Data_importante: ['file_path']

Otra info: API/routes/onoratoFarm/get_voice.py (Línea ~370)

4. Módulo de Almacenamiento (S3)
Status: 403

Nombre: NoCredentialsError

Descripción: No se encuentran las claves AWS en variables de entorno.

Causa: Error de configuración del servidor.

Data_importante: ['env_vars']

Otra info: API/functions/buckets.py (Línea ~108)

Status: 200 (Devuelve lista vacía)

Nombre: NoSuchKey

Descripción: El archivo solicitado no existe en el bucket.

Causa: Usuario nuevo sin historial.

Data_importante: ['s3_path']

Otra info: API/functions/buckets.py (Línea ~112)

5. Auditoría de Mejoras (Errores No Contemplados)
Esta sección lista los errores que actualmente caen en bloques except Exception genéricos, pero que se recomienda implementar específicamente en el futuro.

Status: 402

Nombre: stripe.error.CardError

Descripción: Tarjeta rechazada o sin fondos.

Causa: Error de pago en Stripe.

Data_importante: ['stripe_code']

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~215) - Sustituir en create_payment_intent.

Status: 429

Nombre: stripe.error.RateLimitError

Descripción: Demasiadas peticiones a la pasarela de pago.

Causa: Pico de tráfico en Stripe.

Data_importante: N/A

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~215)

Status: 400

Nombre: stripe.error.InvalidRequestError

Descripción: Datos mal formados enviados a Stripe.

Causa: Error de integración.

Data_importante: N/A

Otra info: API/routes/stripe/create_and_check_payment.py (Línea ~215)

Status: 504

Nombre: openai.APITimeoutError

Descripción: La API tarda demasiado en responder.

Causa: Problemas en servidor de OpenAI.

Data_importante: N/A

Otra info: API/routes/onoratoFarm/get_voice.py (Línea ~335)

Status: 429

Nombre: openai.RateLimitError

Descripción: Se ha excedido la cuota de la API Key.

Causa: Límite de uso de OpenAI alcanzado.

Data_importante: N/A

Otra info: API/routes/onoratoFarm/get_voice.py (Línea ~335)

Status: 429

Nombre: client.exceptions.TooManyRequestsException

Descripción: Bloqueo de seguridad por intentos masivos.

Causa: Seguridad de AWS Cognito.

Data_importante: N/A

Otra info: API/routes/user_identity/login.py (Global try/except)

Status: 405

Nombre: client.exceptions.PasswordResetRequiredException

Descripción: El usuario necesita resetear contraseña obligatoriamente.

Causa: Flujo de cambio de password forzoso.

Data_importante: N/A

Otra info: API/routes/user_identity/login.py (Global try/except)

Status: 503

Nombre: botocore.exceptions.EndpointConnectionError

Descripción: Fallo de red al conectar con S3.

Causa: Problema de conectividad del servidor.

Data_importante: N/A

Otra info: API/functions/buckets.py (Línea ~112)
