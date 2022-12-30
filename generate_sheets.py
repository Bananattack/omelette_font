#!/usr/bin/env python
import collections
import os
import os.path
import PIL.Image # requires Pillow / PIL -- pip install pillow
import shutil
import svgwrite # requires svgwrite -- pip install svgwrite
import common

TRANSPARENT = (0, 0, 0, 0)
MAGENTA = (255, 0, 255, 255)
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)

PALETTE_DEFAULTS = [
    MAGENTA,
    BLACK,
    WHITE,
]

FontVariant = collections.namedtuple('FontVariant', ['name', 'generate_func', 'suffix'])

def create_silhouette(source_image, fill_color, remove_shadows=False):
    result_image = source_image.copy()
    result_data = result_image.load()
    w, h = result_image.size

    for x in range(w): 
        for y in range(h):
            color = result_data[(x, y)]
            result_data[(x, y)] = fill_color if color[3] != 0 and (not remove_shadows or color != BLACK) else TRANSPARENT

    return result_image

def get_average_brightness(color):
    return (int(color[0]) + int(color[1]) + int(color[2])) // 3

def create_monochrome_sheet(source_image, glyph_size, remove_shadows=False):
    # TODO: figure out why the whole image is white pixels.

    result_image = source_image.copy()
    result_data = result_image.load()
    w, h = result_image.size
    glyph_width, glyph_height = glyph_size

    for x in range(0, w, glyph_width): 
        for y in range(0, h, glyph_height):
            min_brightness = None
            max_brightness = None
            for i in range(glyph_width): 
                for j in range(glyph_height):
                    color = result_data[(x + i, y + j)]

                    if color[3] == 0 or color == BLACK:
                        continue

                    brightness = get_average_brightness(color)

                    if min_brightness is None:
                        min_brightness = brightness
                    else:
                        min_brightness = min(min_brightness, brightness)

                    if max_brightness is None:
                        max_brightness = brightness
                    else:
                        max_brightness = max(max_brightness, brightness)                        

            weight = 0.25
            cutoff_brightness = int(min_brightness * (1 - weight) + max_brightness * weight)
            if max_brightness == 255 and min_brightness < 128:
                cutoff_brightness = 100

            for i in range(glyph_width): 
                for j in range(glyph_height):
                    color = result_data[(x + i, y + j)]

                    if color[3] == 0:
                        continue
                    elif remove_shadows and color == BLACK:
                        result_data[(x + i, y + j)] = TRANSPARENT
                    else:
                        brightness = get_average_brightness(color)
                        result_data[(x + i, y + j)] = WHITE if brightness >= cutoff_brightness else (TRANSPARENT if remove_shadows else BLACK)

    return result_image

def erase_grid_bleed(image, grid_size, erase_h, erase_v):
    data = image.load()
    w, h = image.size

    for x in range(w): 
        for y in range(h):
            if erase_h and x % grid_size[0] == 0 \
            or erase_v and y % grid_size[1] == 0:
                data[(x, y)] = TRANSPARENT

    return image

def replace_color(image, search_color, replacement_color):
    data = image.load()
    w, h = image.size

    for x in range(w): 
        for y in range(h):
            if data[(x, y)] == search_color:
                data[(x, y)] = replacement_color

    return image

def isolate_shadow(image, fill_color):
    data = image.load()
    w, h = image.size

    for x in range(w): 
        for y in range(h):
            data[(x, y)] = fill_color if data[(x, y)] == BLACK else TRANSPARENT

    return image

def find_used_indexes(indexed_image):
    data = indexed_image.load()
    w, h = indexed_image.size
    unordered_used_indexes = set()
    ordered_used_indexes = []
    
    for x in range(w):
        for y in range(h):
            index = data[(x, y)]
            if index not in unordered_used_indexes:
                unordered_used_indexes.add(index)

    for i in unordered_used_indexes:
        if i not in PALETTE_DEFAULTS:
            ordered_used_indexes.append(i)

    ordered_used_indexes.sort()

    for i in reversed(PALETTE_DEFAULTS):
        if i in unordered_used_indexes:
            ordered_used_indexes.insert(0, i)

    return ordered_used_indexes

def generate_plain_variant(source_image, subsheet):
    return source_image.copy()

def generate_plain_black_variant(source_image, subsheet):
    return replace_color(source_image.copy(), WHITE, BLACK)

