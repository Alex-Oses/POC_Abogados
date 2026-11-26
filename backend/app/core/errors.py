class AppError(Exception):
    """Error de negocio con la forma del contrato: code estable + mensaje humano."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
