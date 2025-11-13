import argparse
import os

parser = argparse.ArgumentParser(description="Keitai Fugue SO NAND Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-s",
    "--split",
    help="Split FAT partitions.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

FAT_START = b"\xeb\x3c\x90\x47\x52\x2d\x46\x49\x4c\x45\x20"

os.makedirs(args.output, exist_ok=True)

with open(args.input, "rb") as file:
    data = file.read()

len_sectors = len(data) // 0x21 * 0x20
virtual_space = {}
for sector in range(len_sectors // 0x4000):
    spare = data[len_sectors + sector * 0x200 : len_sectors + (sector + 1) * 0x200]
    block_id = int.from_bytes(spare[0xA:0xE], "big")
    subblock_id = int.from_bytes(spare[0x2A:0x2E], "big")
    if block_id == 0xFFFFFFFF:
        continue
    if block_id != int.from_bytes(spare[0x1A:0x1E], "big"):
        continue
    if block_id != int.from_bytes(spare[0x1EA:0x1EE], "big"):
        continue
    if block_id != int.from_bytes(spare[0x1FA:0x1FE], "big"):
        continue
    virtual_space[block_id] = virtual_space.get(block_id, [])
    virtual_space[block_id].append((subblock_id, sector * 0x4000))

output = bytearray()
for _, block_data in sorted(virtual_space.items()):
    block_start = sorted(block_data)[-1][1]
    output += data[block_start : block_start + 0x4000]

if not args.split:
    with open(os.path.join(args.output, "partition.bin"), "wb") as file:
        file.write(output)
else:
    output = bytes(output).split(
        b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" + FAT_START
    )

    for partition_id, partition_data in enumerate(output[1:]):
        with open(
            os.path.join(args.output, "partition_%04d.bin" % partition_id), "wb"
        ) as file:
            file.write(FAT_START + partition_data)