def generate_hshadow_variant(source_image, subsheet):
    result_image = PIL.Image.new('RGBA', source_image.size, TRANSPARENT)
    silhouette_image = create_silhouette(source_image, BLACK)

    result_image.paste(silhouette_image, (1, 0), silhouette_image)
    erase_grid_bleed(result_image, subsheet.glyph_size, True, False)
    result_image.paste(source_image, (0, 0), source_image)

    return result_image

def generate_vshadow_variant(source_image, subsheet):
    result_image = PIL.Image.new('RGBA', source_image.size, TRANSPARENT)
    silhouette_image = create_silhouette(source_image, BLACK)

    result_image.paste(silhouette_image, (0, 1), silhouette_image)
    erase_grid_bleed(result_image, subsheet.glyph_size, False, True)
    result_image.paste(source_image, (0, 0), source_image)

    return result_image

def generate_hvshadow_variant(source_image, subsheet):
    result_image = PIL.Image.new('RGBA', source_image.size, TRANSPARENT)
    silhouette_image = create_silhouette(source_image, BLACK)

    result_image.paste(silhouette_image, (1, 0), silhouette_image)
    result_image.paste(silhouette_image, (0, 1), silhouette_image)
    result_image.paste(silhouette_image, (1, 1), silhouette_image)
    erase_grid_bleed(result_image, subsheet.glyph_size, True, True)
    result_image.paste(source_image, (0, 0), source_image)

    return result_image

def generate_silhouette_variant(source_image, subsheet):
    return create_silhouette(source_image, WHITE, remove_shadows=True)

def generate_isolate_shadow_variant(source_image, subsheet):
    return isolate_shadow(source_image.copy(), WHITE)

def generate_hshadow_outline_variant(source_image, subsheet):
    return isolate_shadow(generate_hshadow_variant(source_image, subsheet), WHITE)

def generate_vshadow_outline_variant(source_image, subsheet):
    return isolate_shadow(generate_vshadow_variant(source_image, subsheet), WHITE)

def generate_hvshadow_outline_variant(source_image, subsheet):
    return isolate_shadow(generate_hvshadow_variant(source_image, subsheet), WHITE)

def generate_monochrome_shadow_variant(source_image, subsheet):
    return create_monochrome_sheet(source_image, subsheet.glyph_size, remove_shadows=False)

def generate_monochrome_no_shadow_variant(source_image, subsheet):
    return create_monochrome_sheet(source_image, subsheet.glyph_size, remove_shadows=True)

FONT_VARIANTS = {
    'plain': FontVariant('plain', generate_plain_variant, 'plain'),
    'plain_black': FontVariant('plain_black', generate_plain_black_variant, 'plain_black'),
    'hshadow': FontVariant('hshadow', generate_hshadow_variant, 'hshadow'),
    'vshadow': FontVariant('vshadow', generate_vshadow_variant, 'vshadow'),
    'hvshadow': FontVariant('hvshadow', generate_hvshadow_variant, 'hvshadow'),
    'monochrome_shadow': FontVariant('monochrome_shadow', generate_monochrome_shadow_variant, 'monochrome_shadow'),
    'monochrome_plain': FontVariant('monochrome_plain', generate_monochrome_no_shadow_variant, 'monochrome_plain'),
    'silhouette': FontVariant('silhouette', generate_silhouette_variant, 'silhouette'),
    'shadow_outline': FontVariant('shadow_outline', generate_isolate_shadow_variant, 'shadow_outline'),
    'hshadow_outline': FontVariant('hshadow_outline', generate_hshadow_outline_variant, 'hshadow_outline'),
    'vshadow_outline': FontVariant('vshadow_outline', generate_vshadow_outline_variant, 'vshadow_outline'),
    'hvshadow_outline': FontVariant('hvshadow_outline', generate_hvshadow_outline_variant, 'hvshadow_outline'),
}



FontSubsheet = collections.namedtuple('FontSubsheet', ['name', 'kind', 'category', 'region', 'glyph_size', 'ascent_descent', 'variants'])

def get_font_subsheet_glyph_info(subsheet, glyph_index):
    return (common.CHARACTERS_TO_FONT_PATHNAMES.get(glyph_index + 32), glyph_index + 32)

