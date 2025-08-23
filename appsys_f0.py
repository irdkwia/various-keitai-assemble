import argparse
import os

from utils.f0 import get_vspace

parser = argparse.ArgumentParser(description="Keitai 00F0F0 Jar Sys Extract")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-a",
    "--app-start",
    help="Chunk ID that starts app system. Varies by phone model.",
    default=5504,
    type=int,
)
parser.add_argument(
    "-b",
    "--block-shift",
    help="Shift for the blocks. 8 is for 0x10000 block size, 9 is for 0x20000 block size.",
    default=8,
    type=int,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

EXTENSIONS = ["ico", "rms", "jar", "jad"]

virtual_space = get_vspace(args.input, args.block_shift, undelete=True)

cdir = virtual_space[args.app_start - 1]
for j in range(len(cdir) // 0x38):
    off = j * 0x38
    if cdir[off : off + 8] == b"\x00\x00\x00\x00\x00\x00\x00\x00":
        continue
    for i in range(off + 0x08, off + 0x38, 0xC):
        size = int.from_bytes(cdir[i : i + 4], "little")
        if size == 0 or size == 0xFFFFFFFF:
            continue
        coff = int.from_bytes(cdir[i + 8 : i + 10], "little")
        cext = cdir[i + 10]
        cbsz = cdir[i + 11]
        data = bytearray()
        try:
            for i in range(cbsz):
                data += virtual_space[args.app_start + coff + i]
            assert len(data) == size, f"{j} {cext}"
        except:
            print("Data for %04d.%s incomplete" % (j, EXTENSIONS[cext]))
            continue
        with open(
            os.path.join(args.output, "%04d.%s" % (j, EXTENSIONS[cext])), "wb"
        ) as file:
            file.write(data)
