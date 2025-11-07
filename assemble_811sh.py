import argparse
import os

parser = argparse.ArgumentParser(description="Keitai 811SH Assemble")
parser.add_argument("input_nor")
parser.add_argument("input_nand")
parser.add_argument("output")

parser.add_argument(
    "-s",
    "--split",
    help="Split all blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-u",
    "--undelete",
    help="Undelete blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)

OFFSET = 0x4000
SECTOR = 0x428000

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

virtual_space = {}
alt_space = {}
leftover = bytearray()
with open(args.input_nor, "rb") as nor:
    with open(args.input_nand, "rb") as nand:
        data = nor.read(0x20000)
        spare_addr = 0
        sector_id = 0
        remaining = []
        while len(data) > 0:
            if data[0xE:0x10] == b"\xf0\xf0":
                offset = 0x10
                while data[offset] == 0:
                    if data[offset + 1] == 0xFF or args.undelete:
                        block_id = int.from_bytes(data[offset + 4 : offset + 6], "big")
                        block_start = int.from_bytes(
                            data[offset + 6 : offset + 8], "big"
                        )
                        block_size = int.from_bytes(
                            data[offset + 8 : offset + 10], "big"
                        )
                        try:
                            assert block_id not in virtual_space or args.undelete, (
                                hex(block_id) + " " + hex(spare_addr)
                            )
                        except Exception as e:
                            if args.ignore:
                                print(e)
                            else:
                                raise e
                        nand.seek(OFFSET + sector_id * SECTOR + block_start * 0x200)
                        block_data = nand.read(block_size)
                        space = alt_space if data[offset + 1] != 0xFF else virtual_space
                        alt_space[block_id] = b""
                        space[block_id] = block_data
                    offset += 0xC
                sector_id += 1
            data = nor.read(0x20000)
            spare_addr += 0x20000
accumulator = bytearray()
first_block_id = 0
prev_block = 0
block_id = 0
for block_id, block_data in sorted(alt_space.items()):
    if block_id in virtual_space:
        block_data = virtual_space[block_id]
    if len(accumulator) == 0:
        first_block_id = block_id
        prev_block = block_id
    if prev_block != block_id:
        if len(block_data) & 0x7FF != 0 or block_id - prev_block > 500:
            with open(
                os.path.join(
                    args.output, "%04d_%04d.bin" % (first_block_id, prev_block)
                ),
                "wb",
            ) as file:
                file.write(accumulator)
            accumulator = bytearray()
            first_block_id = block_id
        else:
            accumulator += bytes(len(block_data) * (block_id - prev_block))
    accumulator += block_data
    if len(block_data) & 0x7FF != 0 or args.split:
        with open(
            os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, block_id)),
            "wb",
        ) as file:
            file.write(accumulator)
        accumulator = bytearray()
    prev_block = block_id + 1

if len(accumulator) > 0:
    with open(
        os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, block_id)), "wb"
    ) as file:
        file.write(accumulator)
