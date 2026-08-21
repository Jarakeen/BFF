import struct


def fround(value: float) -> float:
    """Translate the UESP/JavaScript Math.fround operation to Python."""
    return struct.unpack("f", struct.pack("f", value))[0]