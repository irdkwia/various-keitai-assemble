import argparse
import os

parser = argparse.ArgumentParser(description="Keitai 934SH Assemble")
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


args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)
virtual_space = {}
alt_space = {}
leftover = bytearray()
with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = nand.read(0x20000)
        spare = oob.read(0x1000)
        spare_addr = 0
        remaining = []
        while len(data) > 0:
            sector_type = int.from_bytes(spare[0x20:0x24], "little")
            if sector_type != 0xFFFFFFFF:
                if sum(spare[:0x10]) != 0xFF0:
                    leftover += data
                else:
                    offset = 0x100
                    i = 0
                    while i < len(remaining):
                        space, remain_block, remain_size = remaining[i]
                        block_data = data[offset * 0x20 : offset * 0x20 + remain_size]
                        remain_size -= len(block_data)
                        space[remain_block] += block_data
                        if remain_size > 0:
                            remaining[i] = (space, remain_block, remain_size)
                            i += 1
                        else:
                            del remaining[i]
                    while offset < 0x1000:
                        marker = int.from_bytes(spare[offset : offset + 4], "little")
                        if marker == 0xFFFFFFFF or args.undelete:
                            block_id = int.from_bytes(
                                spare[offset + 0x30 : offset + 0x34], "little"
                            )
                            if block_id not in [0xFFFFFFFE, 0xFFFFFFFF]:
                                try:
                                    assert (
                                        block_id not in virtual_space or args.undelete
                                    ), (hex(block_id) + " " + hex(spare_addr))
                                except Exception as e:
                                    if args.ignore:
                                        print(e)
                                    else:
                                        raise e
                                size = int.from_bytes(
                                    spare[offset + 0x34 : offset + 0x38], "little"
                                )
                                block_data = data[offset * 0x20 : offset * 0x20 + size]
                                remain_size = size - len(block_data)
                                space = (
                                    alt_space if marker != 0xFFFFFFFF else virtual_space
                                )
                                alt_space[block_id] = b""
                                if remain_size > 0:
                                    remaining.append((space, block_id, remain_size))
                                space[block_id] = block_data
                        offset += 0x40
            data = nand.read(0x20000)
            spare = oob.read(0x1000)
            spare_addr += 0x1000
with open(os.path.join(args.output, "leftover.bin"), "wb") as file:
    file.write(leftover)
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
