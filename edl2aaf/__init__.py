#
#
from typing import Optional, Any, Iterable, Dict, List, Tuple

import aaf2
from wavinfo import WavInfoReader
import pycmx
from timecode import Timecode
from functools import total_ordering
import itertools
import subprocess
import json
import os.path
import re


class DecodedEdit:
    def __init__(self, edit: pycmx.Edit, timecode_rate: int = 24):
        self.source_file = edit.source_file
        self.source_name = edit.source
        self.frame_rate = int(timecode_rate)
        self.source_in = Timecode(framerate=timecode_rate, start_timecode=edit.source_in).frames
        self.source_out = Timecode(framerate=timecode_rate, start_timecode=edit.source_out).frames
        self.record_in = Timecode(framerate=timecode_rate, start_timecode=edit.record_in).frames
        self.record_out = Timecode(framerate=timecode_rate, start_timecode=edit.record_out).frames
        self.channels = edit.channels
        self.clip_name = edit.clip_name


class SourceFile:
    def __init__(self, path: str, ffprobe_executable='/usr/local/bin/ffprobe'):

        def probe() -> dict:
            cmd = [ffprobe_executable, '-of', 'json', '-show_format', '-show_streams', path]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                raise subprocess.CalledProcessError(p.returncode, subprocess.list2cmdline(cmd), stderr)
            return json.loads(stdout.decode('utf8'))

        self.path = path
        self.info = WavInfoReader(path)
        self.probe = probe()

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other.path

    @property
    def recommended_lane_name(self) -> Optional[Any]:
        track_1 = next(self.info.ixml.track_list, None)
        if track_1 is not None and track_1.channel_index is not None:
            return track_1.channel_index

        return None

    def match_for_clip(self, edit: DecodedEdit) -> bool:
        """
        Is this source file a match for the given clip?
        :param edit: the `DecodedEdit` to test
        :return: bool
        """

        def match_for_time_range(start: int, finish: int, frame_rate: int):
            file_start_fs = self.info.bext.originator_time
            file_finish_fs = file_start_fs + self.info.data.frame_count
            file_start = file_start_fs * frame_rate / self.info.fmt.sample_rate
            file_finish = file_finish_fs * frame_rate / self.info.fmt.sample_rate
            return file_start <= start <= file_finish and file_start <= finish <= file_finish

        if not match_for_time_range(edit.source_in, edit.source_out, edit.frame_rate):
            return False

        if edit.source_file == os.path.basename(self.path):
            return True
        elif edit.source_name == os.path.basename(self.path):
            return True
        elif edit.source_name == self.info.ixml.tape:
            return True
        else:
            return False


@total_ordering
class Lane:
    def __init__(self, channel, lane):
        self.channel = channel
        self.lane = lane

    @property
    def slot_name(self):
        return f"A{self.channel}_{self.lane}"

    def __eq__(self, other):
        if isinstance(other, Lane):
            return self.slot_name == other.slot_name
        else:
            return False

    def __hash__(self):
        return hash(self.slot_name)

    def __lt__(self, other):
        if self.channel == other.channel:
            return self.lane < other.lane
        else:
            return self.channel < other.channel

    def successor(self):
        index_num = re.search('(^.*?)([0-9]+$)', self.lane)

        if index_num is not None:
            numeric = int(index_num.group(2))
            return Lane(self.channel, index_num.group(1) + str(numeric + 1))
        else:
            return Lane(self.channel, self.lane + '.1')


class SourceClipInstruction:
    def __init__(self, lane: Lane, edit: DecodedEdit, source: SourceFile):
        self.lane = lane
        self.source_start = edit.source_in
        self.record_start = edit.record_in
        self.length = edit.source_out - edit.source_in
        self.source = source
        self.name = edit.clip_name or os.path.basename(source.path)


