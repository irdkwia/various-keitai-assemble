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

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

virtual_space = get_vspace(args.input, undelete=args.undelete)

if args.list_alt:
    alt_space = get_aspace(args.input)
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
k = 0
for k, v in sorted(virtual_space.items()):
    if len(accumulator) == 0:
        first_block_id = k
    accumulator += v
    if len(v) & 0xFF != 0 or args.split:
        with open(
            os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
        ) as file:
            file.write(accumulator)
        accumulator = bytearray()

if len(accumulator) > 0:
    with open(
        os.path.join(args.output, "%04d_%04d.bin" % (first_block_id, k)), "wb"
    ) as file:
        file.write(accumulator)
