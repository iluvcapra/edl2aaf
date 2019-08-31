from optparse import OptionParser, OptionGroup
from edl2aaf import EDLAAFConverter
from pycmx import parse_cmx
from sys import stdin

def do_command():
    arg_parser = OptionParser()
    arg_parser.usage = 'usage: %prog [options] INFILE.EDL [...]'
    arg_parser.version = '0.1'
    arg_parser.description = 'Read a CMX 3600-style EDL and convert it into an AAF.'
    common = OptionGroup(arg_parser, title='Common Options')

    common.add_option('-s', '--source-list', dest='source_list', metavar='PATH_LIST', action='append',
                      help='A list of source Broadcast-WAV files, one file path per line.')
    common.add_option('-n', '--name', dest='sequence_name', metavar='NAME',
                      help='The name for the composition to create. By default, this will be the title of the EDL.')
    common.add_option('--fs', dest='frame_rate', metavar='FPS', default=24,
                      help='The integer frame rate of the EDL. The tracks of the output composition will have ' +
                           'this rate as well. Default is 24.')
    common.add_option('-L', dest='log_file', metavar='LOGFILE',
                      help='Log file. A log file is always generated. By default, this is the name of the output '
                           'file with \'.log\' appended.')
    arg_parser.add_option_group(common)

    unimplemented = OptionGroup(arg_parser, title="Experimental Options (probably don't work)")
    unimplemented.add_option('-b', '--blanks', help='Create and embed dummy silent audio media for each unmatched EDL '
                                                    'event.')
    arg_parser.add_option_group(unimplemented)

    arg_parser.description = "The command attempts to merge a CMX EDL with a list of source Broadcast-WAV files and " \
                             "writes the result to an AAF file as an AAF composition. At this time, only audio " \
                             "tracks are translated."

    options, edl_files = arg_parser.parse_args()

    print(options)
    # source_paths = []
    # if options.source_list is not None:
    #     for file in options.source_list:
    #         with open(file,'r') as f:
    #             for line in f.readline():
    #                 source_paths.append(line)
    #
    # for edl_file in edl_files:
    #     with open(source, 'r') as f:
    #         for line in f.readline():
    #             source_paths.append(line)
    #
    #
    #     edl = parse_cmx.parse_cmx3600(edl_file)







