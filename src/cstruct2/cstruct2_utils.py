host_endianness = "little"

def relative_endianness_resolver(endianness: str) -> str:
    """Resolve endian values, especially relative ones. This function is platform specific."""

    if endianness not in ["little", "big", "host", "network"]:
        raise AttributeError("Endianness can only be little, big, host, or network.")

    # Resolve relative endianness settings
    if endianness == "host":
        endianness = host_endianness

    elif endianness == "network":
        endianness = "big"

    
    return endianness