def get_icon_subsheet_glyph_info(subsheet, glyph_index):
    if subsheet.category == 'icons':
        try:
            glyph_name = common.FONT_ICON_GLYPH_NAMES[glyph_index]
            return (glyph_name, glyph_index)
        except IndexError:
            pass
    elif subsheet.category == 'window':
        try:
            glyph_name = common.FONT_WINDOW_GLYPH_NAMES[glyph_index]
            return (glyph_name, glyph_index)
        except IndexError:
            pass
    elif subsheet.category == 'buttons':
        pass

    return ('icon', glyph_index)

FONT_SUBSHEET_GET_GLYPH_INFO_FUNCS = {
    'font': get_font_subsheet_glyph_info, 
    'icon': get_icon_subsheet_glyph_info
}

def get_subsheet_glyph_info(subsheet, glyph_index):
    func = FONT_SUBSHEET_GET_GLYPH_INFO_FUNCS.get(subsheet.kind)
    return func(subsheet, glyph_index) if func else ('unknown' + str(glyph_index), glyph_index)

FONT_SUBSHEETS = {
    'tiny': FontSubsheet('tiny', 'font', None, (192, 0, 64, 24), (4, 4), (4, 0), ['plain', 'plain_black', 'hshadow']),
    'small': FontSubsheet('small', 'font', None, (128, 0, 64, 48), (4, 8), (6, 2), ['plain', 'plain_black', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']),
    'thin': FontSubsheet('thin', 'font', None, (128, 48, 128, 48), (8, 8), (6, 2), ['plain', 'plain_black', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']),
    'thick': FontSubsheet('thick', 'font', None, (0, 0, 128, 48), (8, 8), (6, 2), ['plain', 'plain_black', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']),
    'tall': FontSubsheet('tall', 'font', None, (0, 48, 128, 96), (8, 16), (14, 2), ['plain', 'plain_black', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']),
    'large': FontSubsheet('large', 'font', None, (0, 144, 256, 96), (16, 16), (14, 2), ['plain', 'plain_black', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']),
    'window': FontSubsheet('window', 'icon', 'window', (192, 24, 64, 24), (8, 8), (6, 2), ['plain', 'silhouette', 'shadow_outline']),
    'buttons': FontSubsheet('buttons', 'icon', 'buttons', (128, 96, 128, 48), (8, 8), (6, 2), ['plain', 'silhouette', 'shadow_outline', 'monochrome_shadow']),
    'icons': FontSubsheet('icons', 'icon', 'icons', (0, 240, 256, 16), (8, 8), (6, 2), ['plain', 'silhouette', 'shadow_outline']),
}



FontValidator = collections.namedtuple('FontValidator', ['validate_func'])    

def validate_1bpp(variant, rgba_image, indexed_image):
    return variant.suffix != 'plain_black' and len(find_used_indexes(indexed_image)) <= 2

def validate_2bpp(variant, rgba_image, indexed_image):
    return len(find_used_indexes(indexed_image)) <= 4

def validate_3c(variant, rgba_image, indexed_image):
    return len(find_used_indexes(indexed_image)) <= 3

def validate_4bpp(variant, rgba_image, indexed_image):
    return len(find_used_indexes(indexed_image)) <= 16

def validate_8bpp(variant, rgba_image, indexed_image):
    return len(find_used_indexes(indexed_image)) <= 256

def validate_unsupported(variant, rgba_image, indexed_image):
    return False

FONT_VALIDATORS = {
    '1bpp': FontValidator(validate_1bpp),
    '2bpp': FontValidator(validate_2bpp),
    '3c': FontValidator(validate_3c),
    '4bpp': FontValidator(validate_4bpp),
    '8bpp': FontValidator(validate_8bpp),
    'unsupported': FontValidator(validate_unsupported),
}



FontFormatKind = collections.namedtuple('FontFormatKind', ['save_func'])

def open_file_verbose(path, mode):
    print('  - Writing "' + path + '"...')    
    return open(path, mode)

def create_directory_verbose(path):
    print('Creating directory "' + path + '"...')
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

def save_binary(subsheet, variant, format, output_path, rgba_image, indexed_image):
    with open_file_verbose(output_path, 'wb') as output_file:
        format.write_func(output_file, subsheet, variant, rgba_image, indexed_image)

def save_text(subsheet, variant, format, output_path, rgba_image, indexed_image):
    with open_file_verbose(output_path, 'w') as output_file:
        format.write_func(output_file, subsheet, variant, rgba_image, indexed_image)

def save_folder(file_mode, subsheet, variant, format, output_path, rgba_image, indexed_image):
    stripped_path, extension = os.path.splitext(output_path)

    create_directory_verbose(stripped_path)

    image_width, image_height = rgba_image.size
    glyph_width, glyph_height = subsheet.glyph_size
    column_count, row_count = image_width // glyph_width, image_height // glyph_height
    print('image size ' + repr(rgba_image.size))
    print('glyph size ' + repr(subsheet.glyph_size))
    print('column count ' + repr(column_count) + ', row count ' + repr(row_count))

    for glyph_index in range(row_count * column_count):
        glyph_name, remapped_index = get_subsheet_glyph_info(subsheet, glyph_index)
        remapped_index_padded_str = '{:03d}'.format(remapped_index)
        glyph_path = os.path.join(stripped_path, os.path.basename(stripped_path) + '_' + remapped_index_padded_str + '_' + glyph_name + '.' + format.extension)

        glyph_x = (glyph_index % column_count) * glyph_width
        glyph_y = (glyph_index // column_count) * glyph_height
        crop_area = (glyph_x, glyph_y, glyph_x + glyph_width, glyph_y + glyph_height)
        print('crop area ' + repr(crop_area))

        glyph_rgba_image = rgba_image.crop(crop_area)
        glyph_indexed_image = indexed_image.crop(crop_area)

        with open_file_verbose(glyph_path, file_mode) as glyph_file:
            format.write_func(glyph_file, subsheet, variant, glyph_rgba_image, glyph_indexed_image)

def save_text_folder(subsheet, variant, format, output_path, rgba_image, indexed_image):
    save_folder('w', subsheet, variant, format, output_path, rgba_image, indexed_image)

def save_binary_folder(subsheet, variant, format, output_path, rgba_image, indexed_image):
    save_folder('wb', subsheet, variant, format, output_path, rgba_image, indexed_image)

FONT_FORMAT_KINDS = {
    'binary': FontFormatKind(save_binary),
    'text': FontFormatKind(save_text),
    'text_folder': FontFormatKind(save_text_folder),
    'binary_folder': FontFormatKind(save_binary_folder),
}



FontFormat = collections.namedtuple('FontFormat', ['extension', 'suffix', 'kind', 'write_func', 'validators'])

COLOR_MAPPING_1BPP = [0, 0, 1]
COLOR_MAPPING_3C = [0, 1, 3]

# https://en.wikipedia.org/wiki/Glyph_Bitmap_Distribution_Format
# https://en.wikipedia.org/wiki/X_logical_font_description
# https://www.x.org/docs/BDF/bdf.pdf
# https://adobe-type-tools.github.io/font-tech-notes/pdfs/5005.BDF_Spec.pdf
# This probably has errors... Wish it were easier to know if this is up to spec, looked at other fonts + read the format spec.
def write_bdf(output_file, subsheet, variant, rgba_image, indexed_image):
    RESOLUTION = 72
    POINT_SIZE = 100
    AVERAGE_WIDTH = 90
    CHARSET_REGISTRY = 'ISO8859'
    CHARSET_ENCODING = '1'

    region_x, region_y, region_width, region_height = subsheet.region

    glyph_width, glyph_height = subsheet.glyph_size
    glyph_columns = region_width // glyph_width
    glyph_rows = region_height // glyph_height
    glyph_count = glyph_columns * glyph_rows

    ascent, descent = subsheet.ascent_descent
    basename = os.path.basename(output_file.name)
    description = '-' + common.FONT_AUTHOR \
        + '-' + common.FONT_NAME \
        + '_' + subsheet.name \
        + '_' + variant.name \
        + '-medium-r-normal' \
        + '--' + str(glyph_width) \
        + '-' + str(POINT_SIZE) \
        + '-' + str(RESOLUTION) \
        + '-' + str(RESOLUTION) \
        + '-m' \
        + '-' + str(AVERAGE_WIDTH) \
        + '-' + str(CHARSET_REGISTRY) \
        + '-' + str(CHARSET_ENCODING)

    output_file.write('STARTFONT 2.1\n')
    output_file.write('COMMENT ' + common.FONT_COPYRIGHT + '\n')
    output_file.write('COMMENT ' + basename + '\n')
    output_file.write('FONT ' + description + '\n')
    output_file.write('SIZE {} {} {}\n'.format(glyph_width, RESOLUTION, RESOLUTION))
    output_file.write('FONTBOUNDINGBOX {} {} {} {}\n'.format(glyph_width, glyph_height, 0, -descent))

    output_file.write('STARTPROPERTIES 13\n')
    output_file.write('FONT_ASCENT ' + str(ascent) + ' \n')
    output_file.write('FONT_DESCENT ' + str(descent) + '\n')
    output_file.write('PIXEL_SIZE ' + str(glyph_height) + '\n')
    output_file.write('POINT_SIZE ' + str(POINT_SIZE) + '\n')
    output_file.write('RESOLUTION_X ' + str(RESOLUTION) + '\n')
    output_file.write('RESOLUTION_Y ' + str(RESOLUTION) + '\n')
    output_file.write('SPACING "C"\n')
    output_file.write('DEFAULT_CHAR 32\n')
    output_file.write('AVERAGE_WIDTH ' + str(AVERAGE_WIDTH) + '\n')
    output_file.write('CHARSET_REGISTRY "' + CHARSET_REGISTRY + '"\n')
    output_file.write('CHARSET_ENCODING "' + CHARSET_ENCODING + '"\n')
    output_file.write('FOUNDRY "' + common.FONT_AUTHOR + '"\n')
    output_file.write('COPYRIGHT "' + common.FONT_COPYRIGHT + '"\n')
    output_file.write('ENDPROPERTIES\n')

    output_file.write('CHARS ' + str(glyph_count) + '\n')

    data = indexed_image.load()
    icon_mapping = common.FONT_ICON_MAPPINGS.get(subsheet.name)

    for glyph_index in range(glyph_count):
        char_code = icon_mapping[glyph_index] if icon_mapping is not None else glyph_index + 32
        output_file.write('STARTCHAR char' + str(char_code) + '\n')
        output_file.write('ENCODING ' + str(char_code) + '\n')
        output_file.write('SWIDTH ' + str(glyph_width * POINT_SIZE) + ' 0\n')
        output_file.write('DWIDTH ' + str(glyph_width) + ' 0\n')
        output_file.write('BBX {} {} {} {}\n'.format(glyph_width, glyph_height, 0, -descent))
        output_file.write('BITMAP\n')

        glyph_x = glyph_index % glyph_columns * glyph_width
        glyph_y = glyph_index // glyph_columns * glyph_height
        #print('glyph_index ' + str(glyph_index) + ' ' + str(glyph_x) + ' ' + str(glyph_y))

        for j in range(glyph_height):
            c = 0
            for i in range(glyph_width):
                c = (c << 1) | (COLOR_MAPPING_1BPP[data[glyph_x + i, glyph_y + j]] & 1)

            shift = glyph_width % 8
            c <<= shift
            padding = (glyph_width + 7) // 8 * 2 # pad to nearest hex-encoded byte length

            output_file.write('{:0{padding}X}\n'.format(c, padding=padding))
        output_file.write('ENDCHAR\n')

    output_file.write('ENDFONT\n')
    pass

# TODO: for CHR, pack better for tiny fonts that do not take up a full row. pad.
# TODO: for CHR, better arrangement of glyphs, so all 8x8 tile chunks for a glyph are adjacent to each other in memory order.
#       (right now it splits it up by image rows/columns, rather than grouped together by glyph)

def write_chr_1bpp(output_file, subsheet, variant, rgba_image, indexed_image):
    w, h = indexed_image.size
    data = indexed_image.load()
    buffer = bytearray()
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            for j in range(8):
                # Write bits of this row.
                c = 0
                for i in range(8):
                    c = (c << 1) | (COLOR_MAPPING_1BPP[data[x + i, y + j]] & 1)
                buffer.append(c)
    output_file.write(buffer)

def write_chr_nes(output_file, subsheet, variant, rgba_image, indexed_image):
    w, h = indexed_image.size
    data = indexed_image.load()    
    buffer = bytearray()
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            # Copy low bits of each 8x8 chunk into the first 8x8 plane.
            for j in range(8):
                c = 0
                for i in range(8):
                    c = (c << 1) | (COLOR_MAPPING_3C[data[x + i, y + j]] & 1)
                buffer.append(c)
            # Copy high bits of each chunk into the second 8x8 plane.
            for j in range(8):
                c = 0
                for i in range(8):
                    c = (c << 1) | ((COLOR_MAPPING_3C[data[x + i, y + j]] >> 1) & 1)
                buffer.append(c)
    output_file.write(buffer)

def write_chr_gb(output_file, subsheet, variant, rgba_image, indexed_image):
    w, h = indexed_image.size
    data = indexed_image.load()
    buffer = bytearray()
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            for j in range(8):
                # Write low bits of this row.
                c = 0
                for i in range(8):
                    c = (c << 1) | (COLOR_MAPPING_3C[data[x + i, y + j]] & 1)
                buffer.append(c)
                
                # Write high bits of this row.
                c = 0
                for i in range(8):
                    c = (c << 1) | ((COLOR_MAPPING_3C[data[x + i, y + j]] >> 1) & 1)
                buffer.append(c)
    output_file.write(buffer)

def write_svg(output_file, subsheet, variant, rgba_image, indexed_image):
    SCALE = 4
    w, h = rgba_image.size
    data = rgba_image.load()
    drawing = svgwrite.Drawing(size=(str(w * SCALE) + 'px', str(h * SCALE) + 'px'))

    for x in range(w):
        for y in range(h):
            color = data[(x, y)]

            if color[3] != 0:
                drawing.add(drawing.rect((str(x * SCALE) + 'px', str(y * SCALE) + 'px'), (str(SCALE) + 'px', str(SCALE) + 'px'), fill=svgwrite.rgb(*color[:-1]), shape_rendering='crispEdges'))

    drawing.write(output_file)

def write_png_indexed(output_file, subsheet, variant, rgba_image, indexed_image):
    indexed_image.save(output_file, 'PNG', transparency=0)

def write_png_rgb_magenta(output_file, subsheet, variant, rgba_image, indexed_image):
    temp_image = PIL.Image.new('RGB', rgba_image.size, MAGENTA)
    temp_image.paste(rgba_image, (0, 0), rgba_image)
    temp_image.save(output_file, 'PNG')

def write_png_rgba(output_file, subsheet, variant, rgba_image, indexed_image):
    rgba_image.save(output_file, 'PNG')

def write_png_rgba_love2d(output_file, subsheet, variant, rgba_image, indexed_image):
    glyph_width, glyph_height = subsheet.glyph_size
    glyph_columns = rgba_image.width // glyph_width
    glyph_rows = rgba_image.height // glyph_height
    glyph_count = glyph_columns * glyph_rows

    temp_image = PIL.Image.new('RGBA', (glyph_count * glyph_width + 1 + glyph_count, glyph_height), TRANSPARENT)
    temp_data = temp_image.load()

    for y in range(glyph_height):
        temp_data[(0, y)] = (0, 255, 255, 255)

    for glyph_index in range(glyph_count):
        glyph_x = (glyph_index % glyph_columns) * glyph_width
        glyph_y = (glyph_index // glyph_columns) * glyph_height
        crop_area = (glyph_x, glyph_y, glyph_x + glyph_width, glyph_y + glyph_height)

        glyph_rgba_image = rgba_image.crop(crop_area)

        dest_x = glyph_index * glyph_width + 1 + glyph_index
        temp_image.paste(glyph_rgba_image, (dest_x, 0), glyph_rgba_image)

        for dest_y in range(glyph_height):
            temp_data[(dest_x + glyph_width, dest_y)] = (0, 255, 255, 255)

    temp_image.save(output_file, 'PNG')

def write_gif(output_file, subsheet, variant, rgba_image, indexed_image):
    indexed_image.save(output_file, 'GIF', transparency=0)

def write_bmp_indexed(output_file, subsheet, variant, rgba_image, indexed_image):
    indexed_image.save(output_file, 'BMP')

def write_bmp_rgb_magenta(output_file, subsheet, variant, rgba_image, indexed_image):
    temp_image = PIL.Image.new('RGB', rgba_image.size, MAGENTA)
    temp_image.paste(rgba_image, (0, 0), rgba_image)
    temp_image.save(output_file, 'BMP')

FONT_FORMATS = {
    'bdf': FontFormat('bdf', '', 'text', write_bdf, ['1bpp']),
    'chr_1bpp': FontFormat('chr', '1bpp', 'binary', write_chr_1bpp, ['1bpp']),
    'chr_nes': FontFormat('chr', 'nes', 'binary', write_chr_nes, ['3c']),
    'chr_gb': FontFormat('chr', 'gb', 'binary', write_chr_gb, ['3c']),
    'svg_packed': FontFormat('svg', '', 'text', write_svg, []),
    'svg_individual': FontFormat('svg', '', 'text_folder', write_svg, []),
    'png_indexed': FontFormat('png', 'idx', 'binary',write_png_indexed, []),
    'png_rgb_magenta': FontFormat('png', 'rgb_magenta', 'binary', write_png_rgb_magenta, []),
    'png_rgba': FontFormat('png', 'rgba', 'binary', write_png_rgba, []),
    'png_rgba_love2d': FontFormat('png', 'rgba_love', 'binary', write_png_rgba_love2d, []),
    'png_rgba_individual': FontFormat('png', '', 'binary_folder', write_png_rgba, []),
    'gif': FontFormat('gif', '', 'binary', write_gif, []),
    'gif_individual': FontFormat('gif', '', 'binary_folder', write_gif, []),
    'bmp_indexed': FontFormat('bmp', 'idx', 'binary', write_bmp_indexed, []),
    'bmp_rgb_magenta': FontFormat('bmp', 'rgb_magenta', 'binary', write_bmp_rgb_magenta, []),
}



FONT_COMBINED_VARIANTS = ['plain', 'hshadow', 'vshadow', 'hvshadow', 'hshadow_outline', 'vshadow_outline', 'hvshadow_outline']
FONT_COMBINED_FORMATS = ['png_indexed', 'png_rgb_magenta', 'png_rgba', 'gif']

def rect_to_flat_coord_pair(region):
    return (region[0], region[1], region[0] + region[2], region[1] + region[3])

def rect_get_size(region):
    return (region[2], region[3])

def generate_indexed_image(source_image):
    palette = PALETTE_DEFAULTS[:]
    source_image = replace_color(source_image.copy(), TRANSPARENT, MAGENTA)
    source_data = source_image.load()
    w, h = source_image.size

    result_image = PIL.Image.new('P', source_image.size, 0)
    result_data = result_image.load()

    for x in range(w):
        for y in range(h):
            color = source_data[(x, y)]
            try:
                index = palette.index(color)
            except ValueError:
                index = len(palette)
                palette.append(color)

            result_data[(x, y)] = index

    palette = [color[:-1] for color in palette]
    palette_data = list(sum(palette, ()))
    result_image.putpalette(palette_data)

    return result_image

def get_sheet_filename(sheet_name, variant_suffix, format_suffix, format_extension):
    return common.FONT_PREFIX \
        + ('_' + sheet_name if sheet_name else '') \
        + ('_' + variant_suffix if variant_suffix else '') \
        + ('_' + format_suffix if format_suffix else '') \
        + '.' + format_extension

def generate_sheets(force_replace):
    if force_replace:
        try:
            shutil.rmtree(common.FONT_OUTPUT_FOLDER)
        except FileNotFoundError:
            pass

    folders_to_create = [common.FONT_OUTPUT_FOLDER] \
        + [os.path.join(common.FONT_OUTPUT_FOLDER, format_name)
            for format_name, format in FONT_FORMATS.items()
            if 'unsupported' not in format.validators]

    if os.path.exists(common.FONT_OUTPUT_FOLDER):
        print('Path "' + common.FONT_OUTPUT_FOLDER + '" already exists.')
        return

    for folder in folders_to_create:
        create_directory_verbose(folder)

    print('Opening font source "' + common.FONT_SOURCE_FILENAME + '" ...')
    full_source_image = replace_color(PIL.Image.open(common.FONT_SOURCE_FILENAME).convert('RGBA'), MAGENTA, TRANSPARENT)

    print('Generating subsheets...')

    for subsheet_name, subsheet in FONT_SUBSHEETS.items():
        print('Processing "' + subsheet_name + '" subsheet...')

        subsheet_source_crop = full_source_image.crop(rect_to_flat_coord_pair(subsheet.region))

        subsheet_source_image = PIL.Image.new('RGBA', rect_get_size(subsheet.region), TRANSPARENT)
        subsheet_source_image.paste(subsheet_source_crop)

        for variant_name in subsheet.variants:
            variant = FONT_VARIANTS[variant_name]

            print('Generating "' + subsheet_name + '" variant "' + variant_name + '"...')

            rgba_image = variant.generate_func(subsheet_source_image, subsheet)

            if rgba_image is not None:
                indexed_image = generate_indexed_image(rgba_image)

                for format_name, format in FONT_FORMATS.items():
                    reject = False

                    for validator_name in format.validators:
                        validator = FONT_VALIDATORS[validator_name]
                        if not validator.validate_func(variant, rgba_image, indexed_image):
                            reject = True

                    if reject:
                        continue

                    output_path = os.path.join(common.FONT_OUTPUT_FOLDER, format_name, get_sheet_filename(subsheet_name, variant.suffix, format.suffix, format.extension))
                    format_kind = FONT_FORMAT_KINDS.get(format.kind)
                    if format_kind is None:
                        raise Exception('Unhandled format kind "' + format.kind + '" used by format "' + format_name + '"')

                    format_kind.save_func(subsheet, variant, format, output_path, rgba_image, indexed_image)

                    print('    OK.')

                print('VARIANT "' + variant_name + '" COMPLETE.')
            else:
                print('VARIANT NOT IMPLEMENTED (IGNORE).')

        print('SUBSHEET "' + subsheet_name + '" COMPLETE.')

    print('')
    print('Generating combined images...')
    print('')

    plain_variant = FONT_VARIANTS['plain']

    for variant_name in FONT_COMBINED_VARIANTS:
        variant = FONT_VARIANTS[variant_name]

        for format_name in FONT_COMBINED_FORMATS:
            format = FONT_FORMATS[format_name]

            output_image = None
            needs_palette_reduce = False

            print('Generating combined texture for ("' + variant_name + '", "' + format_name + '")...')

            for subsheet_name, subsheet in FONT_SUBSHEETS.items():
                subsheet_image = None

                if subsheet_image is None:
                    try:
                        subsheet_path = os.path.join(common.FONT_OUTPUT_FOLDER, format_name, get_sheet_filename(subsheet_name, variant.suffix, format.suffix, format.extension))
                        print('  - Trying ' + subsheet_path)
                        subsheet_image = PIL.Image.open(subsheet_path)
                    except FileNotFoundError:
                        pass

                if subsheet_image is None:
                    try:
                        subsheet_path = os.path.join(common.FONT_OUTPUT_FOLDER, format_name, get_sheet_filename(subsheet_name, plain_variant.suffix, format.suffix, format.extension))
                        print('  - Trying ' + subsheet_path)
                        subsheet_image = PIL.Image.open(subsheet_path)
                    except FileNotFoundError:
                        pass

                if subsheet_image is None:
                    print('  - Failed to open subsheet image for (variant = "' + variant_name + '", format = "' + format_name + '", subsheet_name = "' + subsheet_name + '")')
                    continue

                if subsheet_image is not None and output_image is None:
                    if subsheet_image.mode == 'P':
                        needs_palette_reduce = True
                        output_image = PIL.Image.new('RGBA', full_source_image.size, TRANSPARENT)
                    else:
                        output_image = PIL.Image.new(subsheet_image.mode, full_source_image.size,
                            {
                                'RGB': MAGENTA,
                                'RGBA': TRANSPARENT,
                            }.get('RGBA', 0))

                position = (subsheet.region[0], subsheet.region[1])

                print('    FOUND. Pasting at position = ' + repr(position) + '.')

                output_image.paste(subsheet_image, position)

            output_path = os.path.join(common.FONT_OUTPUT_FOLDER, format_name, get_sheet_filename('complete', variant.suffix, format.suffix, format.extension))

            print('  - Writing "' + output_path + '"...')

            if needs_palette_reduce:
                indexed_image = generate_indexed_image(output_image)
                indexed_image.save(output_path)
            else:
                output_image.save(output_path)

            print('    OK.')

        print('VARIANT ' + variant_name + ' COMPLETE.')

    print('')
    print('GENERATION COMPLETE.')

if __name__ == '__main__':
    import sys    

    force_replace = False

    for arg in sys.argv[1:]:
        if arg == '--force-replace':
            force_replace = True
        else:
            raise Exception('Unrecognized argument "' + arg + "'")

    generate_sheets(force_replace)