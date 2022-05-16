#!/usr/bin/env python
import subprocess
import re

def run_script(path, args):
    with open(path) as f:
        line = f.readline()
        print(line)
        match = re.match('#!/usr/bin/env[ ]*(-[^ ]*[ ]*)?(.*)$', line)
        command = match.group(2)
    
    print(command + ' ' + path + ' ' + args)
    result = subprocess.run(command + ' ' + path + ' ' + args)
    result.check_returncode()

if __name__ == '__main__':
    import sys 

    force_replace = False

    for arg in sys.argv[1:]:
        if arg == '--force-replace':
            force_replace = True
        else:
            raise Exception('Unrecognized argument "' + arg + "'")

    print('GENERATING FONT SHEETS...')
    print('')

    run_script('generate_sheets.py',
        ('--force-replace' if force_replace else ''))    

    print('')
    print('USING FONTFORGE TO CONVERT TO TTF...')
    print('')

    run_script('fontforge_convert_to_ttf.py',
        ('--force-replace' if force_replace else ''))    

    print('')
    print('DONE ALL BUILD STEPS!')
