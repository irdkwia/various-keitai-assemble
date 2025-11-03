import argparse
import os

parser = argparse.ArgumentParser(description="Keitai 202SH Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument(
    "-s",
    "--split",
    help="Split all blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)


args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)
super_spare = bytearray()
super_data = bytearray()
with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        # TODO: may be dynamic
        nand.seek(0x26000)
        data = nand.read(0x1000)
        sectors = [
            int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)
        ]
        add_sector = 4
        for element in sectors:
            nand.seek(element * 0x20000)
            oob.seek(element * 0x1000)
            data = nand.read(0x20000)
            spare = oob.read(0x1000)
            sector_type = int.from_bytes(spare[0x24:0x28], "little")
            if add_sector == 4:
                sector_id = int.from_bytes(data[:4], "little")
            if sector_type != 0xFFFFFFFF:
                if add_sector < 4 or (
                    int.from_bytes(spare[0x4:0x8], "little") == 0xFFFFFFFE
                    and sector_id != 0xFFFFFFFF
                ):
                    super_data += bytes(max(0, sector_id * 0x80000 - len(super_data)))
                    super_data[
                        sector_id * 0x80000
                        + (4 - add_sector) * 0x20000 : sector_id * 0x80000
                        + (5 - add_sector) * 0x20000
                    ] = data
                    super_spare += bytes(max(0, sector_id * 0x4000 - len(super_spare)))
                    super_spare[
                        sector_id * 0x4000
                        + (4 - add_sector) * 0x1000 : sector_id * 0x4000
                        + (5 - add_sector) * 0x1000
                    ] = spare
                    add_sector -= 1
                    if add_sector == 0:
                        add_sector = 4
virtual_space = {}
offset = 0
block_stop = 0
s_block_id = 0
s_block_size = 0
while offset < len(super_spare):
    block_id = int.from_bytes(super_spare[offset + 4 : offset + 8], "little")
    block_size = int.from_bytes(super_spare[offset + 0x14 : offset + 0x18], "little")
    if block_stop > 0:
        assert block_id == s_block_id, s_block_id
        assert block_size == s_block_size, s_block_size
        block_stop -= 1
    else:
        if block_id not in [0xFFFFFFFE, 0xFFFFFFFF]:
            block_stop = block_size // 0x800
            if not block_size & 0x7FF:
                block_stop -= 1
            s_block_id = block_id
            s_block_size = block_size
            virtual_space[s_block_id] = super_data[
                offset * 0x20 : offset * 0x20 + s_block_size
            ]
    offset += 0x40
accumulator = bytearray()
first_block_id = 0
prev_block = 0
block_id = 0
for block_id, block_data in sorted(virtual_space.items()):
    if len(accumulator) == 0:
        first_block_id = block_id
        prev_block = block_id
    if prev_block != block_id:
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
