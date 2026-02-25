# Catálogo Maestro de Errores de la API

Este documento es la referencia técnica completa de todos los errores que pueden ocurrir en la API. Incluye errores de lógica de negocio, validaciones, base de datos y servicios externos (AWS, Stripe, OpenAI).

---

## 1. Módulo de Identidad (Login, Registro y Usuarios)

### Errores de Registro (`register.py`)
| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `MissingFields` | Faltan campos obligatorios. | El body no tiene `email`, `password`, `name` o `last_name`. | `['missing_fields']` | `register.py` |
| **400** | `InvalidEmailFormat` | El email no tiene formato válido. | Falla la regex `^[\w\.-]+@[\w\.-]+\.\w+$`. | `['email']` | `register.py` |
| **400** | `InvalidPasswordException` | La contraseña es muy débil. | No cumple la política de AWS (longitud, símbolos, mayúsculas). | `['password']` | `register.py` |
| **403** | `NoInvitationFound` | Email no invitado. | El usuario intenta registrarse pero su email no está en la tabla `INVITATIONS`. | `['email']` | `register.py` |
| **409** | `UserExists` | Usuario duplicado en BD local. | El email ya existe en la tabla `USERS` de MySQL. | `['email']` | `register.py` |
| **409** | `UsernameExistsException` | Usuario duplicado en Cognito. | El email ya existe en AWS pero no en local (desincronización). | `['email']` | `register.py` |
| **500** | `CodeDeliveryFailureException` | Fallo al enviar email de código. | AWS SES no pudo entregar el correo de verificación. | `['email']` | `register.py` |

### Errores de Login (`login.py`)
| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `MissingCredentials` | Faltan credenciales. | Body sin `email` o `password`. | `['email']` | `login.py` |
| **400** | `MigrationRequired` | Usuario migrado a Cognito. | Usuario con `auth_type='cognito'` intenta login legacy. | `['email']` | `login.py` |
| **401** | `NotAuthorizedException` | Contraseña incorrecta. | El hash de la contraseña no coincide (Cognito o Legacy). | `['email']` | `login.py` |
| **403** | `UserNotConfirmedException` | Cuenta no verificada. | Usuario registrado pero no ha confirmado su email con el código. | `['email']` | `login.py` |
| **404** | `UserNotFound` | Usuario no existe (Local). | Email no encontrado en tabla `USERS`. | `['email']` | `login.py` |
| **404** | `UserNotFoundException` | Usuario no existe (Cognito). | Email no encontrado en AWS User Pool. | `['email']` | `login.py` |
| **405** | `NewPasswordRequired` | Cambio de contraseña forzoso. | Primer login de un usuario creado por admin. Requiere `new_password`. | `['session']` | `login.py` |
| **429** | `TooManyRequestsException` | Bloqueo temporal por intentos. | Demasiados intentos fallidos de login (seguridad AWS). | `['ip_address']` | `login.py` |

### Errores de Confirmación (`register.py` - `confirm_cognito`)
| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `CodeMismatchException` | Código inválido. | El código OTP ingresado no es el correcto. | `['code']` | `register.py` |
| **400** | `ExpiredCodeException` | Código caducado. | El código OTP ha expirado (usualmente 24h). | `['code']` | `register.py` |
| **400** | `AliasExistsException` | Email en uso como alias. | El email ya está asociado como alias a otra cuenta. | `['email']` | `register.py` |

### Errores de Perfil (`delete_profile.py`, `update_profile.py`)
| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `MissingEmail` | Falta el email. | Petición sin el campo `email` para buscar el usuario. | `['email']` | `delete_profile.py` |
| **403** | `AdminDeleteError` | Intento de borrar Admin. | Se intenta eliminar un usuario con rol 'admin'. Prohibido. | `['email']` | `delete_profile.py` |
| **404** | `UserNotFound` | Usuario no encontrado. | Intentando actualizar/borrar un email que no existe. | `['email']` | `update_profile.py` |

---

## 2. Módulo de Recuperación de Contraseña (`recover_password.py`)

| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `LimitExceededException` | Límite de envíos excedido. | Usuario solicitó demasiados códigos de recuperación ("Resend"). | `['email']` | `recover_password.py` |
| **400** | `CodeMismatchException` | Código incorrecto. | El código de reseteo no coincide. | `['code']` | `recover_password.py` |
| **400** | `ExpiredCodeException` | Código expirado. | Pasó el tiempo límite para usar el código de recuperación. | `['code']` | `recover_password.py` |
| **400** | `PasswordHistoryPolicyViolation`| Contraseña ya usada. | La nueva contraseña ya fue usada anteriormente (AWS impide repetir). | `['new_password']` | `recover_password.py` |
| **404** | `UserNotFoundException` | Usuario desconocido. | Intentando recuperar contraseña de un email no registrado. | `['email']` | `recover_password.py` |
| **404** | `InvalidResetCode` | Código no encontrado (Legacy). | El código no existe en la tabla `RECOVERY_PASSWORD`. | `['code']` | `recover_password.py` |

---

## 3. Módulo de Pagos (Stripe) - `create_and_check_payment.py`

| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400** | `InvalidPaymentData` | Datos inválidos. | Email incorrecto o nombre muy corto (<3 chars). | `['email', 'name']` | `create_and_check_payment.py` |
| **400** | `QuantityLimitExceeded` | Cantidad excedida. | Usuario intenta comprar más de 1 unidad (Loro). | `['quantity']` | `create_and_check_payment.py` |
| **400** | `DuplicatePurchase` | Compra duplicada. | El usuario ya tiene un pago `succeeded` en historial. | `['email']` | `create_and_check_payment.py` |
| **402** | `CardError` | Tarjeta rechazada. | Fondos insuficientes, tarjeta caducada o bloqueada. (Stripe). | `['stripe_code']` | `create_and_check_payment.py` |
| **500** | `PaymentCreationError` | Error de API Stripe. | Fallo de conexión o claves inválidas al crear PaymentIntent. | `['stripe_error']` | `create_and_check_payment.py` |

---

## 4. Módulo IA y Voz (OnoratoFarm) - `get_voice.py`

| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **500** | `LLMProcessingError` | Error de respuesta IA. | OpenAI devuelve una respuesta que no es JSON válido o está vacía. | `['openai_response']` | `get_voice.py` |
| **500** | `OpenAIAPIError` | Error de conexión IA. | Timeout o error 5xx desde la API de OpenAI. | `['api_key']` | `get_voice.py` |
| **500** | `VoiceGenerationError` | Fallo en TTS. | La API de Audio no pudo generar el archivo MP3. | `['text']` | `get_voice.py` |
| **500** | `AudioFileError` | Error de archivo. | No se pudo leer/escribir el archivo de audio en disco local. | `['file_path']` | `get_voice.py` |

---

## 5. Módulo de Almacenamiento (S3) - `buckets.py`

| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **403** | `NoCredentialsError` | Faltan credenciales AWS. | El servidor no tiene configurado `AWS_ACCESS_KEY_ID`. | `['env_vars']` | `buckets.py` |
| **500** | `Boto3Error` | Error de conexión S3. | Fallo de red o bucket no existe. | `['bucket_name']` | `buckets.py` |
| **200** | `NoSuchKey` | Archivo no encontrado. | Se pide un JSON que no existe (devuelve lista vacía `[]`). | `['key']` | `buckets.py` |

---

## 6. Errores Generales y Base de Datos

| Status | Error Name | Descripción | Casuística | Datos Clave | Archivo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **500** | `DatabaseError` | Error SQL. | Fallo de conexión a MySQL o query mal formada. | `['query']` | `db_connection.py` |
| **401** | `TokenMissing` | Token ausente. | Petición sin header `Authorization`. | `['headers']` | `require_auth_hybrid.py` |
| **401** | `TokenExpired` | Token caducado. | El JWT ha expirado. | `['exp']` | `require_auth_hybrid.py` |
| **401** | `InvalidToken` | Token inválido. | Firma del token manipulada o incorrecta. | `['signature']` | `require_auth_hybrid.py` |
