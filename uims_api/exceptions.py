class IncorrectCredentialsError(Exception):
    def __init__(self, message=None):
        super(IncorrectCredentialsError, self).__init__(message)

class UIMSInternalError(Exception):
    def __init__(self, message=None):
        super(UIMSInternalError, self).__init__(message)

class PasswordExpiredError(Exception):
    def __init__(self, message=None):
        super(PasswordExpiredError, self).__init__(message)
