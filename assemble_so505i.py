import argparse
import os

parser = argparse.ArgumentParser(description="Keitai SO505i Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument(
    "-p",
    "--partition",
    help="Use partition system.",
    action=argparse.BooleanOptionalAction,
)
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore duplicate entries.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

PARTITION_BLOCKS = 1000

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)
partition = args.partition
block = True
f = None
while block:
    try:
        with open(args.input, "rb") as nand:
            with open(out_oob, "rb") as oob:
                data = nand.read(0x200)
                spare = oob.read(0x10)
                addr = 0
                prev = (0xFFFF, 0xFFFF)
                d = {}
                while len(data) > 0:
                    id_1 = int.from_bytes(spare[6:8], "big")
                    id_2 = int.from_bytes(spare[11:13], "big")
                    assign = (
                        int.from_bytes(spare[2:4], "big")
                        if partition
                        else (0x1101 if id_1 != 0xFFFF else 0xFFFF)
                    )
                    assert (
                        id_1 == id_2
                    ), f"Error: %04X, %04X vs %04X mismatch / %08X" % (
                        assign,
                        id_1,
                        id_2,
                        addr,
                    )
                    t = prev
                    prev = (id_1, assign)
                    if prev != (0xFFFF, 0xFFFF):
                        actual_id = (id_1 & 0xFFF) >> 1
                        actual_assign = ((assign & 0xFF) >> 1, assign >> 12)
                        if prev != t:
                            d[actual_assign[0]] = d.get(actual_assign[0], {})
                            d[actual_assign[0]][actual_assign[1]] = d[
                                actual_assign[0]
                            ].get(actual_assign[1], {})
                            try:
                                assert (
                                    actual_id
                                    not in d[actual_assign[0]][actual_assign[1]]
                                ), f"Error: %04X, %04X already exists / %08X" % (
                                    assign,
                                    id_1,
                                    addr,
                                )
                            except Exception as e:
                                if args.ignore:
                                    print(e)
                                else:
                                    raise e
                            d[actual_assign[0]][actual_assign[1]][actual_id] = (
                                bytearray(data)
                            )
                        else:
                            d[actual_assign[0]][actual_assign[1]][actual_id] += data
                    addr += 0x200
                    data = nand.read(0x200)
                    spare = oob.read(0x10)
        block = False
    except Exception as e:
        partition = not partition
        if f is not None:
            raise f
        f = e

for k, v in d.items():
    with open(os.path.join(args.output, "partition_%02X.bin" % k), "wb") as file:
        for k2, v2 in sorted(v.items()):
            ldata = len(v2[min(v2)])
            m = max(v2) + 1
            if m % PARTITION_BLOCKS != 0:
                m += PARTITION_BLOCKS - (m % PARTITION_BLOCKS)
            for x in range(m):
                if x in v2:
                    file.write(v2[x])
                else:
                    file.write(bytes(ldata))
