"""Small dependency-free Android binary XML reader for manifest inspection.

It intentionally covers the resource chunks and value types needed by the
Services Checker.  The full androguard parser remains the preferred backend;
this fallback keeps remote Python updates compatible with older bundles.
"""

import struct
import xml.etree.ElementTree as ET


ANDROID_NAMESPACE_URI = "http://schemas.android.com/apk/res/android"
RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
NO_INDEX = 0xFFFFFFFF


def _u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        raise ValueError("truncated binary XML")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated binary XML")
    return struct.unpack_from("<I", data, offset)[0]


def _decode_length(data, offset, utf8):
    if utf8:
        first = data[offset]
        offset += 1
        if first & 0x80:
            return ((first & 0x7F) << 8) | data[offset], offset + 1
        return first, offset

    first = _u16(data, offset)
    offset += 2
    if first & 0x8000:
        return ((first & 0x7FFF) << 16) | _u16(data, offset), offset + 2
    return first, offset


class _StringPool:
    def __init__(self, data, chunk_offset):
        if _u16(data, chunk_offset) != RES_STRING_POOL_TYPE:
            raise ValueError("binary XML string pool is missing")
        header_size = _u16(data, chunk_offset + 2)
        chunk_size = _u32(data, chunk_offset + 4)
        if chunk_size < header_size or chunk_offset + chunk_size > len(data):
            raise ValueError("invalid binary XML string pool size")

        count = _u32(data, chunk_offset + 8)
        flags = _u32(data, chunk_offset + 16)
        strings_start = _u32(data, chunk_offset + 20)
        self._utf8 = bool(flags & 0x100)
        self._data = data
        self._base = chunk_offset + strings_start
        self._offsets = [
            _u32(data, chunk_offset + header_size + index * 4)
            for index in range(count)
        ]
        self._cache = {}

    def get(self, index):
        if index == NO_INDEX or index < 0 or index >= len(self._offsets):
            return ""
        if index in self._cache:
            return self._cache[index]

        offset = self._base + self._offsets[index]
        try:
            length, text_offset = _decode_length(self._data, offset, self._utf8)
            if self._utf8:
                _, text_offset = _decode_length(self._data, text_offset, True)
                value = self._data[text_offset:text_offset + length].decode(
                    "utf-8", errors="replace"
                )
            else:
                value = self._data[text_offset:text_offset + length * 2].decode(
                    "utf-16le", errors="replace"
                )
        except (IndexError, UnicodeError, ValueError):
            value = ""
        self._cache[index] = value
        return value


def _find_string_pool(data):
    cursor = 8 if len(data) >= 8 and _u16(data, 0) == RES_XML_TYPE else 0
    while cursor + 8 <= len(data):
        chunk_type = _u16(data, cursor)
        chunk_size = _u32(data, cursor + 4)
        if chunk_size < 8 or cursor + chunk_size > len(data):
            break
        if chunk_type == RES_STRING_POOL_TYPE:
            return _StringPool(data, cursor), cursor + chunk_size
        cursor += chunk_size
    raise ValueError("binary XML string pool was not found")


def _typed_value(pool, raw_index, value_type, value_data):
    raw_value = pool.get(raw_index)
    if raw_value:
        return raw_value
    if value_type == TYPE_STRING:
        return pool.get(value_data)
    if value_type == TYPE_INT_DEC:
        return str(value_data)
    if value_type == TYPE_INT_HEX:
        return "0x{:08x}".format(value_data)
    if value_type == TYPE_INT_BOOLEAN:
        return "true" if value_data else "false"
    if value_type == 0x01:
        return "@0x{:08x}".format(value_data)
    return str(value_data)


def _parse_binary_xml(data):
    pool, cursor = _find_string_pool(data)
    root = None
    stack = []

    while cursor + 8 <= len(data):
        chunk_type = _u16(data, cursor)
        header_size = _u16(data, cursor + 2)
        chunk_size = _u32(data, cursor + 4)
        if chunk_size < 8 or cursor + chunk_size > len(data):
            raise ValueError("invalid binary XML chunk size")

        if chunk_type == RES_XML_START_ELEMENT_TYPE:
            if cursor + 36 > len(data):
                raise ValueError("truncated binary XML start element")
            namespace_index = _u32(data, cursor + 16)
            name_index = _u32(data, cursor + 20)
            attribute_size = _u16(data, cursor + 26)
            attribute_count = _u16(data, cursor + 28)
            if attribute_size < 20:
                raise ValueError("invalid binary XML attribute size")

            element = ET.Element(pool.get(name_index) or "unknown")
            attribute_offset = cursor + 36
            for index in range(attribute_count):
                offset = attribute_offset + index * attribute_size
                if offset + 20 > cursor + chunk_size:
                    raise ValueError("truncated binary XML attribute")
                attr_namespace = pool.get(_u32(data, offset))
                attr_name = pool.get(_u32(data, offset + 4)) or "unknown"
                raw_index = _u32(data, offset + 8)
                value_type = data[offset + 15]
                value_data = _u32(data, offset + 16)
                value = _typed_value(pool, raw_index, value_type, value_data)
                if attr_namespace:
                    key = "{{{}}}{}".format(attr_namespace, attr_name)
                else:
                    key = attr_name
                element.set(key, value)

            if root is None:
                root = element
            elif stack:
                stack[-1].append(element)
            stack.append(element)

        elif chunk_type == RES_XML_END_ELEMENT_TYPE:
            if stack:
                stack.pop()

        cursor += chunk_size

    if root is None:
        raise ValueError("binary XML document has no root element")
    return root


class AXMLPrinter:
    """Drop-in subset of androguard's AXMLPrinter used by app.py."""

    def __init__(self, data):
        ET.register_namespace("android", ANDROID_NAMESPACE_URI)
        self._buffer = ET.tostring(
            _parse_binary_xml(data),
            encoding="utf-8",
            xml_declaration=True,
        )

    def get_buff(self):
        return self._buffer
