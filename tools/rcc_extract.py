#!/usr/bin/env python3
"""Extract a Qt binary resource file (.rcc, format versions 1-3).

    rcc_extract.py FILE.rcc OUTDIR

Can also extract resources compiled into an executable when given the three
file offsets of the resource blobs:

    rcc_extract.py --embedded TREE NAMES DATA [--version N] FILE OUTDIR
"""
import argparse
import os
import struct
import sys
import zlib

FLAG_COMPRESSED = 0x01
FLAG_DIRECTORY = 0x02
FLAG_ZSTD = 0x04


class Rcc:
    def __init__(self, buf, tree, names, data, version):
        self.buf, self.tree, self.names, self.data = buf, tree, names, data
        self.version = version
        self.entry_size = 14 if version < 2 else 22

    def name(self, off):
        pos = self.names + off
        (length,) = struct.unpack_from(">H", self.buf, pos)
        return self.buf[pos + 6 : pos + 6 + 2 * length].decode("utf-16-be")

    def walk(self, index=0, path=""):
        pos = self.tree + index * self.entry_size
        name_off, flags = struct.unpack_from(">IH", self.buf, pos)
        if flags & FLAG_DIRECTORY:
            count, first = struct.unpack_from(">II", self.buf, pos + 6)
            base = path if index == 0 else os.path.join(path, self.name(name_off))
            for i in range(count):
                yield from self.walk(first + i, base)
            return
        (data_off,) = struct.unpack_from(">I", self.buf, pos + 10)
        start = self.data + data_off
        (length,) = struct.unpack_from(">I", self.buf, start)
        blob = self.buf[start + 4 : start + 4 + length]
        if flags & FLAG_COMPRESSED:
            blob = zlib.decompress(blob[4:])  # qCompress: 4-byte size prefix
        elif flags & FLAG_ZSTD:
            import zstandard

            blob = zstandard.ZstdDecompressor().decompress(blob, max_output_size=1 << 30)
        yield os.path.join(path, self.name(name_off)), blob


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--embedded", nargs=3, metavar=("TREE", "NAMES", "DATA"), type=lambda s: int(s, 0))
    ap.add_argument("--version", type=int, default=3)
    ap.add_argument("file")
    ap.add_argument("outdir")
    args = ap.parse_args()

    with open(args.file, "rb") as f:
        buf = f.read()
    if args.embedded:
        tree, names, data = args.embedded
        rcc = Rcc(buf, tree, names, data, args.version)
    else:
        if buf[:4] != b"qres":
            sys.exit("not a Qt resource file")
        version, tree, data, names = struct.unpack_from(">IIII", buf, 4)
        rcc = Rcc(buf, tree, names, data, version)

    count = 0
    root = os.path.realpath(args.outdir)
    for path, blob in rcc.walk():
        dst = os.path.realpath(os.path.join(root, path))
        if not dst.startswith(root + os.sep):
            sys.exit(f"refusing path outside of output directory: {path}")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(blob)
        count += 1
    print(f"{count} files extracted to {args.outdir}")


if __name__ == "__main__":
    main()
