# API/functions/errors.py
from flask import jsonify
from API.functions.logger import get_logger

# Inicializamos el logger para captación de errores automática (Tarea #2)
logger = get_logger(__name__)

class AppError(Exception):
    """
    Clase centralizada para gestionar errores.
    1. Busca el error en el CATÁLOGO MAESTRO.
    2. Guarda el error y la traza en el servidor mediante logger.error (Tarea #2).
    3. Genera una respuesta JSON estándar para el usuario con solución (Tarea #1).
    """

    # --- CATÁLOGO MAESTRO DE ERRORES (Tarea #1 & #3) ---
    CATALOGO = {
        # === 1. IDENTIDAD Y AWS COGNITO (Documentación Oficial AWS) ===
        'AUTH_FAILED': {
            'status': 401,
            'message': 'Credenciales incorrectas.',
            'solution': 'Verifica tu contraseña o email e inténtalo de nuevo.'
        },
        'USER_NOT_FOUND': {
            'status': 404,
            'message': 'El usuario no existe en el sistema.',
            'solution': 'Asegúrate de estar registrado con este email.'
        },
        'USER_NOT_CONFIRMED': {
            'status': 403,
            'message': 'Tu cuenta aún no ha sido confirmada.',
            'solution': 'Revisa tu email y utiliza el código de verificación enviado.'
        },
        'USER_EXISTS_CLOUD': {
            'status': 409,
            'message': 'Ya existe una cuenta con este email.',
            'solution': 'Intenta iniciar sesión o recuperar tu contraseña.'
        },
        'INVALID_CODE': {
            'status': 400,
            'message': 'El código de verificación introducido es incorrecto.',
            'solution': 'Verifica el código en tu email o solicita uno nuevo.'
        },
        'EXPIRED_CODE': {
            'status': 400,
            'message': 'El código de verificación ha caducado.',
            'solution': 'Solicita un nuevo código de verificación para continuar.'
        },
        'LIMIT_EXCEEDED': {
            'status': 429,
            'message': 'Has excedido el límite de intentos permitidos.',
            'solution': 'Por seguridad, espera unos minutos antes de volver a intentarlo.'
        },
        'TOO_MANY_ATTEMPTS': {
            'status': 429,
            'message': 'Demasiados intentos fallidos acumulados.',
            'solution': 'La cuenta se ha bloqueado temporalmente por seguridad. Inténtalo más tarde.'
        },
        'WEAK_PASSWORD': {
            'status': 400,
            'message': 'La contraseña no cumple con los requisitos de seguridad.',
            'solution': 'Debe contener mayúsculas, minúsculas, números y símbolos.'
        },
        'NEW_PASSWORD_REQUIRED': {
            'status': 405,
            'message': 'Es obligatorio cambiar la contraseña para continuar.',
            'solution': 'Establece una nueva contraseña en el portal de usuario.'
        },
        'PASSWORD_RESET_REQUIRED': {
            'status': 400,
            'message': 'Se requiere un restablecimiento de contraseña.',
            'solution': 'Usa la opción "Olvidé mi contraseña" para crear una nueva.'
        },
        'INVALID_PARAMETER': {
            'status': 400,
            'message': 'Uno o más parámetros enviados a AWS son inválidos.',
            'solution': 'Contacta con soporte técnico para revisar la configuración de tu cuenta.'
        },
        'USER_LAMBDA_ERROR': {
            'status': 500,
            'message': 'Error en el servicio de validación de identidad.',
            'solution': 'Hubo un fallo interno en la nube. Por favor, reintenta en un momento.'
        },
        'INTERNAL_AWS_ERROR': {
            'status': 500,
            'message': 'Error interno de los servicios de AWS.',
            'solution': 'Estamos experimentando problemas con el proveedor de identidad.'
        },

        # === 2. VALIDACIÓN Y LÓGICA DE NEGOCIO ===
        'MISSING_FIELDS': {
            'status': 400,
            'message': 'Faltan campos obligatorios en la petición.',
            'solution': 'Verifica que el JSON incluya todos los campos (ej: email, password).'
        },
        'INVALID_EMAIL': {
            'status': 400,
            'message': 'El formato del correo electrónico no es válido.',
            'solution': 'Introduce una dirección de correo real (ejemplo@dominio.com).'
        },
        'NO_INVITATION': {
            'status': 403,
            'message': 'No tienes una invitación válida para acceder.',
            'solution': 'Solicita una invitación al administrador del sistema.'
        },
        'USER_EXISTS_LOCAL': {
            'status': 409,
            'message': 'El usuario ya está registrado en nuestra base de datos local.',
            'solution': 'Intenta iniciar sesión directamente.'
        },

        # === 3. PAGOS (STRIPE) ===
        'STRIPE_ERROR': {
            'status': 500,
            'message': 'Error al procesar el pago con la pasarela Stripe.',
            'solution': 'Verifica tu conexión y los datos de tu tarjeta.'
        },
        'INVALID_PAYMENT_DATA': {
            'status': 400,
            'message': 'Los datos de facturación son incorrectos.',
            'solution': 'Revisa el nombre y el correo electrónico asociados al pago.'
        },
        'QUANTITY_EXCEEDED': {
            'status': 400,
            'message': 'Has superado el límite de unidades permitidas.',
            'solution': 'Este producto está limitado a 1 unidad por usuario.'
        },
        'DUPLICATE_PURCHASE': {
            'status': 400,
            'message': 'Ya dispones de una compra activa para este producto.',
            'solution': 'No es necesario volver a realizar el pago.'
        },

        # === 4. SERVICIOS EXTERNOS (IA / S3) ===
        'AI_ERROR': {
            'status': 500,
            'message': 'Error al procesar la respuesta de la Inteligencia Artificial.',
            'solution': 'La IA no pudo generar una respuesta válida. Inténtalo de nuevo.'
        },
        'VOICE_GENERATION_ERROR': {
            'status': 500,
            'message': 'Error al generar el archivo de voz (TTS).',
            'solution': 'Hubo un problema con el motor de voz. Inténtalo más tarde.'
        },
        'S3_ERROR': {
            'status': 503,
            'message': 'Error de conexión con el servicio de almacenamiento S3.',
            'solution': 'No pudimos acceder a tus archivos. Reintenta en unos minutos.'
        },

        # === 5. ERRORES GENÉRICOS ===
        'GENERIC_ERROR': {
            'status': 500,
            'message': 'Ha ocurrido un error interno e inesperado.',
            'solution': 'Contacta con soporte si el problema persiste.'
        }
    }

    def __init__(self, code, details=None):
        """
        Constructor de la excepción.
        :param code: Código único del error (ej: 'AUTH_FAILED')
        :param details: Detalles técnicos para el log (no se muestran al usuario final).
        """
        # 1. Recuperamos la información del catálogo
        info = self.CATALOGO.get(code, self.CATALOGO['GENERIC_ERROR'])
        
        self.code = code
        self.status_code = info['status']
        self.message = info['message']
        self.solution = info['solution']
        self.details = details

        # 2. LOGGING AUTOMÁTICO (Tarea #2)
        # Registramos el error con toda la información técnica disponible
        log_message = f"APP_ERROR_CODE: {code} | USER_MSG: {self.message}"
        if details:
            log_message += f" | TECHNICAL_DETAILS: {str(details)}"

        # Si el error es un 500 (Server Error), grabamos la traza completa (Stack Trace)
        if self.status_code >= 500:
            logger.error(log_message, exc_info=True)
        else:
            # Si es error de usuario (400), grabamos solo un aviso (Warning)
            logger.warning(log_message)

        super().__init__(self.message)

    def to_response(self):
        """Genera el JSON que se enviará al frontend."""
        return jsonify({
            "ok": False,
            "error_code": self.code,
            "message": self.message,
            "solution": self.solution
        }), self.status_code
