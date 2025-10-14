import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai XSR2 Assemble")
parser.add_argument("input")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used."
)
parser.add_argument("output")

args = parser.parse_args()

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

os.makedirs(args.output, exist_ok=True)

block_list = {}
sector_oldness = {}
block_select = {}
with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        addr = 0
        data = nand.read(0x20000)
        while len(data) > 0:
            spare = oob.read(0x1000)
            if data[0xC:0x10] == b"XSR2" and spare[6] != 0:
                partition = int.from_bytes(data[0x40:0x44], "little")
                sector_oldness[partition] = sector_oldness.get(partition, {})
                block_list[partition] = block_list.get(partition, {})
                block_select[partition] = block_select.get(partition, {})
                sector = int.from_bytes(data[0x10:0x14], "little")
                block = int.from_bytes(data[0x14:0x16], "little")
                version = int.from_bytes(data[0x16:0x18], "little")
                overwrite = False
                if sector not in sector_oldness[partition] or sector_oldness[partition][
                    sector
                ] < (block | (version << 16)):
                    overwrite = True
                    sector_oldness[partition][sector] = block | (version << 16)
                    for area in range(0x7E):
                        for split in range(0x2):
                            block_id = sector * 0xFC + area * 2 + split
                            if data[0x100 + area * 0x2 + 1] >= 0xFE:
                                block_select[partition][block_id] = None
                            else:
                                block_select[partition][block_id] = (
                                    data[0x100 + area * 0x2] & 0x7F
                                )
                for area in range(0xFC):
                    sub_id = spare[0x40 + area * 0x10 + 0x2]
                    if sub_id ^ 0xFF == spare[0x40 + area * 0x10 + 0x3]:
                        block_id = sector * 0xFC + sub_id
                        block_list[partition][block_id] = block_list[partition].get(
                            block_id, {}
                        )
                        block_list[partition][block_id][block] = data[
                            0x800 + 0x200 * area : 0xA00 + 0x200 * area
                        ]
                        if overwrite:
                            block_select[partition][block_id] = block
            data = nand.read(0x20000)
            addr += 0x20000

for partition, blocks in sorted(block_list.items()):
    with open(os.path.join(args.output, "region_%04d.bin" % partition), "wb") as file:
        last_block = 0
        for block_id, block_data in sorted(blocks.items()):
            if last_block != block_id:
                file.write(bytes([0xFF] * (block_id - last_block) * 0x200))
            file.write(
                block_data.get(block_select[partition][block_id], bytes([0xFF] * 0x200))
            )
            last_block = block_id + 1
