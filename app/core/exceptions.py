"""
Excepciones personalizadas para la aplicación Reuse.
"""


class ReuseException(Exception):
    """Excepción base para todas las excepciones de Reuse."""

    def __init__(self, message: str = "Error en la aplicación"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(ReuseException):
    """Excepción cuando un recurso no se encuentra."""

    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message)


class UnauthorizedException(ReuseException):
    """Excepción cuando el usuario no está autenticado."""

    def __init__(self, message: str = "No autorizado"):
        super().__init__(message)


class ForbiddenException(ReuseException):
    """Excepción cuando el usuario no tiene permisos."""

    def __init__(self, message: str = "Acceso prohibido"):
        super().__init__(message)


class BadRequestException(ReuseException):
    """Excepción cuando la solicitud es inválida."""

    def __init__(self, message: str = "Solicitud inválida"):
        super().__init__(message)


class ConflictException(ReuseException):
    """Excepción cuando hay un conflicto con el estado actual."""

    def __init__(self, message: str = "Conflicto con el recurso"):
        super().__init__(message)


class ValidationException(ReuseException):
    """Excepción cuando falla la validación de datos."""

    def __init__(self, message: str = "Error de validación"):
        super().__init__(message)
