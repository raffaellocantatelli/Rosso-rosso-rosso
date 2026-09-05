"""Costruisce un JPEG minimo con EXIF veri, per provare il lettore.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Serve perché il lettore EXIF di occhio/luogo.py è scritto a mano sulla
libreria standard (Pillow qui non è installato), e un parser binario provato
su file «veri ma a caso» non è provato: si prova su byte che qualcuno ha
costruito sapendo cosa ci ha messo dentro.
"""
import struct

def raz(n, d=1): return struct.pack("<II", n, d)

def jpeg_con_exif(lat=None, lon=None, errore=None, modello="iPhone 15 Pro",
                  data="2026:09:03 18:20:11"):
    # IFD0: Make, Model, DateTime, ExifIFD ptr, GPS ptr
    heap = b""            # area dati oltre 4 byte, offset relativi al TIFF header
    def metti(b):
        nonlocal heap
        off = TIFF_LEN + len(heap)
        heap += b
        return off

    make = b"Apple\x00"; mod = modello.encode() + b"\x00"; dt = data.encode() + b"\x00"
    # dimensione fissa: header(8) + ifd0(2 + n*12 + 4) + exififd + gpsifd
    n0 = 5
    n_exif = 1
    n_gps = 5 if lat is not None else 0
    if errore is not None and n_gps: n_gps += 1
    TIFF_LEN = 8 + (2 + n0*12 + 4) + (2 + n_exif*12 + 4) + ((2 + n_gps*12 + 4) if n_gps else 0)
    off_exif = 8 + (2 + n0*12 + 4)
    off_gps = off_exif + (2 + n_exif*12 + 4)

    o_make, o_mod, o_dt = metti(make), metti(mod), metti(dt)
    def voce(tag, tipo, cnt, val):
        return struct.pack("<HHI", tag, tipo, cnt) + (val if len(val) == 4 else struct.pack("<I", val[0]))
    ifd0 = struct.pack("<H", n0)
    ifd0 += struct.pack("<HHII", 0x010F, 2, len(make), o_make)
    ifd0 += struct.pack("<HHII", 0x0110, 2, len(mod), o_mod)
    ifd0 += struct.pack("<HHII", 0x0132, 2, len(dt), o_dt)
    ifd0 += struct.pack("<HHII", 0x8769, 4, 1, off_exif)
    ifd0 += struct.pack("<HHII", 0x8825, 4, 1, off_gps if n_gps else 0)
    ifd0 += struct.pack("<I", 0)

    o_dto = metti(dt)
    ifd_exif = struct.pack("<H", n_exif)
    ifd_exif += struct.pack("<HHII", 0x9003, 2, len(dt), o_dto)
    ifd_exif += struct.pack("<I", 0)

    ifd_gps = b""
    if n_gps:
        def dms(v):
            v = abs(v); g = int(v); m = int((v-g)*60); s = ((v-g)*60-m)*60
            return raz(g) + raz(m) + raz(int(s*10000), 10000)
        o_lat, o_lon = metti(dms(lat)), metti(dms(lon))
        ifd_gps = struct.pack("<H", n_gps)
        ifd_gps += struct.pack("<HHI", 1, 2, 2) + (b"N\x00" if lat>=0 else b"S\x00") + b"\x00\x00"
        ifd_gps += struct.pack("<HHII", 2, 5, 3, o_lat)
        ifd_gps += struct.pack("<HHI", 3, 2, 2) + (b"E\x00" if lon>=0 else b"W\x00") + b"\x00\x00"
        ifd_gps += struct.pack("<HHII", 4, 5, 3, o_lon)
        if errore is not None:
            o_err = metti(raz(int(errore*100), 100))
            ifd_gps += struct.pack("<HHII", 0x001F, 5, 1, o_err)
        ifd_gps += struct.pack("<HHII", 0x0005, 1, 1, 0)   # riempitivo per il conteggio
        ifd_gps += struct.pack("<I", 0)

    tiff = b"II" + struct.pack("<HI", 42, 8) + ifd0 + ifd_exif + ifd_gps + heap
    app1 = b"Exif\x00\x00" + tiff
    seg = b"\xff\xe1" + struct.pack(">H", len(app1)+2) + app1
    return b"\xff\xd8" + seg + b"\xff\xda\x00\x02" + b"\x00"*8 + b"\xff\xd9"
