import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai SH704i D904i Assemble")
parser.add_argument("input")
parser.add_argument("output")

args = parser.parse_args()

out_oob = os.path.join(
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
            p = int.from_bytes(spare[4:6], "little", signed=True)
            for off in range(0x100):
                if (
                    spare[off * 0x10 + 1] == 0xB8
                    and spare[off * 0x10 : off * 0x10 + 4] != b"\xff\xff\xff\xff"
                ):
                    if v == (0xFFFF << 8):
                        print(hex(cs // 0x20))
                    else:
                        c = v | spare[off * 0x10]
                        if c not in e:  # e.get(c, -1) <= p:
                            e[c] = p
                            d[c] = data[off * 0x200 : (off + 1) * 0x200]
            data = nand.read(0x20000)
            spare = oob.read(0x1000)
            cs += 0x20000

with open(args.output, "wb") as file:
    for k, v in sorted(d.items()):
        file.seek(k * 0x200)
        file.write(v)
