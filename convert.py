def encode(media_id: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    shortcode = ""
    while media_id > 0:
        media_id, rem = divmod(media_id, 64)
        shortcode = alphabet[rem] + shortcode
    return shortcode

def decode(url):
    return ""

# Convert ID to shortcode
print(encode(17841453422264702))  # Deve dar: DMjeswEuNwQ

# Convert shortcode back to ID
print(decode("DMjeswEuNwQ"))  # Deve dar: 18296973229188862