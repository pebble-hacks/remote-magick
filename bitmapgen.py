#!/usr/bin/env python

import StringIO
import argparse
import os
import struct
import sys
import png

WHITE_COLOR_MAP = {
    'white' : 1,
    'black' : 0,
    'transparent' : 0,
    }

BLACK_COLOR_MAP = {
    'white' : 0,
    'black' : 1,
    'transparent' : 0,
    }

# Bitmap struct (NB: All fields are little-endian)
#         (uint16_t) row_size_bytes
#         (uint16_t) info_flags
#                         bit 0 : reserved (must be zero for bitmap files)
#                    bits 12-15 : file version
#         (int16_t)  bounds.origin.x
#         (int16_t)  bounds.origin.y
#         (int16_t)  bounds.size.w
#         (int16_t)  bounds.size.h
#         (uint32_t) image data (word-aligned, 0-padded rows of bits)

class PebbleBitmap(object):
    def __init__(self, path, color_map = WHITE_COLOR_MAP):
        self.version = 1
        self.path = path
        self.name, _ = os.path.splitext(os.path.basename(path))
        self.color_map = color_map
        width, height, pixels, metadata = png.Reader(filename=path).asFloat()
        self._im_pixels = list(self._convert_pixels(pixels, metadata))
        self._im_size = (width, height)
        self._set_bbox()

    def _convert_pixels(self, pixels, metadata):
        raw_pixels = [[int(p * 255) for p in row] for row in pixels]
        get_pixel = {
            (True, False): self._pixel_from_l,
            (True, True): self._pixel_from_la,
            (False, False): self._pixel_from_rgb,
            (False, True): self._pixel_from_rgba,
        }[(metadata['greyscale'], metadata['alpha'])]
        converted_pixels = []
        for row in raw_pixels:
            converted_pixels.append([])
            while row:
                converted_pixels[-1].append(get_pixel(row))
        return converted_pixels

    def _pixel_from_l(self, row):
        p = row.pop(0)
        return [p, p, p, 255]

    def _pixel_from_la(self, row):
        p = row.pop(0)
        return [p, p, p, row.pop(0)]

    def _pixel_from_rgb(self, row):
        return [row.pop(0), row.pop(0), row.pop(0), 255]

    def _pixel_from_rgba(self, row):
        return [row.pop(0), row.pop(0), row.pop(0), row.pop(0)]

    def _set_bbox(self):
        left, top = (0, 0)
        right, bottom = self._im_size

        alphas = [[p[3] for p in row] for row in self._im_pixels]
        alphas_transposed = zip(*alphas)
        for row in alphas:
            if any(row):
                break
            top += 1
        for row in reversed(alphas):
            if any(row):
                break
            bottom -= 1
        for row in alphas_transposed:
            if any(row):
                break
            left += 1
        for row in reversed(alphas_transposed):
            if any(row):
                break
            right -= 1

        self.x = left
        self.y = top
        self.w = right - left
        self.h = bottom - top

    def row_size_bytes(self):
        """
        Return the length of the bitmap's row in bytes.

        Row lengths are rounded up to the nearest word, padding up to
        3 empty bytes per row.
        """

        row_size_padded_words = (self.w + 31) / 32
        return row_size_padded_words * 4

    def info_flags(self):
        """Returns the type and version of bitmap."""

        return self.version << 12

    def pbi_header(self):
        return struct.pack('<HHhhhh',
                           self.row_size_bytes(),
                           self.info_flags(),
                           self.x,
                           self.y,
                           self.w,
                           self.h)

    def image_bits(self):
        """
        Return a raw bitmap capable of being rendered using Pebble's bitblt graphics routines.

        The returned bitmap will always be y * row_size_bytes large.
        """

        def get_monochrome_value_for_pixel(pixel):
            if pixel[3] < 127:
                return self.color_map['transparent']
            if ((pixel[0] + pixel[1] + pixel[2]) / 3) < 127:
                return self.color_map['black']
            return self.color_map['white']

        def pack_pixels_to_bitblt_word(pixels, x_offset, x_max):
            word = 0
            for column in xrange(0, 32):
                x = x_offset + column
                if (x < x_max):
                    pixel = pixels[x]
                    word |= get_monochrome_value_for_pixel(pixel) << (column)

            return struct.pack('<I', word)

        src_pixels = self._im_pixels
        out_pixels = []
        row_size_words = self.row_size_bytes() / 4

        for row in xrange(self.y, self.y + self.h):
            x_max = self._im_size[0]
            for column_word in xrange(0, row_size_words):
                x_offset = self.x + column_word * 32
                out_pixels.append(pack_pixels_to_bitblt_word(src_pixels[row],
                                                             x_offset,
                                                             x_max))

        return ''.join(out_pixels)

    def header(self):
        f = StringIO.StringIO()
        f.write("// GBitmap + pixel data generated by bitmapgen.py:\n\n")
        f.write("static const uint8_t s_{0}_pixels[] = {{\n    ".format(self.name))
        bytes = self.image_bits()
        for byte, index in zip(bytes, xrange(0, len(bytes))):
            if index != 0 and index % 16 == 0:
                f.write("/* bytes {0} - {1} */\n    ".format(index-16, index))
            f.write("0x%02x, " % ord(byte))
        f.write("\n};\n\n")
        f.write("static const GBitmap s_{0}_bitmap = {{\n".format(self.name))
        f.write("  .addr = (void*) &s_{0}_pixels,\n".format(self.name))
        f.write("  .row_size_bytes = {0},\n".format(self.row_size_bytes()))
        f.write("  .info_flags = 0x%02x,\n" % self.info_flags())
        f.write("  .bounds = {\n")
        f.write("    .origin = {{ .x = {0}, .y = {1} }},\n".format(self.x, self.y))
        f.write("    .size = {{ .w = {0}, .h = {1} }},\n".format(self.w, self.h))
        f.write("  },\n")
        f.write("};\n\n")
        return f.getvalue()

    def convert_to_h(self, header_file=None):
        to_file = header_file if header_file else (os.path.splitext(self.path)[0] + '.h')
        with open(to_file, 'w') as f:
            f.write(self.header())
        return to_file

    def convert_to_pbi(self, pbi_file=None):
        to_file = pbi_file if pbi_file else (os.path.splitext(self.path)[0] + '.pbi')
        with open(to_file, 'wb') as f:
            f.write(self.pbi_header())
            f.write(self.image_bits())
        return to_file


