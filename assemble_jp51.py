import argparse
import os

parser = argparse.ArgumentParser(description="Keitai J-P51 Assemble")
parser.add_argument("input")
parser.add_argument("output")

args = parser.parse_args()

elements = {}
folders = {}


def normalize(name):
    for x in range(32):
        name = name.replace(chr(x), "%02X" % x)
    return name


def get_hierarchy(h, nh=-1, t=0):
    if h not in folders:
        add = "%04X" % h
    elif nh != h:
        add = folders[h]
    else:
        add = "."
    if t == 0:
        return os.path.join(get_hierarchy(h & 0xFF00, h, t + 1), add)
    elif t == 1:
        return os.path.join(get_hierarchy(h & 0xF000, h, t + 1), add)
    else:
        return add


with open(args.input, "rb") as file:
    data = file.read(0x10000)
    sector = 0
    while len(data) > 0:
        if sum(data[:0x10]) != 0x0 and sum(data[0x10:0x20]) == 0x0:
            line = 0
            while data[line : line + 4] != b"\xff\xff\xff\xff":
                current_id = int.from_bytes(data[line + 2 : line + 4], "little")
                hierarchy = int.from_bytes(data[line + 6 : line + 8], "little")
                if current_id == 0xDDDD:
                    ml = data[0x1000 + line * 0x10 : 0x1000 + line * 0x10 + 0x100]
                    if ml[0] == 0:
                        fn = (
                            ml[1:]
                            .split(b"\0")[0]
                            .decode("shift_jis_2004")
                            .replace("\0", "")
                        )
                    else:
                        fn = ml.decode("shift_jis_2004").replace("\0", "")
                    fn = normalize(fn)
                    folders[hierarchy] = fn
                    line += 0x20
                else:
                    next_line = line + 0x10
                    while sum(data[next_line : next_line + 0x10]) == 0x0:
                        next_line += 0x10
                    blocks = (next_line - line) // 0x10
                    current_size = int.from_bytes(data[line + 12 : line + 16], "little")
                    elements[current_id] = elements.get(
                        current_id, [None, {}, current_size, hierarchy]
                    )
                    elements[current_id][1][sector] = elements[current_id][1].get(
                        sector, bytearray()
                    )
                    if data[line + 5] & 0x80:
                        elements[current_id][0] = normalize(
                            data[0x1000 + line * 0x10 : 0x1000 + line * 0x10 + 0x100]
                            .decode("shift_jis_2004")
                            .replace("\0", "")
                        )
                        elements[current_id][1][sector] += data[
                            0x1000
                            + line * 0x10
                            + 0x120 : 0x1000
                            + line * 0x10
                            + blocks * 0x100
                        ][:0x2800]
                    else:
                        elements[current_id][1][sector] += data[
                            0x1000 + line * 0x10 : 0x1000 + line * 0x10 + blocks * 0x100
                        ]
                    line = next_line
        sector += 1
        data = file.read(0x10000)

for k, v in elements.items():
    path = os.path.join(args.output, get_hierarchy(v[3]))
    os.makedirs(path, exist_ok=True)
    acc = bytearray()
    for _, d in reversed(sorted(v[1].items())):
        acc += d
    acc = acc[: v[2]]
    with open(os.path.join(path, v[0]), "wb") as file:
        file.write(acc)
