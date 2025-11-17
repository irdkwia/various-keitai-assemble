import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai XSR1 Assemble")
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

os.makedirs(args.output, exist_ok=True)

block_oldness = {}
block_select = {}
with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = nand.read(0x8000)
        while len(data) > 0:
            spare = oob.read(0x400)
            if data[0xC:0x10] == b"XSR1" and spare[4] != 0:
                sector = int.from_bytes(data[0x10:0x14], "little")
                version = int.from_bytes(data[0x14:0x18], "little")
                for area in range(0x3F):
                    spare_offset = 0x10 + area * 0x10
                    if spare[spare_offset + 0x3] != 0xFF:
                        block_id = int.from_bytes(
                            spare[spare_offset : spare_offset + 0x3], "little"
                        )
                        if (
                            block_id not in block_oldness
                            or block_oldness[block_id] <= version
                        ):
                            block_select[block_id] = data[
                                0x200 * (area + 1) : 0x200 * (area + 2)
                            ]
                            block_oldness[block_id] = version
            data = nand.read(0x8000)
with open(os.path.join(args.output, "region.bin"), "wb") as file:
    last_block = 0
    for block_id, block_data in sorted(block_select.items()):
        if last_block != block_id:
            file.write(bytes([0xFF] * (block_id - last_block) * 0x200))
        file.write(block_data)
        last_block = block_id + 1
