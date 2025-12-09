import argparse
import os

parser = argparse.ArgumentParser(description="Keitai N505iS FileSystem Read")
parser.add_argument("input")
parser.add_argument("output")

args = parser.parse_args()

with open(args.input, "rb") as file:
    data = file.read()


RANGES = [
    (0, ("unknown",), None, 0),
    (12484, ("unknown",), "bin", 12484),
    (12492, ("JAVA", "JAR"), "jar", 0),
    (12687, ("unknown",), "bin", 12687),
    (12692, ("JAVA", "SCP"), "scp", 0),
    (12887, ("unknown",), "bin", 12887),
    (12892, ("JAVA", "ADF"), "adf", 0),
    (13087, ("unknown",), "bin", 13087),
]

for i in range(0x800, 0x1E000, 8):
    if (
        data[i : i + 8] != b"\xff\xff\xff\xff\xff\xff\xff\xff"
        and data[i : i + 8] != b"\x00\x00\x00\x00\x00\x00\x00\x00"
    ):
        file_st = int.from_bytes(data[i : i + 2], "little")
        file_ed = int.from_bytes(data[i + 2 : i + 4], "little")
        file_ln = int.from_bytes(data[i + 4 : i + 8], "little")
        file_data = bytearray()
        file_st_pv = 0xFFFF
        while file_st != 0xFFFF:
            file_st_pv = file_st
            file_data += data[file_st * 0x200 : (file_st + 1) * 0x200]
            file_st = int.from_bytes(
                data[0x1E40C + file_st * 2 : 0x1E40C + file_st * 2 + 2], "little"
            )
        file_data = file_data[:file_ln]
        assert file_st_pv == file_ed
        assert len(file_data) == file_ln
        file_id = (i - 0x800) // 8
        off = -1
        while RANGES[off][0] > file_id:
            off -= 1
        r = RANGES[off]
        ext = r[2]
        if not ext:
            ext = "bin"
            if file_data[:4] == b"melo":
                ext = "mld"
            elif file_data[:4] == b"GIF8":
                ext = "gif"
            elif file_data[:3] == b"FWS" or file_data[:3] == b"CWS":
                ext = "swf"
            elif file_data[:12] == b"\x00\x00\x00\x1cftypn5lm":
                ext = "3gp"
            elif file_data[:12] == b"\x00\x00\x00\x1cftypmmp4":
                ext = "mp4"
            elif file_data[:2] == b"\xff\xd8":
                ext = "jpg"
            elif file_data[:4] == b"PK\x03\x04":
                ext = "zip"
        path = os.path.join(args.output, *r[1])
        os.makedirs(path, exist_ok=True)
        with open(
            os.path.join(path, "%05d.%s" % (file_id - r[0] + r[3], ext)), "wb"
        ) as file:
            file.write(file_data)
