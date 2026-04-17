import argparse
import io
import os

DEFINITIONS = {
    "811SH": {
        "OFFSET": 0x4000,
        "SECTOR": 0x428000,
        "META_BLOCK_SIZE": 0x20000,
        "BLOCK_UNIT": 0x200,
        "META_SIZE": 0xC,
        "END_LOC": 0,
        "MARK_LOC": 1,
        "BID_LOC": 4,
        "CZ_LOC": None,
        "BSTART_LOC": 6,
        "BSIZE_LOC": 8,
    },
    "705SH": {
        "OFFSET": 0x4000,
        "SECTOR": 0x3F4000,
        "META_BLOCK_SIZE": 0x20000,
        "BLOCK_UNIT": 0x200,
        "META_SIZE": 0xC,
        "END_LOC": 0,
        "MARK_LOC": 1,
        "BID_LOC": 4,
        "CZ_LOC": None,
        "BSTART_LOC": 6,
        "BSIZE_LOC": 8,
    },
    "905SH": {
        "OFFSET": 0x4000,
        "SECTOR": 0x420000,
        "META_BLOCK_SIZE": 0x20000,
        "BLOCK_UNIT": 0x200,
        "META_SIZE": 0xC,
        "END_LOC": 0,
        "MARK_LOC": 1,
        "BID_LOC": 4,
        "CZ_LOC": None,
        "BSTART_LOC": 6,
        "BSIZE_LOC": 8,
    },
    "913SH": {
        "OFFSET": 0x60000,
        "SECTOR": 0x3E0000,
        "META_BLOCK_SIZE": 0x20000,
        "BLOCK_UNIT": 0x800,
        "META_SIZE": 0xC,
        "END_LOC": 0,
        "MARK_LOC": 1,
        "BID_LOC": 4,
        "CZ_LOC": None,
        "BSTART_LOC": 6,
        "BSIZE_LOC": 8,
    },
    "921SH": {
        "OFFSET": 0x1500000,
        "SECTOR": 0x760000,
        "META_BLOCK_SIZE": 0x20000,
        "BLOCK_UNIT": 0x800,
        "META_SIZE": 0x10,
        "END_LOC": 0,
        "MARK_LOC": 1,
        "BID_LOC": 4,
        "CZ_LOC": 6,
        "BSTART_LOC": 8,
        "BSIZE_LOC": 12,
    },
    "922SH": {
        "OFFSET": 0x4000000,
        "SECTOR": 0x6A0000,
        "META_BLOCK_SIZE": 0x40000,
        "BLOCK_UNIT": 0x800,
        "META_SIZE": 0x20,
        "END_LOC": 0x10,
        "MARK_LOC": 0x11,
        "BID_LOC": 0x14,
        "CZ_LOC": 0x16,
        "BSTART_LOC": 0x18,
        "BSIZE_LOC": 0x1C,
    },
}

CONFIGS = {
    "905SH": DEFINITIONS["905SH"],
    "705SH": DEFINITIONS["705SH"],
    "811SH": DEFINITIONS["811SH"],
    "913SH": DEFINITIONS["913SH"],
    "920SH": DEFINITIONS["913SH"],
    "821SH": DEFINITIONS["921SH"],
    "921SH": DEFINITIONS["921SH"],
    "DM001SH": DEFINITIONS["913SH"],
    "922SH": DEFINITIONS["922SH"],
}

parser = argparse.ArgumentParser(description="Keitai SuperAND Assemble")
parser.add_argument("input_nor")
parser.add_argument("input_nand")
parser.add_argument("output")
parser.add_argument(
    "-c",
    "--config",
    help="Choose configuration.",
    choices=CONFIGS.keys(),
    type=str,
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

OFFSET = CONFIGS[args.config]["OFFSET"]
SECTOR = CONFIGS[args.config]["SECTOR"]
META_BLOCK_SIZE = CONFIGS[args.config]["META_BLOCK_SIZE"]
BLOCK_UNIT = CONFIGS[args.config]["BLOCK_UNIT"]
META_SIZE = CONFIGS[args.config]["META_SIZE"]
END_LOC = CONFIGS[args.config]["END_LOC"]
MARK_LOC = CONFIGS[args.config]["MARK_LOC"]
BID_LOC = CONFIGS[args.config]["BID_LOC"]
CZ_LOC = CONFIGS[args.config]["CZ_LOC"]
BSTART_LOC = CONFIGS[args.config]["BSTART_LOC"]
BSIZE_LOC = CONFIGS[args.config]["BSIZE_LOC"]

os.makedirs(args.output, exist_ok=True)

virtual_space = {}
alt_space = {}
leftover = bytearray()
with open(args.input_nor, "rb") as nor:
    with open(args.input_nand, "rb") as nand:
        seeking = -META_BLOCK_SIZE
        nor.seek(seeking, io.SEEK_END)
        data = nor.read(META_BLOCK_SIZE)
        mode = 0
        while mode < 2:
            if (mode == 0 and data[0xE:0x10] == b"\xf0\xf0") or (
                mode == 1 and data[0xE:0x10] != b"\xf0\xf0"
            ):
                mode += 1
            if mode < 2:
                seeking -= META_BLOCK_SIZE
                nor.seek(seeking, io.SEEK_END)
                if nor.tell() < META_BLOCK_SIZE:
                    break
                data = nor.read(META_BLOCK_SIZE)
        nor.seek(seeking, io.SEEK_END)
        spare_addr = nor.tell()
        sector_id = 0
        data = nor.read(META_BLOCK_SIZE)
        while len(data) > 0:
            if data[0xE:0x10] == b"\xf0\xf0":
                offset = 0x10
                while data[offset + END_LOC] == 0:
                    if data[offset + MARK_LOC] == 0xFF or args.undelete:
                        if (
                            CZ_LOC is None
                            or data[offset + CZ_LOC : offset + CZ_LOC + 2]
                            == b"\x00\x00"
                        ):
                            block_id = int.from_bytes(
                                data[offset + BID_LOC : offset + BID_LOC + 2], "big"
                            )
                            block_start = int.from_bytes(
                                data[offset + BSTART_LOC : offset + BSTART_LOC + 2],
                                "big",
                            )
                            block_size = int.from_bytes(
                                data[offset + BSIZE_LOC : offset + BSIZE_LOC + 2], "big"
                            )
                            try:
                                assert block_id not in virtual_space or args.undelete, (
                                    hex(block_id) + " " + hex(spare_addr)
                                )
                            except Exception as e:
                                if args.ignore:
                                    print(e)
                                else:
                                    raise e
                            nand.seek(
                                OFFSET + sector_id * SECTOR + block_start * BLOCK_UNIT
                            )
                            block_data = nand.read(block_size)
                            space = (
                                alt_space
                                if data[offset + MARK_LOC] != 0xFF
                                else virtual_space
                            )
                            alt_space[block_id] = b""
                            space[block_id] = block_data
                    offset += META_SIZE
                sector_id += 1
            data = nor.read(META_BLOCK_SIZE)
            spare_addr += META_BLOCK_SIZE
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
        if len(block_data) & 0x7FF != 0 or block_id - prev_block > 500:
            with open(
                os.path.join(
                    args.output, "%04d_%04d.bin" % (first_block_id, prev_block)
                ),
                "wb",
            ) as file:
                file.write(accumulator)
            accumulator = bytearray()
            first_block_id = block_id
        else:
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
