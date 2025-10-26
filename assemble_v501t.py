import argparse

parser = argparse.ArgumentParser(description="Keitai V501T Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

blocks = {}

with open(args.input, "rb") as file:
    data = file.read(0x20000)
    addr = 0
    while len(data) > 0:
        if data[:8] != b"\xff\xff\xff\xff\xff\xff\xff\xff":
            for i in range(2, 256):
                if int.from_bytes(data[i * 4 : i * 4 + 2], "little") == 0x3FF:
                    blockid = int.from_bytes(data[i * 4 + 2 : i * 4 + 4], "little")
                    try:
                        assert blockid not in blocks, hex(addr + i * 4)
                    except Exception as e:
                        if args.ignore:
                            print(e)
                        else:
                            raise e
                    blocks[blockid] = data[i * 0x200 : i * 0x200 + 0x200]
        data = file.read(0x20000)
        addr += 0x20000

with open(args.output, "wb") as file:
    for blockid, data in sorted(blocks.items()):
        file.seek(blockid * 0x200)
        file.write(data)
