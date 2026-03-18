import argparse
import os

from utils.f0 import get_aspace, get_vspace

parser = argparse.ArgumentParser(description="Keitai 00F0F0 Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-l",
    "--list-alt",
    help="Lists alternatives for each block that has any.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-u",
    "--undelete",
    help="Undelete unused blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-s",
    "--split",
    help="Split all blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-b",
    "--block-shift",
    help="Size of the blocks, expressed in a power of 2. 8 is for 0x100 block size, 9 is for 0x200 block size.",
    default=8,
    type=int,
)
parser.add_argument(
    "-n",
    "--number-block",
    help="Number of blocks for each sector, expressed in a power of 2. Default is 8 for 2^8 blocks per sector.",
    default=8,
    type=int,
)
parser.add_argument(
    "-c",
    "--compact-size",
    help="Use compact size.",
    default=None,
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-x",
    "--overflow-block",
    help="Size for which block overflows, expressed in a power of 2. Default is None.",
    default=None,
    type=int,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

virtual_space = get_vspace(
    args.input,
    args.block_shift,
    args.number_block,
    args.compact_size,
    undelete=args.undelete,
)

if args.list_alt:
    alt_space = get_aspace(
        args.input, args.block_shift, args.number_block, args.compact_size
    )
    for k, v in sorted(alt_space.items()):
        compl = set()
        toprint = False
        lines = []
        for x in sorted(v, key=lambda x: (1 - int(x[2]), x[0])):
            if x[3] not in compl:
                compl.add(x[3])
                if not x[2]:
                    toprint = True
                lines.append("\t%08X\t%04X\t%s" % (x[0], x[1], "*" if x[2] else ""))
        if toprint:
            print(k)
            print("\n".join(lines))

accumulator = bytearray()
first_block_id = 0
prev_block = 0
k = 0
old_size = 0
for k, v in sorted(virtual_space.items()):
    if len(accumulator) == 0:
        first_block_id = k
        prev_block = k
    if prev_block < k:
        accumulator += bytes(old_size * (k - prev_block))
    old_size = len(v)
    if args.overflow_block:
        old_size = min(old_size, 1 << args.overflow_block)
        k += (len(v) - 1) // (1 << args.overflow_block)
    accumulator += v
    if len(v) & 0xFF != 0 or args.split:
        with open(
            os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
        ) as file:
            file.write(accumulator)
        accumulator = bytearray()
    prev_block = k + 1

if len(accumulator) > 0:
    with open(
        os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
    ) as file:
        file.write(accumulator)
