class IncorrectCredentialsError(Exception):
    def __init__(self, message=None):
        super(IncorrectCredentialsError, self).__init__(message)

class UimsFailureError(Exception):
    def __init__(self, message=None):
        super(UimsFailureError, self).__init__(message)