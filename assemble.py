import argparse
import os

parser = argparse.ArgumentParser(description="Keitai 00F0F0 Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-l",
    "--list-alt",
    help="Lists alternatives for each block that has any.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

virtual_space = dict()
alt_space = dict()
block_offset = 0
with open(args.input, "rb") as file:
    data = file.read(0x10000)
    while len(data) > 0:
        if data[0xFFF8:0xFFFA] == b"\xF0\xFF" and data[0xFFFE:0x10000] == b"\xF0\xF0":
            offset = 0
            while data[offset : offset + 2] != b"\xFF\xFF":
                chunk_id = int.from_bytes(data[offset : offset + 2], "little")
                start = int.from_bytes(data[offset + 2 : offset + 4], "little") << 8
                size = int.from_bytes(data[offset + 4 : offset + 6], "little")
                if data[offset + 7] == 0xF:
                    assert chunk_id not in virtual_space
                    virtual_space[chunk_id] = data[start : start + size]
                if args.list_alt:
                    if sum(data[start : start + size]) != 0xFF * size:
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

if args.list_alt:
    for k, v in sorted(alt_space.items()):
        compl = set()
        toprint = False
        lines = []
        for x in sorted(v, key=lambda x: (1 - int(x[2]), x[0])):
            if x[3] not in compl:
                compl.add(x[3])
                if not x[2]:
                    toprint = True
                lines.append("\t%08X\t%04X\t%s" % (x[0], x[1], "*" if x[2] else ""))
        if toprint:
            print(k)
            print("\n".join(lines))
accumulator = bytearray()
first_block_id = 0
k = 0
for k, v in sorted(virtual_space.items()):
    if len(accumulator) == 0:
        first_block_id = k
    accumulator += v
    if len(v) & 0xFF != 0:
        with open(
            os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
        ) as file:
            file.write(accumulator)
        accumulator = bytearray()

if len(accumulator) > 0:
    with open(
        os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
    ) as file:
        file.write(accumulator)
