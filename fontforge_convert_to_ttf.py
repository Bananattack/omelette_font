#!/usr/bin/env -S fontforge -script
import fontforge
import glob
import os
import os.path
import sys
import common
import collections
import shutil
import re

FONT_OUTPUT_TTF_FOLDER = 'assets/ttf'
FONT_INPUT_SVG_FOLDER = 'assets/svg_individual'
FONT_INPUT_BDF_FOLDER = 'assets/bdf'
FONT_FAMILY_HUMAN_NAME = 'Omelette'
FONT_PREFIX = 'om'
FONT_VERSION = 'v1'
FONT_PIXEL_SCALE = 4

EXCLUDED_SUBSHEETS = {'buttons'}
INCLUDED_VARIANTS = {'plain', 'silhouette', 'shadow_outline', 'hshadow_outline', 'vshadow_outline'}
EXCLUDED_ICON_VARIANTS = {'plain'}

SubsheetMetricInfo = collections.namedtuple('SubsheetMetricInfo', ['width', 'height', 'descent'])

SUBSHEET_METRIC_INFO = {
    'tiny': SubsheetMetricInfo(4, 4, 1),
    'small': SubsheetMetricInfo(4, 8, 1),
    'thin': SubsheetMetricInfo(8, 8, 1),
    'thick': SubsheetMetricInfo(8, 8, 1),
    'tall': SubsheetMetricInfo(8, 16, 2),
    'large': SubsheetMetricInfo(16, 16, 2),
    'window': SubsheetMetricInfo(8, 8, 1),
    'buttons': SubsheetMetricInfo(8, 8, 1),
    'icons': SubsheetMetricInfo(8, 8, 1),
}

GLYPH_INDEX_UPPERCASE_LETTERS = 0
GLYPH_COUNT_UPPERCASE_LETTERS = 26
GLYPH_INDEX_LOWERCASE_LETTERS = 26
GLYPH_COUNT_LOWERCASE_LETTERS = 26
GLYPH_INDEX_DIGITS = 52
GLYPH_COUNT_DIGITS = 10
GLYPH_INDEX_SPECIALS = 52

def convert_svg_to_ttf(force_replace):
    if force_replace:
        try:
            shutil.rmtree(FONT_OUTPUT_TTF_FOLDER)
        except FileNotFoundError:
            pass

    print('Creating directory "' + FONT_OUTPUT_TTF_FOLDER + '"...')
    try:
        os.makedirs(FONT_OUTPUT_TTF_FOLDER)
    except FileExistsError:
        if os.path.exists(FONT_OUTPUT_TTF_FOLDER):
            print('Path "' + FONT_OUTPUT_TTF_FOLDER + '" already exists.')
            return
        pass

    input_folders = glob.glob(os.path.join(FONT_INPUT_SVG_FOLDER, '*'))
    print(input_folders)

    for input_folder in input_folders:
        input_folder_basename = input_folder[len(FONT_INPUT_SVG_FOLDER) + 1:]

        print('input_folder_basename ' + input_folder_basename)

        # 1: subsheet name
        # 2: variant name
        subsheet_match = re.match('om_([a-z]+)_([a-z_]+)', input_folder_basename)

        if subsheet_match is None:
            print('no subsheet_match')
            continue

        subsheet_name = subsheet_match.group(1)
        variant_name = subsheet_match.group(2)
        icon_mapping = common.FONT_ICON_MAPPINGS.get(subsheet_name)

        if subsheet_name in EXCLUDED_SUBSHEETS:
            print('excluded subsheet, skipping...')
            continue            

        if variant_name not in INCLUDED_VARIANTS:
            print('not in included variants, skipping...')
            continue

        if icon_mapping is not None and variant_name in EXCLUDED_ICON_VARIANTS:
            print('excluded variant, skipping...')
            continue

        input_svg_filenames = glob.glob(os.path.join(input_folder, '*.svg'))
        print(input_svg_filenames)

        subsheet_human_name = subsheet_name.replace('_', ' ').title()
        variant_human_name = variant_name.replace('_', ' ').title()
        font_human_name = ' '.join([FONT_FAMILY_HUMAN_NAME, subsheet_human_name, variant_human_name])
        font_postscript_name = font_human_name.replace(' ', '-') + '-Regular'
        print('font_human_name ' + font_human_name)
        
        output_ttf_filename = os.path.join(FONT_OUTPUT_TTF_FOLDER, input_folder_basename + '.ttf')
        input_bdf_filename = os.path.join(FONT_INPUT_BDF_FOLDER, input_folder_basename + '.bdf')

        metric_info = SUBSHEET_METRIC_INFO[subsheet_name]

        font = fontforge.font()
        font.appendSFNTName('English (US)', 'Copyright', common.FONT_COPYRIGHT)
        font.appendSFNTName('English (US)', 'Family', font_human_name)
        font.appendSFNTName('English (US)', 'SubFamily', 'Regular')
        font.appendSFNTName('English (US)', 'UniqueID', font_human_name + ' ' + FONT_VERSION)
        font.appendSFNTName('English (US)', 'Fullname', font_human_name)
        font.appendSFNTName('English (US)', 'Version', FONT_VERSION)
        font.appendSFNTName('English (US)', 'PostScriptName', font_postscript_name)
        font.fontname = font_human_name
        font.familyname = font_human_name
        font.fullname = font_human_name
        font.em = metric_info.width * FONT_PIXEL_SCALE
        font.encoding = 'latin1'
        font.ascent = (metric_info.height - metric_info.descent) * FONT_PIXEL_SCALE
        font.descent = metric_info.descent * FONT_PIXEL_SCALE
        font.importBitmaps(input_bdf_filename)
        print(font.bitmapSizes)

        for input_svg_filename in input_svg_filenames:
            input_file_basename = os.path.basename(input_svg_filename)

            print('input_file_basename ' + input_file_basename)

            # 1: character code/glyph index
            # 2: glyph name
            glyph_match = re.match('om_' + subsheet_name + '_' + variant_name + '_([0-9]+)_([a-z0-9_+])', input_file_basename)

            if glyph_match is None:
                print('no glyph_match')
                continue

            glyph_index = int(glyph_match.group(1))
            character_code = icon_mapping[glyph_index] if icon_mapping is not None else glyph_index
            print('glyph_index ' + str(glyph_index))
            print('character_code ' + str(character_code))

            glyph = font.createMappedChar(character_code)

            if icon_mapping is not None or character_code != ord(' '):
                glyph.importOutlines(input_svg_filename, correct_dir=True, scale=False)
                glyph.removeOverlap()
                glyph.round(FONT_PIXEL_SCALE)

            glyph.width = metric_info.width * FONT_PIXEL_SCALE
            glyph.vwidth = metric_info.height * FONT_PIXEL_SCALE

        print('Exporting to "' + output_ttf_filename + '"...')
        font.generate(output_ttf_filename)

if __name__ == '__main__':
    import sys    

    force_replace = False

    for arg in sys.argv[1:]:
        if arg == '--force-replace':
            force_replace = True
        else:
            raise Exception('Unrecognized argument "' + arg + "'")

    convert_svg_to_ttf(force_replace)