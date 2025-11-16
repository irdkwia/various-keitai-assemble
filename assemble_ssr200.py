import argparse
import os

parser = argparse.ArgumentParser(description="Keitai SSR200 Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)


args = parser.parse_args()

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = nand.read(0x4000)
        spare = oob.read(0x200)
        data_addr = 0
        virtual_space = {}
        while len(data) != 0:
            if (
                data[:0x8] == b"SSR200\x00\x00"
                and data[0x8:0x10] != b"\xff\xff\xff\xff\xff\xff\xff\xff"
            ):
                assert data[0x10:0x12] == b"\xf5\xaf", hex(data_addr)
                mode = int.from_bytes(data[0x12:0x14], "little")
                count2 = int.from_bytes(spare[0x8:0xC], "little")
                if mode == 2:
                    count = int.from_bytes(spare[0x4:0x8], "little")
                elif mode == 3:
                    count = int.from_bytes(spare[0x0:0x4], "little")
                    if count & 0xFF != 0x00 and count2 & 0xFF != 0x00:
                        count >>= 8
                        count2 >>= 8
                    else:
                        count = -1
                        count2 = -2
                else:
                    raise ValueError("Unknown SSR mode: %d" % mode)
                    count = -1
                    count2 = -2
                if count == count2:
                    assert count not in virtual_space, hex(data_addr)
                    virtual_space[count] = data_addr
            data = nand.read(0x4000)
            spare = oob.read(0x200)
            data_addr += 0x4000
        with open(args.output, "wb") as file:
            for sector_id, sector_addr in sorted(virtual_space.items()):
                nand.seek(sector_addr)
                data = nand.read(0x400)
                mode = int.from_bytes(data[0x12:0x14], "little")
                oob.seek(sector_addr // 0x20 + 0x20)
                for i in range(30):
                    data = nand.read(0x200)
                    spare = oob.read(0x10)
                    count = int.from_bytes(spare[0x0:0x4], "little")
                    count2 = int.from_bytes(spare[0x4:0x8], "little")
                    if mode == 3:
                        if count & 0xFF != 0x00 and count2 & 0xFF != 0x00:
                            count >>= 8
                            count2 >>= 8
                        else:
                            count = -1
                            count2 = -2
                    if count == count2 and spare[:4] != b"\xff\xff\xff\xff":
                        file.seek(count * 0x200)
                        file.write(data)
