from __future__ import annotations


def matches_image_content_type(content_type: str, file_bytes: bytes) -> bool:
    if content_type == "image/jpeg":
        return len(file_bytes) >= 3 and file_bytes.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"
    if content_type in {"image/heic", "image/heif"}:
        if len(file_bytes) < 12 or file_bytes[4:8] != b"ftyp":
            return False
        box_size = int.from_bytes(file_bytes[:4], "big")
        if box_size < 12:
            return False
        allowed_brands = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
        brand_bytes = file_bytes[8 : min(len(file_bytes), box_size)]
        return any(
            brand_bytes[index : index + 4] in allowed_brands
            for index in range(0, len(brand_bytes) - 3, 4)
        )
    return False
