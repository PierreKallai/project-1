from flask import jsonify
from API.functions.logger import get_logger

# Inicializamos el logger para que registre automáticamente los errores de esta clase
logger = get_logger(__name__)

class AppError(Exception):
    """
    Clase centralizada para gestionar errores.
    1. Busca el error en el CATÁLOGO.
    2. Lo guarda automáticamente en los LOGS.
    3. Genera una respuesta JSON estándar para el usuario.
    """

    # --- CATÁLOGO MAESTRO DE ERRORES (Sincronizado con README.md) ---
    CATALOGO = {
        # 1. VALIDACIÓN Y ENTRADA
        'MISSING_FIELDS': {
            'status': 400,
            'message': 'Faltan campos obligatorios en la petición.',
            'solution': 'Revisa que envíes todos los datos requeridos (ej: email, password).'
        },
        'INVALID_EMAIL': {
            'status': 400,
            'message': 'El formato del email no es válido.',
            'solution': 'Usa un email real con formato usuario@dominio.com.'
        },

        # 2. IDENTIDAD (AUTH & COGNITO)
        'AUTH_FAILED': { # NotAuthorizedException
            'status': 401,
            'message': 'Credenciales incorrectas.',
            'solution': 'Verifica tu contraseña o email.'
        },
        'USER_NOT_FOUND': { # UserNotFoundException
            'status': 404,
            'message': 'El usuario no existe.',
            'solution': 'Regístrate o verifica el email.'
        },
        'USER_NOT_CONFIRMED': { # UserNotConfirmedException
            'status': 403,
            'message': 'El email no ha sido verificado.',
            'solution': 'Busca el código OTP en tu correo y confirma tu cuenta.'
        },
        'NO_INVITATION': {
            'status': 403,
            'message': 'No tienes invitación para registrarte.',
            'solution': 'Contacta con el administrador para solicitar acceso.'
        },
        'USER_EXISTS_LOCAL': {
            'status': 409,
            'message': 'El usuario ya existe en la base de datos local.',
            'solution': 'Intenta iniciar sesión.'
        },
        'USER_EXISTS_CLOUD': { # UsernameExistsException
            'status': 409,
            'message': 'El usuario ya existe en la nube (Cognito).',
            'solution': 'Intenta iniciar sesión o recuperar contraseña.'
        },
        'WEAK_PASSWORD': { # InvalidPasswordException
            'status': 400,
            'message': 'La contraseña es demasiado débil.',
            'solution': 'Usa mayúsculas, minúsculas, números y símbolos.'
        },
        'NEW_PASSWORD_REQUIRED': {
            'status': 405,
            'message': 'Debes cambiar tu contraseña obligatoriamente.',
            'solution': 'Usa el endpoint de cambio de contraseña.'
        },

        # 3. RECUPERACIÓN Y TOKENS
        'INVALID_CODE': { # CodeMismatchException
            'status': 400,
            'message': 'El código de verificación es incorrecto.',
            'solution': 'Revisa el código enviado a tu email.'
        },
        'LIMIT_EXCEEDED': { # LimitExceededException
            'status': 400,
            'message': 'Has excedido el límite de intentos.',
            'solution': 'Espera un tiempo antes de volver a intentarlo.'
        },
        'TOKEN_EXPIRED': {
            'status': 401,
            'message': 'Tu sesión ha caducado.',
            'solution': 'Vuelve a iniciar sesión para obtener un token nuevo.'
        },
        'INVALID_TOKEN': {
            'status': 401,
            'message': 'Token de sesión inválido.',
            'solution': 'No modifiques el token manualmente. Inicia sesión de nuevo.'
        },

        # 4. PAGOS (STRIPE)
        'INVALID_PAYMENT_DATA': {
            'status': 400,
            'message': 'Datos de pago inválidos (nombre o email).',
            'solution': 'Corrige los datos del formulario.'
        },
        'QUANTITY_EXCEEDED': {
            'status': 400,
            'message': 'Solo puedes comprar 1 unidad.',
            'solution': 'Reduce la cantidad a 1.'
        },
        'DUPLICATE_PURCHASE': {
            'status': 400,
            'message': 'Ya tienes una compra activa.',
            'solution': 'No es necesario volver a pagar.'
        },
        'STRIPE_ERROR': {
            'status': 500,
            'message': 'Error al procesar el pago con Stripe.',
            'solution': 'Inténtalo de nuevo más tarde o usa otra tarjeta.'
        },

        # 5. EXTERNOS (IA / S3)
        'AI_ERROR': {
            'status': 500,
            'message': 'Error al procesar la respuesta de la IA.',
            'solution': 'Reintenta la pregunta.'
        },
        'S3_ERROR': {
            'status': 503,
            'message': 'No se pudo conectar con el almacenamiento.',
            'solution': 'Problema temporal del servidor.'
        },
        
        # DEFAULT
        'GENERIC_ERROR': {
            'status': 500,
            'message': 'Error interno del servidor.',
            'solution': 'Contacta con soporte.'
        }
    }

    def __init__(self, code, details=None):
        """
        :param code: Clave del error (ej: 'AUTH_FAILED')
        :param details: Info técnica extra (str(e)) para el log, NO para el usuario.
        """
        # 1. Recuperar info del catálogo
        info = self.CATALOGO.get(code, self.CATALOGO['GENERIC_ERROR'])
        
        self.code = code
        self.status_code = info['status']
        self.message = info['message']
        self.solution = info['solution']
        self.details = details

        # 2. LOGGING AUTOMÁTICO
        # Guardamos la traza completa si es un error 500, o warning si es error de usuario
        log_message = f"APP_ERROR: {code} | UserMsg: {self.message}"
        if details:
            log_message += f" | Details: {str(details)}"

        if self.status_code >= 500:
            logger.error(log_message, exc_info=True)
        else:
            logger.warning(log_message)

        super().__init__(self.message)

    def to_response(self):
        """Devuelve el JSON listo para Flask"""
        return jsonify({
            "ok": False,
            "error": self.code,
            "message": self.message,
            "solution": self.solution
            # Nota: NO enviamos 'details' al usuario por seguridad
        }), self.status_code
