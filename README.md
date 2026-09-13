# QY100 / QY70 SysEx Converter

Converts Bulk Dump SysEx (`.syx`) files between the Yamaha QY100 and QY70, so patterns and songs made on one machine can be loaded on the other. Also converts to and from the QY100's own `.Q1P` (style/pattern) and `.Q1S` (song) SmartMedia disk file formats.

Two versions of the same converter are included:

- `syx_converter.html`, a standalone browser tool. Drop a file in, get the converted file(s) back. Runs entirely client side, no upload involved.
- `SYX_Converter.py`, a batch script that reads files from local folders and writes the converted versions to an output folder.

## How it works

### SysEx: QY100 <-> QY70

Pattern (`tr` type `2`) and song (`tr` type `1`) Bulk Dump SEQ Data blocks are converted; anything else in the file is left alone. Converting only changes the machine ID nibble in the address byte, the block type, address bytes, and data are all preserved as is. Checksums are recomputed using Yamaha's two's complement convention, verified against real QY100 hardware and against `protocol.py` in [qy100-toolkit](https://github.com/doffu0000/qy100-toolkit).

### Disk files: .Q1P / .Q1S <-> SysEx

The QY70 has no disk drive, so `.Q1P`/`.Q1S` are QY100-only. Reverse engineered from paired disk/SysEx dumps of the same styles and songs: a fixed 128-byte header (signature plus a per-track block-count table) is followed by every SEQ Data block's payload with the wire format's 7-bit packing undone (147 bytes -> 128 bytes per block), concatenated in ascending track-address order. Verified against 4 pattern and 3 song reference pairs spanning 13-191 blocks, matching block-for-block.

Two minor header details don't affect playback and are approximated rather than guaranteed byte-exact: one unidentified header byte, and the padding convention used past a track's actual end (the disk format zero-fills; the wire format fills with `0xFE`). Worth double-checking a converted disk file loads correctly on real hardware before relying on it.

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
