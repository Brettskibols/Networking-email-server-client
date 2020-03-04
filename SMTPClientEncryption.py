class nws_encryption:
    def __init__(self):
        self._enabled = False  # False
        self._method = "caesar"
        self._alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!£$%^&*()-+={}[]:;@'<,>.?/\\# "
        self._caesarkey = 2  # None
        self._vigenerekey = None

    # Caesar cipher not working but included for consideration for marks, some minor problem enabling decryption
    # on client side

    def toggle_enable(self):
        self._enabled = not self._enabled
        return self._enabled

    def set_caesar_key(self, key):
        try:
            self._caesarkey = int(key)
        except TypeError:
            self._caesarkey = 0
            return None
        return self._caesarkey

    def set_vigenere_key(self, key):
        try:
            self._vigenerekey = str(key)
        except TypeError:
            self._vigenerekey = "Derby"
            return None
        return self._caesarkey

    def set_method(self, method):
        if method.lower() == "caesar":
            self._method = "caesar"
        elif method.lower() == "vigenere":
            self._method = "vigenere"
        else:
            self._method = None

    def encrypt(self, message) -> str:
        if self._enabled:
            if self._method == "caesar":
                return self._caesar_cipher_encrypt(message)
            elif self._method == "vigenere":
                return self._vigenere_square_encrypt(message)
        return message

    def decrypt(self, message) -> str:
        if self._enabled:
            if self._method == "caesar":
                return self._caesar_cipher_decrypt(message)
            elif self._method == "vigenere":
                return self._vigenere_square_decrypt(message)
        return message

    def _caesar_cipher_encrypt(self, message) -> str:
        try:
            # message = str(message)
            shift = self._caesarkey
            placeholderstring = ""
            lowerstring = message.lower()
            for elem in lowerstring:
                new_elem = ord(elem) + shift
                if new_elem > 122:
                    new_elem = new_elem - 26
                placeholderstring = placeholderstring + chr(new_elem)
                message = placeholderstring

            return message

        except TypeError:
            return ""

        # perform caesar cipher here

    def _vigenere_square_encrypt(self, message) -> str:
        try:
            message = str(message)
        except TypeError:
            return ""

        # perform vigenere square here

    def _caesar_cipher_decrypt(self, message) -> str:
        try:
            # message = str(message)
            shift = self._caesarkey
            placeholderstring = ""
            lowerstring = message.lower()
            for elem in lowerstring:
                new_elem = ord(elem) - shift
                if new_elem < 97:
                    new_elem = new_elem + 26
                placeholderstring = placeholderstring + chr(new_elem)
                message = placeholderstring
            return message

        except TypeError:
            return ""

        # perform caesar cipher here

    def _vigenere_square_decrypt(self, message) -> str:
        try:
            message = str(message)
        except TypeError:
            return ""

        # perform vigenere square here
