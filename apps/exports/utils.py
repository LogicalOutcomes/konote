
def sanitize_for_csv(value):
    """Sanitize a value to prevent CSV injection (Formula Injection) attacks.

    If the value starts with =, +, -, or @, we prepend a single quote.
    """
    if value and isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return f"'{value}"
    return value
