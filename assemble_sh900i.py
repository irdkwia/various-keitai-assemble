import argparse
import os

parser = argparse.ArgumentParser(description="Keitai SH900i Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-c",
    "--config",
    help="Choose configuration. Accepted values: D506i, SH900i",
    default="SH900i",
    type=str,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

if args.config == "D506i":
    SIZE = 0x40000
    ENDIANESS = "big"
    SHIFT = 4
elif args.config == "SH900i":
    SIZE = 0x20000
    ENDIANESS = "little"
    SHIFT = 9
else:
    raise ValueError(f"Invalid configuration: {args.config}")

vspace = {}
with open(args.input, "rb") as file:
    data = file.read(SIZE)
    block_number = 0
    while len(data) > 0:
        if data[SIZE - 4 : SIZE] == b"\xf0\xf0\x00\xff":
            off = 0
            while data[off : off + 4] != b"\xff\xff\xff\xff":
                chunk_id = int.from_bytes(data[off : off + 2], ENDIANESS)
                size = int.from_bytes(data[off + 4 : off + 6], ENDIANESS)
                loc = int.from_bytes(data[off + 6 : off + 8], ENDIANESS)
                fs = data[off + 8]
                if (
                    int.from_bytes(data[off + 10 : off + 12], ENDIANESS) & 0xFF00
                    == 0xFF00
                ):
                    vspace[fs] = vspace.get(fs, {})
                    if args.ignore:
                        if chunk_id in vspace[fs]:
                            print(
                                "Duplicate at %08X: region %d, block %d"
                                % (block_number + off, fs, chunk_id)
                            )
                    else:
                        assert (
                            chunk_id not in vspace[fs]
                        ), "Duplicate at %08X: region %d, block %d" % (
                            block_number + off,
                            fs,
                            chunk_id,
                        )
                    vspace[fs][chunk_id] = data[
                        SIZE
                        - 0x10
                        - (loc << SHIFT) : SIZE
                        - 0x10
                        - ((loc - size) << SHIFT)
                    ]
                off += 0xC
        data = file.read(SIZE)
        block_number += SIZE


for k, v in vspace.items():
    with open(os.path.join(args.output, "region_%04d.bin" % k), "wb") as file:
        for e, d in sorted(v.items()):
            file.write(d)
