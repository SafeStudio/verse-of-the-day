class BibleVersionNotSupportedException(Exception):
    code = 600

    def __init__(self, message='Bible version was not supported'):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        # Now for your custom code...
        self.error = {
            'code': self.code,
            'message': message
        }
