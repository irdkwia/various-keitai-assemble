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

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

vspace = {}
with open(args.input, "rb") as file:
    data = file.read(0x20000)
    block_number = 0
    while len(data) > 0:
        if data[0x1FFFC:0x20000] == b"\xf0\xf0\x00\xff":
            off = 0
            while data[off : off + 4] != b"\xff\xff\xff\xff":
                chunk_id = int.from_bytes(data[off : off + 4], "little")
                size = int.from_bytes(data[off + 4 : off + 6], "little")
                loc = int.from_bytes(data[off + 6 : off + 8], "little")
                fs = data[off + 8]
                if data[off + 11] == 0xFF:
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
                        0x1FFF0 - (loc << 9) : 0x1FFF0 - ((loc - size) << 9)
                    ]
                off += 0xC
        data = file.read(0x20000)
        block_number += 0x20000


for k, v in vspace.items():
    with open(os.path.join(args.output, "region_%04d.bin" % k), "wb") as file:
        for e, d in sorted(v.items()):
            file.write(d)
