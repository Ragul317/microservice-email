def mask_email(address: str) -> str:
    """Mask an email address for logs: customer@example.com -> c***@example.com."""
    local, _, domain = str(address).partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"
