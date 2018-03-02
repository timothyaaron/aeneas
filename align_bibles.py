#!/usr/bin/env python
# coding=utf-8
from __future__ import print_function
import errno
import os
import re
import shutil
import xlrd

ROOT_DIR = "../samples/Bengali WTC"
AUDIO_DIR = os.path.join(ROOT_DIR, 'ChapterVOX (Original)')
FINAL_AUDIO_DIR = os.path.join(ROOT_DIR, 'ChapterVOX (Edited)')
TIMING_DIR = os.path.join(ROOT_DIR, 'QINFO')
SCRIPT_DIR = os.path.join(ROOT_DIR, 'Infofiles')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'alignments')
SCRIPT_START_ROW = 56


def _value(v, t):
    try:
        return t(v)
    except:
        return v


def _clear_directory(dir):
    try:
        shutil.rmtree(dir)
    except:
        pass

    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def _load_script(file_name):
    def _is_valid(this_verse, next_verses):
        def _clean_break(next_verses):
            if not next_verses:
                return True

            next_line = next_verses[0]
            continuation = not next_line['verse_starts'] and not next_line['starts_new']
            clean_start = next_line['verse_starts'] and next_line['starts_new']

            if continuation:
                return _clean_break(next_verses[1:])

            elif clean_start or not next_verses[1:]:
                return True

            return False

        single_verse = this_verse['starts_new'] and len(this_verse['verse_starts']) <= 1
        return bool(single_verse and _clean_break(next_verses))

    file_path = os.path.join(SCRIPT_DIR, file_name)
    workbook = xlrd.open_workbook(file_path)
    sheet = workbook.sheet_by_index(0)

    script = {}
    for rx in range(SCRIPT_START_ROW, sheet.nrows):
        row = sheet.row(rx)
        book = _value(row[1].value, str)
        chapter = _value(row[2].value, int)
        verse = _value(row[3].value, int)
        # order = _value(row[8].value, int)  # already ordered
        text = _value(row[10].value, str)

        if book not in script:
            script[book] = {}

        verse_starts = [m.group(1) for m in re.finditer('{([0-9]+)}', text) if m]
        verse_meta = {
            'num': verse,
            'starts_new': verse == '<<' or text.startswith(' {{{}}}'.format(verse)),
            'verse_starts': ['<<'] if verse == '<<' else verse_starts
        }
        if chapter in script[book]:
            script[book][chapter].append(verse_meta)
        else:
            script[book][chapter] = [verse_meta]

    # import pdb; pdb.set_trace()
    for book, chapters in script.iteritems():
        for chapter, verses in chapters.iteritems():
            for i, verse_meta in enumerate(verses):
                # if book == 'MAT' and chapter == 1 and verse_meta['verse_starts'] == ['20']:
                #     import pdb; pdb.set_trace()
                verse_num, starts_new, verse_starts = verse_meta
                verse_meta['is_valid'] = _is_valid(verse_meta, verses[i + 1:])

    # for book, chapters in script.iteritems():
    #     for num, chapter in chapters.iteritems():
    #         for i, [verse, (starts, verses)] in enumerate(chapter):
    #             is_contained = bool(starts and len(verses) == 1)
    #             chapter[i].append(is_contained)

    # import pdb; pdb.set_trace()

    return script


def _load_timings(file_path):
    with open(file_path, 'r') as file:
        lines = [l.strip() for l in file.readlines()]

    sample_rate = float(lines[2])
    starting_times = [int(t)/sample_rate for t in lines[3::5]]
    # length_times = [int(t)/sample_rate for t in lines[4::5]]

    return starting_times


def _build_synt_timings(final_audio_file, timings, script):
    book, chapter = final_audio_file[15:21].split('_')
    output = []

    csv_path = os.path.join(OUTPUT_DIR, 'timings.{}.{}.csv'.format(book, chapter))
    with open(csv_path, 'a') as csv_file:
        # import pdb; pdb.set_trace()

        # loop each script item, only append the timing if the item hasn't been seen before
        for i, meta in enumerate(script[book][int(chapter)]):

            verses_output = []

            # if not seen before
            # import pdb; pdb.set_trace()
            for verse_number in meta['verse_starts']:
                if verse_number not in verses_output:
                    final_audio_path = os.path.join(AUDIO_DIR, final_audio_file)
                    description = 'error' if not meta['is_valid'] else final_audio_path
                    output.append('{},{},{}\n'.format(verse_number, timings[i], description))
                    verses_output.append(verse_number)

        csv_file.writelines(output)

        # import pprint
        # pp = pprint.PrettyPrinter(indent=2)
        # pp.pprint(output)

    return csv_path


if __name__ == '__main__':
    print('Aligning', ROOT_DIR)

    print('Clearing previous output...')
    _clear_directory(OUTPUT_DIR)

    print('Loading script...')
    script = _load_script('CORE_Scr_1067r1__1ENG__25_Spkr__Bengali_N2_BNG_WTC.xls')

    print('Building chapter times...')
    final_audio_files = os.listdir(FINAL_AUDIO_DIR)
    for final_audio_file in sorted(final_audio_files)[:5]:
        print(final_audio_file)
        timing_path = os.path.join(TIMING_DIR, '{}.clt'.format(final_audio_file[:-4]))
        timings = _load_timings(timing_path)  # start of each script line (which has dupes)

        synt_timing = _build_synt_timings(final_audio_file, timings, script)

        # build csv and save
        # call `python -m aeneas.tools.execute_task [final_audio] [csv] [options] [output]`
