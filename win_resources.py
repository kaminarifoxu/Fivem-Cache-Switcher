# Copyright (c) 2026 GANOMABI / amiinarii.
"""Update PE icons and version information without running the Windows binary."""
import struct


def align(n, unit=4):
    return (n + unit - 1) // unit * unit


def version_info(name, version, copyright_text):
    def block(key, value=b"", kind=1, children=()):
        head = bytearray(b"\0" * 6 + (key + "\0").encode("utf-16le"))
        head.extend(b"\0" * (align(len(head)) - len(head)))
        head.extend(value)
        if children:
            head.extend(b"\0" * (align(len(head)) - len(head)))
            for child in children:
                head.extend(child)
                head.extend(b"\0" * (align(len(head)) - len(head)))
        length = len(value) // 2 if kind == 1 else len(value)
        struct.pack_into("<HHH", head, 0, len(head), length, kind)
        return bytes(head)
    major, minor, patch = [int(x) for x in version.split(".")]
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x10000, major << 16 | minor, patch << 16,
                        major << 16 | minor, patch << 16, 0x3F, 0, 0x40004, 1, 0, 0, 0)
    strings = {
        "CompanyName": "GANOMABI / amiinarii", "FileDescription": name,
        "FileVersion": version, "InternalName": name, "LegalCopyright": copyright_text,
        "OriginalFilename": name + ".exe", "ProductName": name, "ProductVersion": version,
    }
    table = block("040904B0", children=[block(k, (v + "\0").encode("utf-16le")) for k, v in strings.items()])
    info = block("StringFileInfo", children=[table])
    translation = block("VarFileInfo", children=[block("Translation", struct.pack("<HH", 0x409, 1200), 0)])
    return block("VS_VERSION_INFO", fixed, 0, [info, translation])


def patch_resources(bootloader, ico, name="GanoV-Cache-Switch", version="2.3.0"):
    data = bytearray(bootloader)
    pe = struct.unpack_from("<I", data, 60)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Invalid PE")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:
        raise ValueError("Expected PE32+")
    section_table = opt + struct.unpack_from("<H", data, pe + 20)[0]
    size_headers = struct.unpack_from("<I", data, opt + 60)[0]
    if section_table + (section_count + 1) * 40 > size_headers:
        raise ValueError("No room for resource section header")
    section_align, file_align = struct.unpack_from("<II", data, opt + 32)
    sections = []
    for i in range(section_count):
        vs, va, rs, ro = struct.unpack_from("<IIII", data, section_table + i * 40 + 8)
        sections.append((va, vs, ro, rs))
    def rva_offset(rva):
        for va, vs, ro, rs in sections:
            if va <= rva < va + max(vs, rs):
                return ro + rva - va
        raise ValueError("Resource RVA not mapped")
    resource_rva = struct.unpack_from("<I", data, opt + 112 + 16)[0]
    base = rva_offset(resource_rva)
    leaves = {}
    def read_tree(offset, keys=()):
        directory = base + offset
        named, ids = struct.unpack_from("<HH", data, directory + 12)
        for i in range(named + ids):
            key, pointer = struct.unpack_from("<II", data, directory + 16 + i * 8)
            if key & 0x80000000:
                at = base + (key & 0x7FFFFFFF)
                length = struct.unpack_from("<H", data, at)[0]
                key = bytes(data[at + 2:at + 2 + length * 2]).decode("utf-16le")
            if pointer & 0x80000000:
                read_tree(pointer & 0x7FFFFFFF, keys + (key,))
            else:
                rva, size, codepage, _ = struct.unpack_from("<4I", data, base + pointer)
                start = rva_offset(rva)
                leaves[keys + (key,)] = (bytes(data[start:start + size]), codepage)
    read_tree(0)
    leaves = {k: v for k, v in leaves.items() if k[0] not in (3, 14, 16)}
    reserved, icon_type, count = struct.unpack_from("<HHH", ico)
    if reserved or icon_type != 1 or not count:
        raise ValueError("Invalid ICO")
    group = bytearray(struct.pack("<HHH", 0, 1, count))
    for index in range(count):
        width, height, colors, zero, planes, bits, size, start = struct.unpack_from("<BBBBHHII", ico, 6 + index * 16)
        image = ico[start:start + size]
        if len(image) != size:
            raise ValueError("Truncated ICO")
        icon_id = index + 1
        leaves[(3, icon_id, 1033)] = (image, 0)
        group.extend(struct.pack("<BBBBHHIH", width, height, colors, zero, planes, bits, size, icon_id))
    leaves[(14, 1, 1033)] = (bytes(group), 0)
    leaves[(16, 1, 1033)] = (version_info(name, version, "Copyright (c) 2026 GANOMABI / amiinarii"), 1200)
    tree = {}
    for keys, value in leaves.items():
        node = tree
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
    directories, strings, entries = [], [], []
    cursor = 0
    def allocate(node):
        nonlocal cursor
        offset = cursor
        keys = sorted(node, key=lambda k: (0, k) if isinstance(k, str) else (1, k))
        cursor += 16 + len(keys) * 8
        record = [offset, []]
        directories.append(record)
        for key in keys:
            if isinstance(key, str):
                strings.append(key)
            value = node[key]
            record[1].append([key, allocate(value) if isinstance(value, dict) else value])
        return offset
    allocate(tree)
    result = bytearray(cursor)
    string_offsets = {}
    for key in dict.fromkeys(strings):
        string_offsets[key] = len(result)
        result.extend(struct.pack("<H", len(key)) + key.encode("utf-16le"))
    result.extend(b"\0" * (align(len(result)) - len(result)))
    for offset, records in directories:
        named = sum(isinstance(key, str) for key, value in records)
        struct.pack_into("<IIHHHH", result, offset, 0, 0, 0, 0, named, len(records) - named)
        for i, (key, value) in enumerate(records):
            encoded_key = 0x80000000 | string_offsets[key] if isinstance(key, str) else key
            if isinstance(value, int):
                pointer = 0x80000000 | value
            else:
                pointer = len(result)
                result.extend(b"\0" * 16)
                entries.append((pointer, value))
            struct.pack_into("<II", result, offset + 16 + i * 8, encoded_key, pointer)
    new_rva = align(max(va + max(vs, rs) for va, vs, ro, rs in sections), section_align)
    for pointer, (value, codepage) in entries:
        result.extend(b"\0" * (align(len(result)) - len(result)))
        start = len(result)
        result.extend(value)
        struct.pack_into("<4I", result, pointer, new_rva + start, len(value), codepage, 0)
    raw_offset = align(len(data), file_align)
    raw_size = align(len(result), file_align)
    data.extend(b"\0" * (raw_offset - len(data)))
    data.extend(result)
    data.extend(b"\0" * (raw_size - len(result)))
    header = section_table + section_count * 40
    struct.pack_into("<8sIIIIIIHHI", data, header, b".gnrsrc\0", len(result), new_rva, raw_size, raw_offset, 0, 0, 0, 0, 0x40000040)
    struct.pack_into("<H", data, pe + 6, section_count + 1)
    struct.pack_into("<I", data, opt + 8, struct.unpack_from("<I", data, opt + 8)[0] + raw_size)
    struct.pack_into("<I", data, opt + 56, align(new_rva + len(result), section_align))
    struct.pack_into("<I", data, opt + 64, 0)  # Unsigned output; Windows accepts zero PE checksum.
    struct.pack_into("<II", data, opt + 112 + 16, new_rva, len(result))
    struct.pack_into("<II", data, opt + 112 + 32, 0, 0)  # Do not retain an invalid signature.
    return bytes(data)
