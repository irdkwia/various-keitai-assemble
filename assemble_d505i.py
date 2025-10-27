import argparse

parser = argparse.ArgumentParser(description="Keitai D505i Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-a",
    "--all",
    help="Return all data, even from unused blocks.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-c",
    "--compact",
    help="Compact mode. For 0x10000 structures.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

blocks = {}

cp = 2 if args.compact else 1

with open(args.input, "rb") as file:
    data = file.read(0x20000 // cp)
    addr = 0
    while len(data) > 0:
        if (
            (data[0x61] == 0xF8 or args.all)
            and data[:4] == b"\xff\xff\xff\xff"
            and data[4:8] == data[8:12]
            and data[4:8] == data[12:16]
            and data[4:8] == data[16:20]
        ):
            if data[4] == 0xF2:
                for i in range(253 // cp):
                    blockid = int.from_bytes(
                        data[0x400 // cp + i * 2 * cp : 0x400 // cp + i * 2 * cp + 2],
                        "big",
                    )
                    if blockid != 0 and blockid != 0xFFFF:
                        blockid -= 1
                        try:
                            assert blockid not in blocks, hex(
                                addr + 0x400 // cp + i * 2 + 2
                            )
                        except Exception as e:
                            if args.ignore:
                                print(e)
                            else:
                                raise e
                        blocks[blockid] = data[
                            i * 0x200
                            + 0x400 // cp
                            + 0x200 : i * 0x200
                            + 0x400 // cp
                            + 0x400
                        ]
        data = file.read(0x20000 // cp)
        addr += 0x20000 // cp

with open(args.output, "wb") as file:
    for blockid, data in sorted(blocks.items()):
        file.seek(blockid * 0x200)
        file.write(data)
