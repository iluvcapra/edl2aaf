from optparse import OptionParser


def do_command(argv):
    arg_parser = OptionParser()
    arg_parser.add_option('-s', '--source-list', dest='source_list')
    arg_parser.add_option('-t', '--sequence-name', dest='sequence_name')
    arg_parser.add_option('--fs', dest='frame_rate')
    arg_parser.add_option('-o', '--output', dest='output_file')

    options, rest = arg_parser.parse_args(args=argv)