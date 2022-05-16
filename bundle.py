#!/usr/bin/env python
import common
import zipfile
import glob

def make_zip():
    print('Scanning for files...')
    files = set(glob.glob('*') + glob.glob('**/*', recursive=True))
    excluded = set(glob.glob('.*'))

    print('Excluding .gitignore...')
    with open('.gitignore') as gitignore:
        for line in gitignore:
            line = line.strip()
            excluded = excluded.union(glob.glob(line))
            if '*' in line:
                excluded = excluded.union(glob.glob('**/' + line, recursive=True))

    zipname = common.FONT_NAME + '_font.zip'

    files = files.difference(excluded)
    files = files.union(['.gitignore'])
    files = files.difference([zipname])

    print('Creating zip...')

    with zipfile.ZipFile(zipname, 'w') as zf:
        for file in files:
            print(file + '...')
            zf.write(file)
            print('...OK.')
            
    print('')
    print('Saved to "' + zipname + '"!')
    print('')
    print('DONE.')


if __name__ == '__main__':
    import sys 

    make_zip()