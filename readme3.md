#Errores de la API



---

## 1.(Auth & Cognito)

**`API/routes/user_identity/`**

### Errores de Validación y Lógica
| Estado | Nombre | Descripción | Causa | Data Importante | archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `MissingRequiredFields` | El cuerpo de la petición no contiene los campos necesarios. | Envío de JSON incompleto desde el frontend. | `['missing_keys']` | `register.py`: ~29 <br> `login.py`: ~40 |
| **400** | `InvalidEmailFormat` | El email no cumple con la estructura regex estándar. | Error tipográfico en el email (`^[\w\.-]+@[\w\.-]+\.\w+$`). | `['email']` | `login.py`: ~43 <br> `register.py`: ~31 |
| **403** | `NoInvitationFound` | El email no está en la tabla de invitaciones. | Usuario no invitado intentando registrarse (Sistema cerrado). | `['email']` | `register.py`: ~42 |
| **409** | `UserAlreadyExistsLocal` | El email ya existe en la base de datos MySQL local. | Intento de duplicar cuenta existente en local. | `['email']` | `register.py`: ~35 |

### Errores de AWS Cognito (Autenticación)
| Estado | Nombre | Descripción | Causa | Data Importante | archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **401** | `NotAuthorizedException` | Contraseña incorrecta o usuario no autorizado. | Login fallido por credenciales inválidas. | `['email']` | `login.py`: ~125 |
| **404** | `UserNotFoundException` | El usuario no existe en el User Pool de AWS. | Login con email erróneo o desincronización BD/AWS. | `['email']` | `login.py`: ~127 |
| **403** | `UserNotConfirmedException` | El usuario no ha verificado su email (estado UNCONFIRMED). | Login antes de verificar el código OTP. | `['email']` | `login.py`: ~129 |
| **405** | `NewPasswordRequired` | El usuario debe cambiar su contraseña obligatoriamente. | Primer login de un usuario creado administrativamente. | `['session']` | `login.py`: ~95 |
| **400** | `InvalidPasswordException` | La contraseña no cumple la política de seguridad. | Registro con pass débil (Faltan mayúsculas, números, símbolos). | `['requirements']` | `register.py`: ~68 |
| **409** | `UsernameExistsException` | El email ya existe en AWS Cognito. | Usuario existe en la nube pero quizás no en local. | `['email']` | `register.py`: ~66 |

### Recuperación y Tokens
| Estado | Nombre | Descripción | Causa | Data Importante | archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `CodeMismatchException` | El código OTP de recuperación es incorrecto. | Error al teclear el código recibido por email. | `['code']` | `recover_password.py`: ~211 |
| **400** | `LimitExceededException` | Excedido el límite de intentos de envío de códigos. | Spam o demasiados reintentos en poco tiempo. | `['email']` | `recover_password.py`: ~193 |
| **401** | `TokenExpiredError` | El token JWT ha caducado. | Sesión larga sin refrescar. | `['expired_at']` | `require_auth_hybrid.py`: ~108 |
| **401** | `InvalidTokenSignature` | La firma del token no coincide con la clave pública. | Token manipulado, corrupto o incorrecto. | `['token']` | `require_auth_hybrid.py`: ~110 |

---

## 2. Módulo de Pagos (Stripe)

**Archivo:** `API/routes/stripe/create_and_check_payment.py`

| Estado | Nombre | Descripción | Causa | Data Importante | archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `InvalidPaymentData` | Email vacío o nombre demasiado corto (< 3 caracteres). | Validación previa a llamada a Stripe. | `['email', 'name']` | ~55, ~134 |
| **400** | `QuantityLimitExceeded` | Intento de comprar más de 1 unidad. | Restricción de negocio (1 loro por usuario). | `['quantity']` | ~137 |
| **400** | `DuplicatePurchase` | El usuario ya tiene una compra finalizada en BD. | Evitar cobros dobles a un mismo usuario. | `['email']` | ~150 |
| **500** | `PaymentCreationError` | Fallo al crear el PaymentIntent. | Error de conexión o claves inválidas (Capturado como Genérico). | `['stripe_error']` | ~215 |

