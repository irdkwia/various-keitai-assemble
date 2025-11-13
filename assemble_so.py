import argparse
import os

parser = argparse.ArgumentParser(description="Keitai Fugue SO NAND Assemble")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-s",
    "--split",
    help="Split FAT partitions.",
    action=argparse.BooleanOptionalAction,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

with open(args.input, 'rb') as file:
    data = file.read()

len_sectors = len(data)//0x21*0x20
acc = {}
for x in range(len_sectors//0x4000):
    spr = data[len_sectors+x*0x200:len_sectors+(x+1)*0x200]
    cid = int.from_bytes(spr[0xA:0xE], 'big')
    did = int.from_bytes(spr[0x2A:0x2E], 'big')
    if cid==0xFFFFFFFF:
        continue
    if cid!=int.from_bytes(spr[0x1A:0x1E], 'big'):
        continue
    if cid!=int.from_bytes(spr[0x1EA:0x1EE], 'big'):
        continue
    if cid!=int.from_bytes(spr[0x1FA:0x1FE], 'big'):
        continue
    acc[cid] = acc.get(cid, [])
    acc[cid].append((did, x*0x4000))

final = bytearray()
for k, v in sorted(acc.items()):
    p, s = sorted(v)[-1]
    final += data[s:s+0x4000]

if not args.split:
    with open(os.path.join(args.output, "partition.bin"), 'wb') as file:
        file.write(final)
else:
    final = bytes(final).split(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xEB\x3C\x90\x47\x52\x2D\x46\x49\x4C\x45\x20')

    for i, x in enumerate(final[1:]):
        with open(os.path.join(args.output, "partition_%04d.bin"%i), 'wb') as file:
            file.write(b'\xEB\x3C\x90\x47\x52\x2D\x46\x49\x4C\x45\x20'+x)
