#!/usr/bin/env python3
"""Locate and extract Qt resources compiled into an executable.

    find_embedded_rcc.py EXE OUTDIR

rcc emits three arrays per resource collection, in this order: data, names,
tree. This tool finds each tree by its root entry, then searches backwards
for the names array (validated by the name hashes) and the data array
(validated by the chain of length-prefixed blobs).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcc_extract import FLAG_DIRECTORY, Rcc  # noqa: E402

ENTRY = 22  # format version >= 2
SEARCH = 64 << 20


def qt_hash(s):
    h = 0
    for ch in s:
        h = ((h << 4) + ord(ch)) & 0xFFFFFFFF
        h ^= (h & 0xF0000000) >> 23
        h &= 0x0FFFFFFF
    return h


def parse_tree(buf, tree):
    """Return the entries of a tree at offset tree, or None if implausible."""
    entries, total, i = [], 1, 0
    while i < total:
        pos = tree + i * ENTRY
        if pos + ENTRY > len(buf):
            return None
        name_off, flags = struct.unpack_from(">IH", buf, pos)
        if flags & ~0x7:
            return None
        if flags & FLAG_DIRECTORY:
            count, first = struct.unpack_from(">II", buf, pos + 6)
            if count == 0 or count > 100000 or first < 1 or first + count > 1000000:
                return None
            total = max(total, first + count)
            entries.append((name_off, True, 0))
        else:
            (data_off,) = struct.unpack_from(">I", buf, pos + 10)
            entries.append((name_off, False, data_off))
        i += 1
    return entries


def name_ok(buf, pos):
    if pos < 0 or pos + 6 > len(buf):
        return False
    length, h = struct.unpack_from(">HI", buf, pos)
    if length == 0 or length > 512 or pos + 6 + 2 * length > len(buf):
        return False
    try:
        s = buf[pos + 6 : pos + 6 + 2 * length].decode("utf-16-be")
    except UnicodeDecodeError:
        return False
    return qt_hash(s) == h


def find_names(buf, tree, entries):
    offs = sorted({e[0] for e in entries[1:]})
    for start in range(tree - offs[-1] - 6, max(0, tree - SEARCH), -1):
        if name_ok(buf, start + offs[0]) and all(name_ok(buf, start + o) for o in offs):
            return start
    return None


def find_data(buf, names, entries):
    offs = sorted({e[2] for e in entries if not e[1]})
    if not offs:
        return 0

    def chain_ok(start):
        for a, b in zip(offs, offs[1:] + [None]):
            pos = start + a
            if pos < 0 or pos + 4 > len(buf):
                return False
            (length,) = struct.unpack_from(">I", buf, pos)
            if b is not None and a + 4 + length != b:
                return False
            if b is None and pos + 4 + length > names:
                return False
        return True

    for start in range(names - offs[-1] - 4, max(0, names - SEARCH), -1):
        if chain_ok(start):
            return start
    return None


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    exe, outdir = sys.argv[1:]
    with open(exe, "rb") as f:
        buf = f.read()

    root = bytes.fromhex("000000000002")  # name offset 0, directory
    pos, found = 0, 0
    while (pos := buf.find(root, pos)) != -1:
        tree, pos = pos, pos + 1
        if struct.unpack_from(">I", buf, tree + 10)[0] != 1:
            continue
        entries = parse_tree(buf, tree)
        if not entries or len(entries) < 2:
            continue
        names = find_names(buf, tree, entries)
        if names is None:
            continue
        data = find_data(buf, names, entries)
        if data is None:
            print(f"tree {tree:#x}: names at {names:#x}, data not found", file=sys.stderr)
            continue
        try:
            files = list(Rcc(buf, tree, names, data, 3).walk())
        except Exception as err:  # a byte pattern that only looks like a tree
            print(f"tree {tree:#x}: skipped ({err})", file=sys.stderr)
            continue
        if any("\0" in path for path, _ in files):
            continue
        found += 1
        dst = os.path.join(outdir, f"res{found}")
        count = 0
        for path, blob in files:
            full = os.path.realpath(os.path.join(dst, path))
            if not full.startswith(os.path.realpath(dst) + os.sep):
                sys.exit(f"refusing path outside of output directory: {path}")
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(blob)
            count += 1
        print(f"tree {tree:#x} names {names:#x} data {data:#x}: {count} files -> {dst}")


if __name__ == "__main__":
    main()