---

## 3. Módulo de IA (OpenAI)

**Archivo:** `API/routes/onoratoFarm/get_voice.py`

| Estado | Nombre | Descripción | Causa | Data Importante |archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **500** | `LLMProcessingError` | Error al procesar/parsear el JSON de respuesta. | La IA devuelve texto plano o formato inválido. | `['openai_res']` | ~280 |
| **500** | `VoiceGenerationError` | Fallo al generar el audio (TTS). | Error en API de Audio de OpenAI (Timeout/Quota). | `['text_input']` | ~335 |
| **500** | `AudioFileError` | Error al leer/guardar archivos de audio locales. | Problema de permisos de escritura o disco lleno. | `['file_path']` | ~370 |

---

## 4. Módulo de Almacenamiento (S3)

**Archivo:** `API/functions/buckets.py`

| Estado | Nombre | Descripción | Causa | Data Importante | archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **403** | `NoCredentialsError` | No se encuentran las claves AWS en variables de entorno. | Error de configuración del servidor (`.env`). | `['env_vars']` | ~108 |
| **200** | `NoSuchKey` | El archivo solicitado no existe (Devuelve lista vacía). | Usuario nuevo sin historial de archivos. | `['s3_path']` | ~112 |

---

## 5. Lista de errores a implementar


Tabla de listas de errores `except Exception` genéricos que hay que implemetar específicamete:

| Estado Sugerido | Nombre del Error | Descripción |archivo |
| :--- | :--- | :--- | :--- |
| **402** | `stripe.error.CardError` | Tarjeta rechazada o sin fondos. | `create_and_check_payment.py`: ~215 |
| **429** | `stripe.error.RateLimitError` | Demasiadas peticiones a la pasarela de pago. | `create_and_check_payment.py`: ~215 |
| **400** | `stripe.error.InvalidRequestError` | Datos mal formados enviados a Stripe. | `create_and_check_payment.py`: ~215 |
| **504** | `openai.APITimeoutError` | La API de OpenAI tarda demasiado en responder. | `get_voice.py`: ~335 |
| **429** | `openai.RateLimitError` | Se ha excedido la cuota de la API Key de OpenAI. | `get_voice.py`: ~335 |
| **429** | `client.exceptions.TooManyRequests` | Bloqueo de seguridad AWS por intentos masivos. | `login.py` (Global) |
| **405** | `client.exceptions.PasswordResetRequired` | El usuario necesita resetear contraseña obligatoriamente. | `login.py` (Global) |
| **503** | `botocore.exceptions.EndpointConnectionError` | Fallo de red al conectar con S3. | `buckets.py`: ~112 |


## Manejo de errores globales en app.py ##
Añadir al inicio de app.py:
```python
from werkzeug.exceptions import HTTPException
from API.functions.errors import AppError
```
Correción habia 2 veces reminders:
```python from API.routes.admin import info_users, stats, reminders```
## ##
https://api.tuweb.com/admin/logs y ver el archivo de texto sin usar la consola. 
```python
@app.route('/admin/logs', methods=['GET'])
@require_auth_hybrid
def get_server_logs():
```
He sustituido/añadido el final del archivo para conectar la clase AppError y el Logger.

Añadir al final de app.py (linea ~330):
```python
## Manejador de errores centralizados ##
@app.errorhandler(AppError)
def handle_app_error(e):
    # Cuando alguien lance un AppError, Flask devuelve la respuesta JSON bonita
    return e.to_response()

## Manejador de errores globales#
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e

    # GRABAR EL ERROR EN EL ARCHIVO DE LOGS
    logger.error(f"ERROR CRÍTICO NO CONTROLADO: {str(e)}", exc_info=True)

    return jsonify({
        "status": "error",
        "message": "Internal Server Error",
        "error": str(e) 
    }), 500
```
