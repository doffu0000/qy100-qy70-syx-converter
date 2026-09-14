# QY100 / QY70 SysEx Converter

Converts Bulk Dump SysEx (`.syx`) files between the Yamaha QY100 and QY70, so patterns and songs made on one machine can be loaded on the other. Also converts to and from the QY100's own `.Q1P` (style/pattern) and `.Q1S` (song) SmartMedia disk file formats.

Two versions of the same converter are included:

- `syx_converter.html`, a standalone browser tool. Drop a file in, get the converted file(s) back. Runs entirely client side, no upload involved.
- `SYX_Converter.py`, a batch script that reads files from local folders and writes the converted versions to an output folder.

## How it works

### SysEx: QY100 <-> QY70

Pattern (`tr` type `2`) and song (`tr` type `1`) Bulk Dump SEQ Data blocks are converted; anything else in the file is left alone. Converting only changes the machine ID nibble in the address byte, the block type, address bytes, and data are all preserved as is. Checksums are recomputed using Yamaha's two's complement convention, verified against real QY100 hardware and against `protocol.py` in [qy100-toolkit](https://github.com/doffu0000/qy100-toolkit).

### Disk files: .Q1P / .Q1S <-> SysEx

The QY70 has no disk drive, so `.Q1P`/`.Q1S` are QY100-only. Reverse engineered from paired disk/SysEx dumps of the same styles and songs: a fixed 128-byte header (signature plus a per-track block-count table) is followed by every SEQ Data block's payload with the wire format's 7-bit packing undone (147 bytes -> 128 bytes per block), concatenated in ascending track-address order. Verified against 4 pattern and 3 song reference pairs spanning 13-191 blocks, matching block-for-block, then sanity checked against every real `.Q1P`/`.Q1S` file on the machine that built this (1952 patterns, 8 songs) with zero exceptions.

That larger check caught a real bug: the pattern/song "header" block's own size isn't fixed at 5/6 blocks like the original reference files all happened to have. Real patterns range from 4 to 34 blocks, so it's now derived from each file's own size instead of assumed.

Two minor details don't affect playback and remain approximated: one unidentified pattern-header byte (no correlation found against header size or track count across the full local collection), and the padding convention past a track's real data ends (the disk format zero-fills; the wire format leaves whatever was in that memory region, usually a run of `0xFE`). For songs specifically, the disk file only ever uses the first 654 of the header track's 768 bytes, confirmed against all 3 reference songs, so that tail is now zero-filled on conversion rather than carrying over the wire dump's leftover bytes. The equivalent boundary for patterns isn't pinned down yet. Worth double-checking a converted disk file loads correctly on real hardware before relying on it.

## Using the Python script

`SYX_Converter.py` expects these folders next to it:

- `QY100 SYX To Be Converted/`, QY100 `.syx` files. Produces `_QY70.syx`, plus a `.Q1P`/`.Q1S` disk file if the content is a pattern or song.
- `QY70 SYX To Be Converted/`, QY70 `.syx` files. Produces `_QY100.syx`, plus a `.Q1P`/`.Q1S` disk file if applicable.
- `Q1P To Be Converted/`, `.Q1P` style files. Produces both `_QY100.syx` and `_QY70.syx`.
- `Q1S To Be Converted/`, `.Q1S` song files. Produces both `_QY100.syx` and `_QY70.syx`.
- `Converted Files/`, where all output lands.

Run it with `python SYX_Converter.py`.

## License

Copyright (C) 2026 Doffu (<https://qy100.doffu.net/>)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

If this project has been useful to you, consider supporting future work
on Patreon: <https://www.patreon.com/doffu>.