def cmd_pbi(args):
    pb = PebbleBitmap(args.input_png)
    pb.convert_to_pbi(args.output_pbi)

def cmd_header(args):
    pb = PebbleBitmap(args.input_png)
    print pb.header()

def cmd_white_trans_pbi(args):
    pb = PebbleBitmap(args.input_png, WHITE_COLOR_MAP)
    pb.convert_to_pbi(args.output_pbi)

def cmd_black_trans_pbi(args):
    pb = PebbleBitmap(args.input_png, BLACK_COLOR_MAP)
    pb.convert_to_pbi(args.output_pbi)

def process_all_bitmaps():
    directory = "bitmaps"
    paths = []
    for _, _, filenames in os.walk(directory):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.png':
                paths.append(os.path.join(directory, filename))

    header_paths = []
    for path in paths:
        b = PebbleBitmap(path)
        b.convert_to_pbi()
        to_file = b.convert_to_h()
        header_paths.append(os.path.basename(to_file))

    f = open(os.path.join(directory, 'bitmaps.h'), 'w')
    print>>f, '#pragma once'
    for h in header_paths:
        print>>f, "#include \"{0}\"".format(h)
    f.close()

def process_cmd_line_args():
    parser = argparse.ArgumentParser(description="Generate pebble-usable files from png images")
    subparsers = parser.add_subparsers(help="commands", dest='which')

    pbi_parser = subparsers.add_parser('pbi', help="make a .pbi (pebble binary image) file")
    pbi_parser.add_argument('input_png', metavar='INPUT_PNG', help="The png image to process")
    pbi_parser.add_argument('output_pbi', metavar='OUTPUT_PBI', help="The pbi output file")
    pbi_parser.set_defaults(func=cmd_pbi)

    h_parser = subparsers.add_parser('header', help="make a .h file")
    h_parser.add_argument('input_png', metavar='INPUT_PNG', help="The png image to process")
    h_parser.set_defaults(func=cmd_header)

    white_pbi_parser = subparsers.add_parser('white_trans_pbi', help="make a .pbi (pebble binary image) file for a white transparency layer")
    white_pbi_parser.add_argument('input_png', metavar='INPUT_PNG', help="The png image to process")
    white_pbi_parser.add_argument('output_pbi', metavar='OUTPUT_PBI', help="The pbi output file")
    white_pbi_parser.set_defaults(func=cmd_white_trans_pbi)

    black_pbi_parser = subparsers.add_parser('black_trans_pbi', help="make a .pbi (pebble binary image) file for a black transparency layer")
    black_pbi_parser.add_argument('input_png', metavar='INPUT_PNG', help="The png image to process")
    black_pbi_parser.add_argument('output_pbi', metavar='OUTPUT_PBI', help="The pbi output file")
    black_pbi_parser.set_defaults(func=cmd_black_trans_pbi)

    args = parser.parse_args()
    args.func(args)

def main():
    if (len(sys.argv) < 2):
        # process everything in the  bitmaps folder
        process_all_bitmaps()
    else:
        # process an individual file
        process_cmd_line_args()

if __name__ == "__main__":
    main()
