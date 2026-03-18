def get_vspace(
    filename, block_shift=8, number_block=8, compact_size=None, undelete=False
):
    block_size = (1 << number_block) << block_shift
    if compact_size is None:
        compact_size = block_size != 0x20000
    size_file = 2 if compact_size else 4
    virtual_space = dict()
    block_offset = 0
    with open(filename, "rb") as file:
        data = file.read(block_size)
        while len(data) > 0:
            if (
                data[block_size - 7 : block_size - 6] == b"\xff"
                and data[block_size - 2 : block_size] == b"\xf0\xf0"
            ):
                offset = 0
                while data[offset : offset + 2] != b"\xff\xff":
                    chunk_id = int.from_bytes(data[offset : offset + 2], "little")
                    start = (
                        int.from_bytes(data[offset + 2 : offset + 4], "little")
                        << block_shift
                    )
                    size = int.from_bytes(
                        data[offset + 4 : offset + 4 + size_file], "little"
                    )
                    if (
                        data[offset + 4 + size_file] == 0xFF
                        if block_size == 0x20000
                        else data[offset + 5 + size_file] == 0xF
                    ):
                        assert chunk_id not in virtual_space or undelete
                        virtual_space[chunk_id] = data[start : start + size]
                    elif undelete and chunk_id not in virtual_space:
                        virtual_space[chunk_id] = data[start : start + size]
                    offset += 0x10
            block_offset += block_size
            data = file.read(block_size)
    return virtual_space


def get_aspace(filename, block_shift=8, number_block=8, compact_size=None):
    block_size = (1 << number_block) << block_shift
    if compact_size is None:
        compact_size = block_size != 0x20000
    size_file = 2 if compact_size else 4
    alt_space = dict()
    block_offset = 0
    with open(filename, "rb") as file:
        data = file.read(block_size)
        while len(data) > 0:
            if (
                data[block_size - 7 : block_size - 6] == b"\xff"
                and data[block_size - 2 : block_size] == b"\xf0\xf0"
            ):
                offset = 0
                while data[offset : offset + 2] != b"\xff\xff":
                    chunk_id = int.from_bytes(data[offset : offset + 2], "little")
                    start = (
                        int.from_bytes(data[offset + 2 : offset + 4], "little")
                        << block_shift
                    )
                    size = int.from_bytes(
                        data[offset + 4 : offset + 4 + size_file], "little"
                    )
                    alt = alt_space.get(chunk_id, [])
                    alt.append(
                        (
                            start + block_offset,
                            size,
                            (
                                data[offset + 4 + size_file] == 0xFF
                                if block_size == 0x20000
                                else data[offset + 5 + size_file] == 0xF
                            ),
                            data[start : start + size],
                        )
                    )
                    alt_space[chunk_id] = alt
                    offset += 0x10
            block_offset += block_size
            data = file.read(block_size)
    return alt_space
