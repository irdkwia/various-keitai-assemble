import argparse
import os

parser = argparse.ArgumentParser(description="Keitai W31S Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)


args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        max_count = -1
        max_addr = 0
        spare = oob.read(0x10)
        spare_addr = 0
        while len(spare) != 0:
            count = int.from_bytes(spare[0x8:0xC], "big")
            if spare[6] == 0x00 and max_count < count:
                max_count = count
                max_addr = spare_addr * 0x20
            spare = oob.read(0x10)
            spare_addr += 0x10
        nand.seek(max_addr)
        data = nand.read(0x200)
        with open(args.output, "wb") as file:
            for i in range(256):
                nand.seek(int.from_bytes(data[i * 2 : i * 2 + 2], "big") * 0x200)
                subdata = nand.read(0x200)
                for j in range(256):
                    nand.seek(int.from_bytes(subdata[j * 2 : j * 2 + 2], "big") * 0x200)
                    file.write(nand.read(0x200))
