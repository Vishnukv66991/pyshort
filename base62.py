ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def encode_base62(n: int) -> str:
    if n == 0:
        return "0"
    base = len(ALPHABET)
    out = []
    while n > 0:
        n, rem = divmod(n, base)
        out.append(ALPHABET[rem])
    return "".join(reversed(out))