class MatchedClip:
    def __init__(self, edit: DecodedEdit, source_files: Iterable[SourceFile]):
        self.edit = edit
        matching_files = filter(lambda f: f.match_for_clip(edit), source_files)
        self.sources = list(matching_files)

    @property
    def source_clip_instructions(self) -> Iterable[SourceClipInstruction]:
        for (source, lane) in self.source_files_with_lane_assignments:
            yield SourceClipInstruction(lane=lane, edit=self.edit, source=source)

    @property
    def source_files_with_lane_assignments(self) -> Iterable[Tuple[SourceFile, Lane]]:
        lane_list = set()
        for channel in self.edit.channels:
            for source_file in self.sources:
                trial = source_file.recommended_lane_name or ""
                lane = Lane(channel=channel, lane=trial)
                while lane in lane_list:
                    lane = lane.successor()
                lane_list.add(lane)
                yield source_file, lane


def add_source_clips_to_lane(clips_this_lane, f, slot, source_map):
    time_cursor = 0
    for clip in clips_this_lane:
        if clip.record_start > time_cursor:
            filler_length = clip.record_start - time_cursor
            filler = f.create.Filler(media_kind='sound', length=filler_length)
            slot.segment.components.append(filler)
            time_cursor = time_cursor + filler_length
        master_mob: aaf2.mobs.MasterMob = source_map[clip.source.path]
        source_slot = next((slot for slot in master_mob.slots if slot.media_kind == 'sound'), None)
        source_clip = master_mob.create_source_clip(source_slot=source_slot,
                                                    start=clip.source_start, length=clip.length, media_kind='sound')
        slot.segment.components.append(source_clip)
        time_cursor = time_cursor + clip.length


class EDLAAFConverter:
    def __init__(self, source_file_paths: Iterable[str], edl: pycmx.parse_cmx_events.EditList,
                 timecode_rate: int, out_file=None, composition_name=None):
        self.source_file_paths = source_file_paths
        self.edl = edl
        self.timecode_rate = timecode_rate
        self.composition_name = composition_name or self.edl.title
        self.out_file = out_file or self.composition_name + '.aaf'

    def convert(self):
        with aaf2.open(self.out_file, 'wb') as f:
            source_map = self.add_sources_to_aaf(f)

            composition_mob: aaf2.mobs.CompositionMob = f.create.CompositionMob(name=self.composition_name)
            composition_mob.usage = 'Usage_TopLevel'
            f.content.append(composition_mob)

            marshalled_clips = self.marshall_clips_to_lanes()
            lanes = sorted(marshalled_clips.keys())

            for lane in lanes:
                clips_this_lane = marshalled_clips[lane]
                slot: aaf2.mobslots.TimelineMobSlot = composition_mob.create_sound_slot(edit_rate=self.timecode_rate)
                slot.name = lane.slot_name
                add_source_clips_to_lane(clips_this_lane, f, slot, source_map)

    def add_sources_to_aaf(self, f):
        source_map = {}
        for source_file in self.used_files:
            master_mob, _, _ = f.content.create_ama_link(source_file.path, source_file.probe)
            source_map[source_file.path] = master_mob

        return source_map

    @property
    def source_files(self):
        return map(SourceFile, self.source_file_paths)

    @property
    def decoded_events(self) -> Iterable[DecodedEdit]:
        edits = itertools.chain.from_iterable([event.edits for event in self.edl.events])
        return map(DecodedEdit, zip(edits, itertools.repeat(self.timecode_rate)))

    @property
    def source_clip_instructions(self) -> Iterable[SourceClipInstruction]:
        matched_clips = map(MatchedClip, zip(self.decoded_events, itertools.repeat(self.source_files)))
        return itertools.chain.from_iterable([m.source_clip_instructions for m in matched_clips])

    @property
    def used_files(self) -> Iterable[SourceFile]:
        unique_files = set()
        for file in map(lambda i: i.source, self.source_clip_instructions):
            if file not in unique_files:
                unique_files.add(file)
                yield file

    def marshall_clips_to_lanes(self) -> Dict[Lane, List[SourceClipInstruction]]:
        lane_map: Dict[Lane, List[SourceClipInstruction]] = {}
        for sci in self.source_clip_instructions:
            if sci.lane not in lane_map:
                lane_map[sci.lane] = []

            lane_map[sci.lane].append(sci)

        for lane in lane_map:
            lane_map[lane] = sorted(lane_map[lane], key=lambda i: i.record_start)

        return lane_map
