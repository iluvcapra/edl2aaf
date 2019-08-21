#!/usr/bin/env python3
from typing import Any, Tuple, Iterator

import pycmx
from timecode import Timecode
import aaf2
from wavinfo import WavInfoReader
import subprocess
import json
import os.path
from optparse import OptionParser
from collections import namedtuple

# FFPROBE_EXEC: str = 'ffprobe'
#
#
# def probe(path, show_packets=False):
#     cmd = [FFPROBE_EXEC, '-of', 'json', '-show_format', '-show_streams', path]
#
#     if show_packets:
#         cmd.extend(['-show_packets', ])
#
#     p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#
#     stdout, stderr = p.communicate()
#
#     if p.returncode != 0:
#         raise subprocess.CalledProcessError(p.returncode, subprocess.list2cmdline(cmd), stderr)
#
#     return json.loads(stdout.decode('utf8'))
#
#
# Clip = namedtuple("Clip", ['source_file', 'source_start', 'record_start', 'record_finish', 'original_edl_event','lane'])
#
#
# class EDLConverter:
#     def __init__(self, edl_path, edl_frame_rate, source_files, sequence_name, output_file_name):
#         self.source_files = source_files
#         with open(edl_path) as f:
#             self.edit_list = pycmx.parse_cmx3600(f)
#
#         self.sequence_name = sequence_name or self.edit_list.title
#         self.frame_rate = edl_frame_rate
#         self.source_files = source_files
#         self.output_file_name = output_file_name
#
#         self.ffprobe_cache = {}
#         self.wavinfo_cache = {}
#
#     def _convert_edit_times_to_fs(self, edit, fs):
#         source_start = Timecode(framerate=self.frame_rate, start_timecode=edit.source_in)
#         source_finish = Timecode(framerate=self.frame_rate, start_timecode=edit.source_out)
#         record_start = Timecode(framerate=self.frame_rate, start_timecode=edit.record_in)
#         record_finish = Timecode(framerate=self.frame_rate, start_timecode=edit.record_out)
#         source_fs_start = source_start.frame_number * fs / self.frame_rate
#         source_fs_finish = source_finish.frame_number * fs / self.frame_rate
#         record_fs_start = record_start.frame_number * fs / self.frame_rate
#         record_fs_finish = record_finish.frame_number * fs / self.frame_rate
#         return source_fs_start, source_fs_finish, record_fs_start, record_fs_finish
#
#     def _is_source_path_valid_for_time_range(self, edit, info):
#         fs = info.fmt.sample_rate
#         wav_start_fs = info.bext.time_reference
#         wav_finish_fs = wav_start_fs + info.data.frame_count
#         source_fs_start, source_fs_finish, _, _ = self._convert_edit_times_to_fs(edit, fs)
#         return wav_start_fs <= source_fs_start <= wav_finish_fs and wav_start_fs <= source_fs_finish <= wav_finish_fs
#
#     def _is_source_path_valid_for_edit(self, edit, path, info):
#         if not self._is_source_path_valid_for_time_range(edit, info):
#             return False
#
#         if edit.source_file == os.path.basename(path):
#             return True
#         elif edit.source == os.path.basename(path):
#             return True
#         elif edit.source == info.ixml.tape:
#             return True
#         else:
#             return False
#
#     def _info_for_path(self, path):
#         if path not in self.wavinfo_cache:
#             self.wavinfo_cache[path] = WavInfoReader(path)
#         return self.wavinfo_cache[path]
#
#     def _ffprobe_metadata_for_path(self, path):
#         if path not in self.ffprobe_cache:
#             self.ffprobe_cache[path] = probe(path)
#         return self.ffprobe_cache[path]
#
#     def default_lane_name_for_path(self, path):
#         """
#         Recommend a name for the lane this path should be on.
#         :param path:
#         :return:
#         """
#         info = self._info_for_path(path)
#         for track in info.ixml.track_list:
#             return track.channel_index
#
#         return ''
#
#     def source_paths_for_edit(self, edit):
#         """
#         Find files that are the correct source for this Edit
#         :param edit: a pycmx.Edit
#         :return: a list of os.pathlike things
#         """
#         sources_and_info = [(path, self._info_for_path(path)) for path in self.source_files]
#
#         def filterproc(path, info):
#             return self._is_source_path_valid_for_edit(edit, path, info)
#
#         file_set = filter(filterproc, sources_and_info)
#
#         return file_set
#
#     def clips_for_edit_source(self, edit):
#         matched_files = self.source_paths_for_edit(edit)
#         for matched_file in matched_files:
#             info_for_path: WavInfoReader = self._info_for_path(matched_file)
#             fs = info_for_path.fmt.sample_rate
#             file_timestamp_fs = info_for_path.bext.time_reference
#             src_start_fs, _, rec_start_fs, rec_finish_fs = self._convert_edit_times_to_fs(edit, fs)
#             clip_start_fs = src_start_fs - file_timestamp_fs
#
#             yield Clip(source_file=matched_file, source_start=clip_start_fs,
#                        record_start=rec_start_fs, record_finish=rec_finish_fs,
#                        original_edl_event=edit)
#
#     def clips(self):
#         """
#         All of the clips in the edl as `Clip`s
#         :return: an Iterator
#         """
#         for event in self.edit_list.events:
#             for edit in event.edits:
#                 if edit.channels.audio:
#                     for clip in self.clips_for_edit_source(edit):
#                         yield clip
#
#     def used_files(self):
#         """
#         All files that will be used in reassembling the EDL
#         :return: an Iterator
#         """
#         used_list = set()
#         for clip in self.clips():
#             if clip.source_file not in used_list:
#                 used_list.add(clip.source_file)
#                 yield clip.source_file
#
#     def convert(self):
#         clips = list(self.clips())
#         assert len(clips) > 0, 'No linkable EDL events were found'
#
#         source_paths = list(self.used_files())
#         assert len(source_paths) > 0, 'No linkable source files were found'
#
#         source_map = {}
#         with aaf2.open(path=self.output_file_name, mode='wb') as f:
#             for source_path in source_paths:
#                 metadata = self._ffprobe_metadata_for_path(source_path)
#                 master_mob, _, _ = f.content.create_ama_link(source_path, metadata)
#                 source_map[source_path] = master_mob.mob_id
#
#             composition_mob: aaf2.mobs.CompositionMob = f.create.CompositionMob(name=self.sequence_name)
#             f.content.append(composition_mob)
#
#             for channel in self.edit_list.channels:
#                 lane_map = {}
#                 slot_base_name = f"A{channel}"
#                 for clip in clips:
#                     if channel in clip.original_edl_event.channels:
#                         source_info = self._info_for_path(clip.source_file)
#                         if source_info.ixml.channel_index is not None:
#                             lane_name = slot_base_name + '_' + source_info.ixml.channel_index
#                             slot = None
#                             if lane_name not in lane_map:
#                                 slot = composition_mob.create_sound_slot(edit_rate=self.frame_rate)
#                             else:
#                                 slot = composition_mob.slot_at(lane_map[lane_name])


arg_parser = OptionParser()
arg_parser.add_option('-s', '--source-list', dest='source_list')
arg_parser.add_option('-t', '--sequence-name', dest='sequence_name')
arg_parser.add_option('--fs', dest='frame_rate')
arg_parser.add_option('-o', '--output', dest='output_file')

options, rest = arg_parser.parse_args()
