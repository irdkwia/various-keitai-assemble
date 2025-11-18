import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai XSR2 Assemble")
parser.add_argument("input")
parser.add_argument(
    "-ob",
    "--input-oob",
    default=None,
    help="If not specified, a file with the same name as the input NAND file and the extension '.oob' in the same folder will be automatically used.",
)
parser.add_argument("output")

args = parser.parse_args()

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
                sector_size = 0x20000
                sector_start = int.from_bytes(
                    part_table[part + 8 : part + 12], "little"
                )
                sector_nb = int.from_bytes(part_table[part + 12 : part + 16], "little")
                nand.seek(sector_size * sector_start)
                oob.seek(sector_size * sector_start // 0x20)
                with open(
                    os.path.join(args.output, "partition_%08X.bin" % part_nb), "wb"
                ) as file:
                    if not part_table[part + 4] & 1:
                        file.write(nand.read(sector_size * sector_nb))
                    else:
                        block_list = {}
                        sector_oldness = {}
                        block_select = {}
                        sector_id = 0
                        while sector_id < sector_nb:
                            data = nand.read(sector_size)
                            spare = oob.read(sector_size // 0x20)
                            sector_id += 1
                            if (
                                data[0xC:0x10] == b"XSR2"
                                and spare[6] != 0
                                and int.from_bytes(data[0x40:0x44], "little") == part_nb
                            ):
                                sector = int.from_bytes(data[0x10:0x14], "little")
                                block = int.from_bytes(data[0x14:0x16], "little")
                                version = int.from_bytes(data[0x16:0x18], "little")
                                overwrite = False
                                if sector not in sector_oldness or sector_oldness[
                                    sector
                                ] < (block | (version << 16)):
                                    overwrite = True
                                    sector_oldness[sector] = block | (version << 16)
                                    for area in range(0x7E):
                                        for split in range(0x2):
                                            block_id = sector * 0xFC + area * 2 + split
                                            if data[0x100 + area * 0x2 + 1] >= 0xFE:
                                                block_select[block_id] = None
                                            else:
                                                block_select[block_id] = (
                                                    data[0x100 + area * 0x2] & 0x7F
                                                )
                                for area in range(0xFC):
                                    sub_id = spare[0x40 + area * 0x10 + 0x2]
                                    if sub_id ^ 0xFF == spare[0x40 + area * 0x10 + 0x3]:
                                        block_id = sector * 0xFC + sub_id
                                        block_list[block_id] = block_list.get(
                                            block_id, {}
                                        )
                                        block_list[block_id][block] = data[
                                            0x800 + 0x200 * area : 0xA00 + 0x200 * area
                                        ]
                                        if overwrite:
                                            block_select[block_id] = block
                        last_block = 0
                        for block_id, block_data in sorted(block_list.items()):
                            if last_block != block_id:
                                file.write(
                                    bytes([0xFF] * (block_id - last_block) * 0x200)
                                )
                            file.write(
                                block_data.get(
                                    block_select[block_id], bytes([0xFF] * 0x200)
                                )
                            )
                            last_block = block_id + 1
