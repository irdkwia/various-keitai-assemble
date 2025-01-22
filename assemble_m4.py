import argparse
import os

parser = argparse.ArgumentParser(description="Keitai M4 Assemble")
parser.add_argument("input")
parser.add_argument("output")
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

vspace = {}
with open(args.input, "rb") as file:
    data = file.read(0x20000)
    block_number = 0
    while len(data) > 0:
        if data[0x1FFF9:0x1FFFE] == b"\x55\x55\x55\xFF\xFF":
            off = 0
            while data[off : off + 0x10] != b"\xFF" * 0x10:
                fs = int.from_bytes(data[off + 3 : off + 5], "little")
                chunk_id = int.from_bytes(data[off + 6 : off + 8], "little")
                loc = int.from_bytes(data[off + 8 : off + 0xA], "little")
                size = int.from_bytes(data[off + 0xC : off + 0x10], "little")
                vspace[fs] = vspace.get(fs, {})
                # assert chunk_id not in vspace[fs], (
                    # hex(block_number) + " " + hex(off)
                # )
                vspace[fs][chunk_id] = data[
                    0x1FFE0 - (loc * 0x80) : 0x1FFE0 - (loc * 0x80) + size
                ]
                off += 0x10
        data = file.read(0x20000)
        block_number += 0x20000
        
for k, v in vspace.items():
    with open(os.path.join(args.output, "region_%04d.bin" % k), "wb") as file:
        for e, d in sorted(v.items()):
            file.write(d)
