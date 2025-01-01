def get_vspace(filename, undelete=False):
    virtual_space = dict()
    block_offset = 0
    with open(filename, "rb") as file:
        data = file.read(0x10000)
        while len(data) > 0:
            if (
                data[0xFFF8:0xFFFA] == b"\xF0\xFF"
                and data[0xFFFE:0x10000] == b"\xF0\xF0"
            ):
                offset = 0
                while data[offset : offset + 2] != b"\xFF\xFF":
                    chunk_id = int.from_bytes(data[offset : offset + 2], "little")
                    start = int.from_bytes(data[offset + 2 : offset + 4], "little") << 8
                    size = int.from_bytes(data[offset + 4 : offset + 6], "little")
                    if data[offset + 7] == 0xF:
                        assert chunk_id not in virtual_space or undelete
                        virtual_space[chunk_id] = data[start : start + size]
                    elif undelete and chunk_id not in virtual_space:
                        virtual_space[chunk_id] = data[start : start + size]
                    offset += 0x10
            block_offset += 0x10000
            data = file.read(0x10000)
    return virtual_space


def get_aspace(filename):
    alt_space = dict()
    block_offset = 0
    with open(filename, "rb") as file:
        data = file.read(0x10000)
        while len(data) > 0:
            if (
                data[0xFFF8:0xFFFA] == b"\xF0\xFF"
                and data[0xFFFE:0x10000] == b"\xF0\xF0"
            ):
                offset = 0
                while data[offset : offset + 2] != b"\xFF\xFF":
                    chunk_id = int.from_bytes(data[offset : offset + 2], "little")
                    start = int.from_bytes(data[offset + 2 : offset + 4], "little") << 8
                    size = int.from_bytes(data[offset + 4 : offset + 6], "little")
                    alt = alt_space.get(chunk_id, [])
                    alt.append(
                        (
                            start + block_offset,
                            size,
                            data[offset + 7] == 0xF,
                            data[start : start + size],
                        )
                    )
                    alt_space[chunk_id] = alt
                    offset += 0x10
            block_offset += 0x10000
            data = file.read(0x10000)
    return alt_space
