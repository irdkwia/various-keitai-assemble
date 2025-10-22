import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai SH704i D904i Assemble")
parser.add_argument("input")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument("output")

args = parser.parse_args()

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

d = {}
e = {}
with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = nand.read(0x20000)
        spare = oob.read(0x1000)
        cs = 0
        while len(spare) > 0:
            v = int.from_bytes(spare[2:4], "little") << 8
            p = int.from_bytes(spare[6:7], "little") & 0xF
            if int.from_bytes(spare[4:6], "little") == 0xFFFF:
                e[v] = p
            for off in range(0x100):
                if (
                    spare[off * 0x10 + 1] == 0xB8
                    and spare[off * 0x10 : off * 0x10 + 4] != b"\xff\xff\xff\xff"
                ):
                    if v == (0xFFFF << 8):
                        print(hex(cs // 0x20))
                    else:
                        c = v | spare[off * 0x10]
                        d[c] = d.get(c, {})
                        d[c][p] = data[off * 0x200 : (off + 1) * 0x200]
            data = nand.read(0x20000)
            spare = oob.read(0x1000)
            cs += 0x20000

with open(args.output, "wb") as file:
    for k, v in sorted(d.items()):
        file.seek(k * 0x200)
        c = k & (~0xFF)
        x = bytearray(0)
        f = e.get(c, 0)
        for i in range(16):
            if (f + i) & 0xF in v:
                x = v[(f + i) & 0xF]
        file.write(x)
