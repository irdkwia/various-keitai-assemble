import argparse
import os

parser = argparse.ArgumentParser(description="Keitai F900i Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

blocks = {}

with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = nand.read(0x4000)
        spare = oob.read(0x200)
        addr = 0
        while len(data) > 0:
            if (
                spare[0x6:0x8] == b"\x55\x55"
                and spare[0x1C:0x20] == b"\x69\x3c\x69\x3c"
            ):
                blockid = int.from_bytes(spare[8:10], "little")
                if blockid != 0xFFFF and blockid == int.from_bytes(
                    spare[10:12], "little"
                ):
                    try:
                        assert blockid not in blocks, hex(addr)
                    except Exception as e:
                        if args.ignore:
                            print(e)
                        else:
                            raise e
                    blocks[blockid] = data
            data = nand.read(0x4000)
            spare = oob.read(0x200)
            addr += 0x200

with open(args.output, "wb") as file:
    for blockid, data in sorted(blocks.items()):
        file.seek(blockid * 0x4000)
        file.write(data)
