import argparse
import os

parser = argparse.ArgumentParser(description="Keitai SH902i Assemble")
parser.add_argument("inputs", nargs="+")
parser.add_argument("output")
parser.add_argument(
    "-i",
    "--ignore",
    help="Ignore assertions.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

MAGIC = b"\x7c\x00\x00\x00\x10\x00\x1c\x00\x40\x00\x05\x39\x00\x01\x00\x02\x10\xc8\x00\x64\x0c\x00\x04\x00"

chunks = {}
filestat = {}
for s in args.inputs:
    with open(s, "rb") as file:
        data = file.read(0x40)
        while len(data) > 0:
            if data[0x14:0x2C] == MAGIC:
                data += file.read(int.from_bytes(data[0x10:0x14], "little") - 0x40)
                if data[0x30:0x34] == b"\x8c\x02\x00\x00":
                    chunks[int.from_bytes(data[0x40:0x44], "little") << 1] = data
                    offset = 0x68
                    max_offset = len(data)
                    while offset + 0x1C < max_offset:
                        if (
                            int.from_bytes(data[offset : offset + 2], "little")
                            == 0x818C
                        ) and int.from_bytes(
                            data[offset + 12 : offset + 16], "little"
                        ) == 0:
                            fileid = int.from_bytes(
                                data[offset + 8 : offset + 12], "little"
                            )
                            file_offset = (
                                int.from_bytes(
                                    data[offset + 16 : offset + 18], "little"
                                )
                                << 4
                            )
                            max_offset = min(file_offset, max_offset)
                            if offset + 0x1C > max_offset or file_offset >= len(data):
                                break
                            file_length = int.from_bytes(
                                data[offset + 18 : offset + 20], "little"
                            )
                            try:
                                assert fileid not in filestat
                            except Exception as e:
                                if args.ignore:
                                    print(e)
                                else:
                                    raise e
                            filestat[fileid] = data[
                                file_offset : file_offset + file_length
                            ]
                        offset += 0x1C
            data = file.read(0x40)

filedata = {}
for fileid, stat in sorted(filestat.items()):
    stat_chain = [
        bytearray(),
        bytearray(stat[0x1C:0x30]),
        bytearray(stat[0x30:0x34]),
        bytearray(stat[0x34:0x38]),
        bytearray(stat[0x38:0x3C]),
        bytearray(stat[0x3C:0x40]),
    ]
    while len(stat_chain) > 1:
        chunk = stat_chain[-1]
        del stat_chain[-1]
        for i in range(0, len(chunk), 4):
            w = int.from_bytes(chunk[i : i + 4], "little")
            if w != 0:
                data = chunks[w >> 24]
                w &= 0xFFFFFF
                offset = 0x14 + 0x1C * w
                file_offset = (
                    int.from_bytes(data[offset + 16 : offset + 18], "little") << 4
                )
                file_length = int.from_bytes(data[offset + 18 : offset + 20], "little")
                stat_chain[-1] += data[file_offset : file_offset + file_length]
    filedata[fileid] = stat_chain[0][: int.from_bytes(stat[8:12], "little")]

generated = set()
generated.add(1)
generated.add(3)

to_generate = [(2, os.path.join(args.output, "tree"))]

while len(to_generate) > 0:
    fileid, path = to_generate[0]
    del to_generate[0]
    if fileid in generated:
        print("ALREADY GENERATED %d, '%s'" % (fileid, path))
        continue
    if fileid not in filestat:
        print("MISSING FILE %d, '%s'" % (fileid, path))
        continue
    generated.add(fileid)
    if filestat[fileid][6:8] == b"\x01\x00":
        with open(path, "wb") as file:
            file.write(filedata[fileid])
    else:
        os.makedirs(path, exist_ok=True)
        offset = 0
        data = filedata[fileid]
        while 0 < int.from_bytes(data[offset : offset + 4], "little") < 0x80000000:
            size = int.from_bytes(data[offset : offset + 4], "little")
            new_fileid = int.from_bytes(data[offset + 4 : offset + 8], "little")
            fn = data[offset + 12 : offset + size].decode("utf-16-le").replace("\0", "")
            if new_fileid != 0:
                to_generate.append((new_fileid, os.path.join(path, fn)))
            offset += size

for fileid, data in sorted(filedata.items()):
    if fileid in generated:
        continue
    os.makedirs(os.path.join(args.output, "orphan"), exist_ok=True)
    with open(os.path.join(args.output, "orphan", "%04d.bin" % fileid), "wb") as file:
        file.write(data)
