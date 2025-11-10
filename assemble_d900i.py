import argparse
import os

parser = argparse.ArgumentParser(description="Keitai D900i Assemble")
parser.add_argument("input")
parser.add_argument("output")

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

MAGIC = b"\x44\x41\x54\x41\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
blocks = {}

with open(args.input, "rb") as file:
    data = file.read(0x20000)
    addr = 0
    while len(data) > 0:
        if data[:0x10] == MAGIC:
            for i in range(0, 0xF8):
                offset = i * 0x10 + 0x10
                fstart = i * 0x200 + 0xF90
                blockid = int.from_bytes(data[offset : offset + 2], "big")
                if blockid == 0xFFFF:
                    continue
                bsize = int.from_bytes(data[offset + 4 : offset + 8], "big")
                blocknum = int.from_bytes(data[offset + 8 : offset + 12], "big")
                blocks[blockid] = blocks.get(blockid, [bsize, {}, blocknum])
                if blocks[blockid][2] < blocknum:
                    blocks[blockid][0] = bsize
                    blocks[blockid][2] = blocknum
                subblockid = int.from_bytes(data[offset + 2 : offset + 4], "big")
                if (
                    subblockid not in blocks[blockid][1]
                    or blocks[blockid][1][subblockid][0] < blocknum
                ):
                    blocks[blockid][1][subblockid] = (
                        blocknum,
                        data[fstart : fstart + 0x200],
                    )
        data = file.read(0x20000)
        addr += 0x20000

filedata = {}
for block_id, block_data in sorted(blocks.items()):
    block_size, block_data, _ = block_data
    i = 0
    file_data = bytearray()
    not_found = False
    while len(file_data) < block_size:
        try:
            file_data += block_data[i][1]
        except Exception as e:
            file_data += bytes(0x200)
            not_found = True
        i += 1
    if not_found:
        print("CHUNK NOT FOUND", block_id)
    filedata[block_id] = file_data[:block_size]

generated = set()

to_generate = [(1, os.path.join(args.output, "tree"))]

while len(to_generate) > 0:
    fileid, path = to_generate[0]
    del to_generate[0]
    generated.add(fileid)
    os.makedirs(path, exist_ok=True)
    offset = 0
    data = filedata[fileid]
    while offset < len(data):
        if data[offset : offset + 2] != b"\x00\x00":
            new_folder = int.from_bytes(data[offset + 0x50 : offset + 0x52], "big")
            new_fileid = int.from_bytes(data[offset + 0x52 : offset + 0x54], "big")
            fn = data[offset : offset + 0x50].decode("utf-16-be").split("\0")[0]
            if fn not in [".", ".."] and new_folder & 0x8000 == 0:
                if new_fileid in generated:
                    print(
                        "ALREADY GENERATED %d, '%s'"
                        % (new_fileid, os.path.join(path, fn))
                    )
                elif new_fileid not in filedata:
                    print(
                        "MISSING FILE %d, '%s'" % (new_fileid, os.path.join(path, fn))
                    )
                elif new_folder == 0x02:
                    to_generate.append((new_fileid, os.path.join(path, fn)))
                else:
                    with open(os.path.join(path, fn), "wb") as file:
                        file.write(filedata[new_fileid])
                    generated.add(new_fileid)
        offset += 0x54

for fileid, data in sorted(filedata.items()):
    if fileid in generated:
        continue
    os.makedirs(os.path.join(args.output, "orphan"), exist_ok=True)
    with open(os.path.join(args.output, "orphan", "%04d.bin" % fileid), "wb") as file:
        file.write(data)
