import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai XSR1 Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument(
    "-c",
    "--config",
    help="Choose configuration. Accepted values: compact, extended",
    default="compact",
    type=str,
)

args = parser.parse_args()

if args.config == "compact":
    SECTOR_SIZE = 0x4000
    NB_SIZE = 2
    OFFSET = 0
elif args.config == "extended":
    SECTOR_SIZE = 0x20000
    NB_SIZE = 1
    OFFSET = 2
else:
    raise ValueError(f"Invalid configuration: {args.config}")

out_oob = args.input_oob or os.path.join(
    os.path.dirname(args.input),
    f"{os.path.splitext(os.path.basename(args.input))[0]}.oob",
)

os.makedirs(args.output, exist_ok=True)

with open(args.input, "rb") as nand:
    with open(out_oob, "rb") as oob:
        data = b"\x00" * 0x10
        while data[:0xC] != b"XSRPARTI\x00\x10\x01\x00" and len(data) > 0:
            data = nand.read(0x10)
        if len(data) > 0:
            part_table = nand.read(0x10 * int.from_bytes(data[0xC:], "little"))
            for part in range(0, len(part_table), 0x10):
                part_nb = int.from_bytes(part_table[part : part + 4], "little")
                sector_start = int.from_bytes(
                    part_table[part + 8 : part + 12], "little"
                )
                sector_nb = int.from_bytes(part_table[part + 12 : part + 16], "little")
                nand.seek(SECTOR_SIZE * sector_start)
                oob.seek(SECTOR_SIZE * sector_start // 0x20)
                with open(
                    os.path.join(args.output, "partition_%08X.bin" % part_nb), "wb"
                ) as file:
                    if not part_table[part + 4] & 1:
                        file.write(nand.read(SECTOR_SIZE * sector_nb))
                    else:
                        block_oldness = {}
                        block_select = {}
                        sector_id = 0
                        while sector_id < sector_nb:
                            data = nand.read(SECTOR_SIZE)
                            spare = oob.read(SECTOR_SIZE // 0x20)
                            sector_id += 1
                            if data[0xC:0x10] == b"XSR1" and spare[OFFSET + 4] != 0:
                                data += nand.read(SECTOR_SIZE * (NB_SIZE - 1))
                                spare += oob.read(SECTOR_SIZE * (NB_SIZE - 1) // 0x20)
                                sector_id += NB_SIZE - 1
                                sector = int.from_bytes(data[0x10:0x14], "little")
                                version = int.from_bytes(data[0x14:0x18], "little")
                                for spare_offset in range(0, len(spare), 0x10):
                                    if spare[spare_offset + OFFSET + 0x3] != 0xFF:
                                        block_id = int.from_bytes(
                                            spare[
                                                spare_offset
                                                + OFFSET : spare_offset
                                                + OFFSET
                                                + 0x3
                                            ],
                                            "little",
                                        )
                                        if (
                                            block_id not in block_oldness
                                            or block_oldness[block_id] <= version
                                        ):
                                            block_select[block_id] = data[
                                                0x20
                                                * spare_offset : 0x20
                                                * (spare_offset + 0x10)
                                            ]
                                            block_oldness[block_id] = version
                        last_block = 0
                        for block_id, block_data in sorted(block_select.items()):
                            if last_block != block_id:
                                file.write(
                                    bytes([0xFF] * (block_id - last_block) * 0x200)
                                )
                            file.write(block_data)
                            last_block = block_id + 1
