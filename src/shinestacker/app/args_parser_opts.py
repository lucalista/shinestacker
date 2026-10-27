# pylint: disable=C0114, C0116
import sys
from shinestacker.config.defaults import DEFAULTS
from shinestacker.config.gui_constants import gui_constants


def add_project_arguments(parser):
    parser.add_argument('-x', '--expert', action='store_true', help='''
make expert options visible.
''')
    parser.add_argument('-n', '--no-new-project', dest='new_project',
                        action='store_false', default=True, help='''
do not open new project dialog at startup (default: open).
''')
    parser.add_argument('-p', '--path', nargs='?', help='''
input folder path for new project.
''')
    parser.add_argument('-s', '--start', action='store_true', help='''
Automatically run scheduled jobs at startup.
''')
    parser.add_argument('-b', '--bunches', action='store_true', help='''
with --path and --start: add a focus stack bunch step to the new project
(stack groups of frames first, then stack the resulting bunches).
''')
    parser.add_argument('--bunch-frames', type=int, default=None, help='''
frames per bunch (implies --bunches).
''')
    parser.add_argument('--bunch-overlap', type=int, default=None, help='''
overlap between bunches (implies --bunches).
''')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-e', '--enable-auto-retouch', action='store_true',
                       dest='auto_retouch', help='''
Enable retouch after run at startup''')
    group.add_argument('-d', '--disable-auto-retouch', action='store_false',
                       dest='auto_retouch', help='''
Disable retouch after run at startup''')
    parser.set_defaults(auto_retouch=None)


def get_bunch_params(args):
    if not (args.bunches or args.bunch_frames is not None or args.bunch_overlap is not None):
        return None
    defaults = DEFAULTS['focus_stack_bunch_params']
    params = {
        'frames': defaults['frames'] if args.bunch_frames is None else args.bunch_frames,
        'overlap': defaults['overlap'] if args.bunch_overlap is None else args.bunch_overlap
    }
    for key, limits in (('frames', gui_constants.NEW_PROJECT_BUNCH_FRAMES),
                        ('overlap', gui_constants.NEW_PROJECT_BUNCH_OVERLAP)):
        if not limits['min'] <= params[key] <= limits['max']:
            print(f"--bunch-{key} must be between {limits['min']} and {limits['max']}",
                  file=sys.stderr)
            sys.exit(1)
    if params['overlap'] >= params['frames']:
        print("--bunch-overlap must be smaller than --bunch-frames", file=sys.stderr)
        sys.exit(1)
    return params


def add_retouch_arguments(parser):
    parser.add_argument('-i', '--image-folder', nargs='?', help='''
open all images in the specified folder in the retouch window.
Multiple folder paths can be specified separated by ';'.
''')
    view_group = parser.add_mutually_exclusive_group()
    view_group.add_argument('-v1', '--view-overlaid', action='store_true', help='''
set overlaid view.
''')
    view_group.add_argument('-v2', '--view-side-by-side', action='store_true', help='''
set side-by-side view.
''')
    view_group.add_argument('-v3', '--view-top-bottom', action='store_true', help='''
set top-bottom view.
''')


def extract_positional_filename():
    positional_filename = None
    filtered_args = []
    value_flags = {'-p', '--path', '-i', '--image-folder', '-f', '--filename',
                   '--bunch-frames', '--bunch-overlap'}
    consume_next = False
    for arg in sys.argv[1:]:
        if consume_next:
            filtered_args.append(arg)
            consume_next = False
        elif arg in value_flags:
            filtered_args.append(arg)
            consume_next = True
        elif not arg.startswith('-') and not positional_filename:
            positional_filename = arg
        else:
            filtered_args.append(arg)
    return positional_filename, filtered_args


def setup_filename_argument(parser):
    parser.add_argument('-f', '--filename', nargs='?', const=True, help='''
project file or image file(s) to open.
Image files are opened in the retouch window.
Multiple file paths can be specified separated by ';'.
''')


def process_filename_argument(args, positional_filename):
    filename = getattr(args, 'filename', None)
    if positional_filename and not filename:
        filename = positional_filename
    if filename is True:
        if positional_filename:
            filename = positional_filename
        else:
            print("Error: -f flag used but no filename provided", file=sys.stderr)
            sys.exit(1)
    return filename
