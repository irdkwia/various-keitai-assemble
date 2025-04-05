import argparse
import os

parser = argparse.ArgumentParser(description="SoFFS Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-w",
    "--warnings",
    help="Show warnings.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-l",
    "--little-endian",
    help="Forces endianess of SoFFS data to little.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-b",
    "--big-endian",
    help="Forces endianess of SoFFS data to big. This option overrides option -l.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

MAGIC = b"\x13\x03\x43\x49\x53\x46\x39\x00\x46\x54\x4c\x31\x30\x30\x00"

byte_order = None
if args.big_endian:
    byte_order = "big"
elif args.little_endian:
    byte_order = "little"
regions = {}

with open(args.input, "rb") as file:
    data = file.read(0x80)
    while len(data) > 0:
        if data[:0x0F] == MAGIC:
            if byte_order is None:
                bam_offset_b = int.from_bytes(data[0x30:0x34], "big")
                bam_offset_l = int.from_bytes(data[0x30:0x34], "little")
                if bam_offset_b > bam_offset_l:
                    byte_order = "little"
                    print("Detected little endianess.")
                else:
                    byte_order = "big"
                    print("Detected big endianess.")
            bam_offset = int.from_bytes(data[0x30:0x34], byte_order)
            data += file.read((1 << data[0x17]) - 0x80)
            logical_eun = int.from_bytes(data[0x14:0x16], byte_order)
            vbm_pages = int.from_bytes(data[0x24:0x26], byte_order)
            eu_size = 1 << data[0x17]
            page_size = 1 << data[0x16]
            nb_pages = eu_size // page_size
            serial = int.from_bytes(data[0x28:0x2C], byte_order)
            # Data Normal, Data Replace, VBM Normal, VBM Replace, AADR to VADR, bsize
            regions[serial] = regions.get(serial, ({}, {}, {}, {}, {}, page_size))
            for x in range(nb_pages):
                off = bam_offset + 4 * x
                hinfo = int.from_bytes(data[off : off + 4], byte_order)
                if hinfo & 0x70 in (0x40, 0x60):
                    cat = 0
                    if hinfo & 0x70 == 0x60:
                        cat += 1
                    hnum = hinfo
                    if hnum & 0x80000000:
                        cat += 2
                        hnum = hnum - (0x100000000 - vbm_pages * page_size)
                    hnum &= ~(page_size - 1)
                    if cat < 2:
                        regions[serial][4][logical_eun * eu_size + x * page_size] = (
                            cat,
                            hnum,
                        )
                    regions[serial][cat][hnum] = data[
                        x * page_size : (x + 1) * page_size
                    ]
        data = file.read(0x80)

for k, v in regions.items():
    with open(os.path.join(args.output, "region_%04d.bin" % k), "wb") as file:
        for r, a in sorted(v[2].items()):
            for x in range(0, len(a), 4):
                pn = (r + x) >> 2
                pv = int.from_bytes(a[x : x + 4], byte_order) & (~0xC000007F)
                if pv == 0 and r in v[3]:
                    pv = int.from_bytes(v[3][r][x : x + 4], byte_order) & (~0xC000007F)
                file.seek(pn * v[5])
                if pv in v[4]:
                    file.write(v[v[4][pv][0]][v[4][pv][1]])
                else:
                    if args.warnings:
                        if not pv in (0, 0x3FFFFF80):
                            print("Warning: missing page %08X, %08X" % (pn * v[5], pv))
                    file.write(bytes(v[5]))
