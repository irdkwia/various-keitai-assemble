import argparse
import os

# oob must be separated
parser = argparse.ArgumentParser(description="Keitai VSH Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-c",
    "--config",
    help="Choose configuration. Accepted values: V601SH, V301SH",
    default="V601SH",
    type=str,
)
parser.add_argument(
    "-s",
    "--split",
    help="Split all blocks.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

with open(args.input, "rb") as file:
    data = file.read()

os.makedirs(args.output, exist_ok=True)

if args.config == "V601SH":
    FTLAREA = [0x72000, 0x13A000, 0x15E000, 0x1C6000]
elif args.config == "V301SH":
    FTLAREA = [0x57000, 0x11F000, 0x143000, 0x1A9000]
else:
    raise ValueError(f"Invalid configuration: {args.config}")

last = -1
sectors = []
sub_sectors = []
virtual_space = {}

for block in range(FTLAREA[0], FTLAREA[1], 0x800):
    bid = int.from_bytes(data[block + 0x7E8 : block + 0x7EC], "little")
    if bid != 0xFFFFFFFF:
        bid = bid >> 16
        total_sector = []
        y = []
        for sub in range(0, 0x7B4, 0x44):
            total_sector.append(
                int.from_bytes(data[block + sub + 0x42 : block + sub + 0x44], "little")
            )
            y.append(
                [
                    (
                        data[block + sub + subsub]
                        if data[block + sub + subsub + 1] & 0x40
                        else 0xFF
                    )
                    for subsub in range(0, 64, 2)
                ]
            )
        if last != bid:
            last = bid
            sectors.append(total_sector)
            sub_sectors.append(y)
        else:
            sectors[-1] = total_sector
            sub_sectors[-1] = y
    else:
        last = -1
        assert sum(data[block : block + 0x800]) == 0xFF * 0x800, "%08X" % block
sectors = sum(sectors, [])
sub_sectors = sum(sub_sectors, [])
extended_area = {}
for block in list(range(FTLAREA[2], FTLAREA[3], 0x800)):
    bid = int.from_bytes(data[block + 0x7E8 : block + 0x7EC], "little")
    if bid != 0xFFFFFFFF:
        bid = bid >> 16
        for sub in range(0, 0x700, 0x8):
            sector_id = int.from_bytes(
                data[block + sub + 0x0 : block + sub + 0x2], "little"
            )
            if sector_id != 0xFFFF:
                sub_sector_id = int.from_bytes(
                    data[block + sub + 0x2 : block + sub + 0x4], "little"
                )
                extended_area[((block - FTLAREA[2]) // 0x1000 * 0xE0) + (sub >> 3)] = (
                    sector_id,
                    sub_sector_id,
                    int.from_bytes(
                        data[block + sub + 0x4 : block + sub + 0x6], "little"
                    ),
                )
    else:
        assert sum(data[block : block + 0x800]) == 0xFF * 0x800, "%08X" % block
last = -1
current = -1
for block in list(range(0, FTLAREA[0], 0x800)):
    bid = int.from_bytes(data[block + 0x7E8 : block + 0x7EC], "little")
    if bid != 0xFFFFFFFF:
        bid = bid >> 16
        if last != bid:
            current += 1
            last = bid
        for sub in range(0, 0x7E0, 0x10):
            if (
                int.from_bytes(data[block + sub + 0x4 : block + sub + 0x8], "little")
                == 0xFFFFFFFF
            ):
                sector_id = int.from_bytes(
                    data[block + sub + 0x8 : block + sub + 0xA], "little"
                )
                if sector_id != 0xFFFF:
                    sub_sector_id = int.from_bytes(
                        data[block + sub + 0xA : block + sub + 0xC], "little"
                    )
                    if sub_sector_id < 32:
                        total_size = int.from_bytes(
                            data[block + sub + 0x0 : block + sub + 0x4], "little"
                        )
                        sector_size = int.from_bytes(
                            data[block + sub + 0xC : block + sub + 0xE], "little"
                        )
                        total_sector = bytearray()
                        current_size = len(total_sector)
                        while len(total_sector) < total_size:
                            sector_id_t = sectors.index(sector_id)
                            try:
                                sub_sector_id_t = sub_sectors[sector_id_t].index(
                                    sub_sector_id
                                )
                                while len(total_sector) - current_size < sector_size:
                                    total_sector += data[
                                        FTLAREA[-1]
                                        + sector_id_t * 0x4000
                                        + sub_sector_id_t * 0x200 : FTLAREA[-1]
                                        + sector_id_t * 0x4000
                                        + sub_sector_id_t * 0x200
                                        + min(
                                            0x200,
                                            sector_size
                                            - len(total_sector)
                                            + current_size,
                                        )
                                    ]
                                    sub_sector_id_t += 1
                            except Exception:
                                total_sector += bytes(sector_size)
                            if len(total_sector) < total_size:
                                try:
                                    sector_id, sub_sector_id, sector_size = (
                                        extended_area[sector_id * 0x20 + sub_sector_id]
                                    )
                                    current_size = len(total_sector)
                                except Exception:
                                    total_sector += bytes(
                                        total_size - len(total_sector)
                                    )
                        virtual_space[(current * 0x7E) + (sub >> 4)] = total_sector
    else:
        last = -1
        assert sum(data[block : block + 0x800]) == 0xFF * 0x800, "%08X" % block

accumulator = bytearray()
first_block_id = -2
last_block_id = -2
k = 0
for k, v in sorted(virtual_space.items()):
    if len(accumulator) & 0xFF != 0 or args.split or last_block_id != k - 1:
        if len(accumulator) > 0:
            with open(
                os.path.join(
                    args.output, "%05d_%05d.bin" % (first_block_id, last_block_id)
                ),
                "wb",
            ) as file:
                file.write(accumulator)
        accumulator = bytearray()
        first_block_id = k
    accumulator += v
    last_block_id = k

if len(accumulator) > 0:
    with open(
        os.path.join(args.output, "%05d_%05d.bin" % (first_block_id, last_block_id)),
        "wb",
    ) as file:
        file.write(accumulator)
