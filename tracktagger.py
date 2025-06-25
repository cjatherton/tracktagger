#!/usr/bin/env python
#
# Copyright 2025 Christopher Atherton <the8lack8ox@pm.me>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

"""Read specially formatted 'trackinfo' files and apply contained tag information."""

import re
import sys
import math
from pathlib import Path
import tempfile
import subprocess
import zipfile
from multiprocessing import Pool
import argparse

ARCHIVE_EXTS = (".zip", ".rar", ".7z")

UNKNOWN_ALBUM_NAME = "UnknownAlbum"

TRACKINFO_RE = re.compile(r"([a-zA-Z]+)(?:\[([0-9]+)\])?=(.*)")
INPUT_TRACKINFO_RE = re.compile(r"INPUT(?:\[[0-9]+\])?=(.*)", re.I)
TRACKINFO_STANDARD_KEYS = (
    "INPUT",
    "TITLE",
    "ARTIST",
    "LYRICIST",
    "COMPOSER",
    "ARRANGER",
    "ALBUM",
    "DISCNUMBER",
    "GENRE",
    "DATE",
    "LABEL",
    "COMMENT",
    "COVER"
)

TRACK_INPUT_RE = re.compile(r".*?([0-9]+).*\.flac", re.I)

def truncate_filename(filename, max_bytes=255, encoding=None):
    """Truncate filenames if they're too big for the filesystem."""
    if encoding is None:
        working_enc = 'utf-16' if sys.platform.startswith('win') else 'utf-8'
    else:
        working_enc = encoding
    path = Path(filename)
    extension = path.suffix
    base = path.name.removesuffix(extension)
    max_base_bytes = max_bytes - len(extension.encode(working_enc))
    encoded_base = base.encode(working_enc)
    if len(encoded_base) > max_base_bytes:
        truncated_bytes = encoded_base[:max_base_bytes]
        try:
            truncated_base = truncated_bytes.decode(working_enc)
        except UnicodeDecodeError as e:
            while len(truncated_bytes) > 0:
                try:
                    truncated_base = truncated_bytes.decode(working_enc)
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
            else:
                raise ValueError(f"'{filename}' could not be truncated") from e
        ret = Path(truncated_base + extension)
        print(f"WARNING: Filename '{filename}' has been truncated to '{ret}'!")
    else:
        ret = path
    return ret

def expand_archive(path, out_dir):
    """Expands archives creating a temporary container directory and returns the path of that."""
    match path.suffix.lower():
        case ".zip":
            container_dir = Path(tempfile.mkdtemp(dir=out_dir))
            with zipfile.ZipFile(path) as archive:
                archive.extractall(container_dir)
        case ".rar":
            container_dir = Path(tempfile.mkdtemp(dir=out_dir))
            subprocess.run(
                ["unrar", "x", path, container_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        case ".7z":
            container_dir = Path(tempfile.mkdtemp(dir=out_dir))
            subprocess.run(
                ["7za", "x", f"-o{container_dir}", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        case _:
            raise TypeError(f"Unknown archive format '{path.suffix}'")
    return container_dir

def expand_archives_in_tree(paths, tmp_dir, parent=Path()):
    """
    Expands all archives in paths and returns a mapping from the original to new locations.

    Parameters:
        paths ([Path]): List of paths to expand.
        tmp_dir (Path): Place to put expanded archives.
        parent (Path): Used only for internal recursion, ignore.

    Returns:
        {Path: Path}: Mapping of original paths to new locations with archives expanded.
    """
    nodes = {}
    for path in paths:
        nodes.setdefault(Path(path.parts[0]), set()).add(Path(*path.parts[1:]))

    new_nodes = []
    for head, tails in nodes.items():
        stub = parent / head
        if stub.is_file() and stub.suffix.lower() in ARCHIVE_EXTS:
            archive_path = expand_archive(stub, tmp_dir)
            archive_files = list(archive_path.iterdir())
            if len(archive_files) == 1 and archive_files[0].is_dir():
                new_nodes.append((stub, archive_files[0], tails))
            else:
                new_nodes.append((stub, archive_path, tails))
        else:
            new_nodes.append((stub, stub, tails))

    ret = {}
    for stub, real_path, tails in new_nodes:
        if Path() in tails:
            ret[Path(stub.parts[-1])] = real_path
            tails.remove(Path())
        if len(tails) > 0:
            for base, mapped in expand_archives_in_tree(tails, tmp_dir, real_path).items():
                ret[stub.parts[-1] / base] = mapped
    return ret

def resolve_trackinfo_inputs(path, tmp_dir):
    """Returns the inputs from the trackinfo at 'path' mapped to real locations."""
    inputs = set()
    with path.open('r') as file:
        for line in file:
            m = INPUT_TRACKINFO_RE.fullmatch(line.rstrip())
            if m is not None:
                p = Path(m.group(1))
                if p.is_absolute():
                    # If input path is absolute, that is the input path
                    inputs.add(p.resolve())
                else:
                    # Otherwise, the input is relative to
                    # the location of the trackinfo's location
                    inputs.add((path.parent / p).resolve())
    return expand_archives_in_tree(inputs, tmp_dir)

def parse_trackinfo_meta(path, input_map):
    """Parse a TRACKINFO file and return a dict of albums."""
    track_meta = {}
    global_meta = {'ALBUM': None, 'DISCNUMBER': None}

    with path.open('r') as file:
        for line in file:
            line = line.rstrip()
            # Skip empty lines
            if len(line) == 0:
                continue
            m = TRACKINFO_RE.fullmatch(line)
            if not m:
                raise ValueError(f"'{line}' is not a valid trackinfo line")
            key = m.group(1).upper()
            value = m.group(3).strip()
            if key not in TRACKINFO_STANDARD_KEYS:
                print(f"WARNING: '{key}' is not a standard key.")
            if m.group(2):
                # This is a track entry
                track_num = int(m.group(2))
                # Dictionary location
                match key:
                    case 'ALBUM':
                        album = value
                        disc = global_meta['DISCNUMBER']
                    case 'DISCNUMBER':
                        album = global_meta['ALBUM']
                        # Verify the disc number is an integer value
                        if not value.isdigit():
                            raise ValueError(f"DISCNUMBER ('{value}') must be an integer")
                        disc = int(value)
                    case _:
                        album = global_meta['ALBUM']
                        disc = global_meta['DISCNUMBER']
                # Select track dict
                dst_dict = track_meta.setdefault(album, {}).setdefault(disc, {}) \
                    .setdefault(track_num, global_meta | {'TRACKNUMBER': track_num})
            else:
                # Select global dict
                dst_dict = global_meta
            # Set key-value
            if len(value) == 0 and key in dst_dict:
                # Delete this entry
                del dst_dict[key]
                continue
            match key:
                case 'INPUT':
                    # Inputs are resolved relative to trackinfo location
                    # Reference input_map dict
                    dst_dict['INPUT'] = input_map[(path.parent / value).resolve()]
                case 'COVER':
                    value = Path(value)
                    if value.is_absolute():
                        # If cover path is absolute, that is the cover path
                        dst_dict['COVER'] = value
                    elif 'INPUT' in dst_dict:
                        # If there is an input in the meta,
                        # the cover path is relative to that input
                        dst_dict['COVER'] = (dst_dict['INPUT'] / value).resolve()
                    else:
                        # Otherwise, the cover is relative to
                        # the location of the trackinfo's location
                        dst_dict['COVER'] = (path.parent / value).resolve()
                case 'DISCNUMBER':
                    # Verify the disc number is an integer value
                    if not value.isdigit():
                        raise ValueError(f"DISCNUMBER ('{value}') must be an integer")
                    dst_dict['DISCNUMBER'] = int(value)
                case _:
                    dst_dict[key] = value

    return track_meta

def calc_padding(info):
    """Calculate padding values disc and track strings."""
    disc_ret = {}
    track_ret = {}
    for album, discs in info.items():
        discs_no_none = [v for v in discs.keys() if v is not None]
        if len(discs_no_none) > 0:
            disc_ret[album] = math.floor(math.log10(max(discs_no_none))) + 1
        else:
            disc_ret[album] = 0
        track_ret[album] = {}
        for disc, tracks in discs.items():
            track_ret[album][disc] = math.floor(math.log10(max(tracks.keys()))) + 1
    return (disc_ret, track_ret)

def track_id_to_string(album, disc, num, disc_padding=0, track_padding=0):
    """Pretty printed string for track on disc on album."""
    if album:
        album_str = f"\"{album}\":"
    else:
        album_str = ""
    if disc:
        disc_str = f"{disc:0{disc_padding}d}."
    else:
        disc_str = ""
    return f"{album_str}#{disc_str}{num:0{track_padding}d}"

def map_tracks(info):
    """Returns file paths for the tracks in info."""
    ret = {}
    for album, discs in info.items():
        ret[album] = {}
        for disc, tracks in discs.items():
            ret[album][disc] = {}
            for num, tags in tracks.items():
                for f in tags['INPUT'].iterdir():
                    m = TRACK_INPUT_RE.fullmatch(f.name)
                    if m and int(m.group(1)) == num:
                        ret[album][disc][num] = f.name
                        break
                else:
                    raise FileNotFoundError("Could not find file for track "
                        f"{track_id_to_string(album, disc, num)}"
                    )
    return ret

def print_track_map(track_map, disc_padding, track_padding):
    """Display the track map to the user."""
    for album, discs in track_map.items():
        for discnum, tracks in discs.items():
            for num, filename in tracks.items():
                print(
                    f"{track_id_to_string(album, discnum, num,
                        disc_padding[album], track_padding[album][discnum])}"
                    f" ← {filename}"
                )

def make_album_dirs(out_dir, info):
    """Create album directories."""
    for album in info.keys():
        if album is not None:
            album_dir = out_dir / album.replace('/', '_')
        else:
            album_dir = out_dir / UNKNOWN_ALBUM_NAME
        album_dir.mkdir()
        print(f"Created album directory: {album_dir}")

def map_covers(info, tmp_dir):
    """Returns a map of where covers actually are to handle
    extraction of cover art from FLAC inputs."""
    ret = {}
    extract_cover_set = set()
    for discs in info.values():
        for tracks in discs.values():
            for tags in tracks.values():
                if 'COVER' in tags:
                    if tags['COVER'].suffix.lower() == ".flac":
                        extract_cover_set.add(tags['COVER'])
                    else:
                        ret[tags['COVER']] = tags['COVER']
    if len(extract_cover_set) > 0:
        cover_dir = tmp_dir / "covers"
        cover_dir.mkdir()
    for flac_cover in extract_cover_set:
        with tempfile.NamedTemporaryFile(dir=cover_dir, delete=False) as cover_file:
            try:
                subprocess.run(
                    ["metaflac", "--export-picture-to=-", flac_cover],
                    stdout=cover_file,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            except subprocess.CalledProcessError:
                print(f"ERROR: Could not extract cover art from '{flac_cover}'!", file=sys.stderr)
            ret[flac_cover] = Path(cover_file.name)
    return ret

def gen_output_path(tags, out_dir, disc_padding, track_padding):
    """Create the output path for this track."""
    if tags['ALBUM'] is None:
        album_dir = UNKNOWN_ALBUM_NAME
    else:
        album_dir = tags['ALBUM'].replace('/', '_')
    filename = ""
    if tags['DISCNUMBER'] is not None:
        filename += str(tags['DISCNUMBER']).zfill(disc_padding) + "."
    filename += str(tags['TRACKNUMBER']).zfill(track_padding)
    if 'TITLE' in tags and 'ARTIST' in tags:
        filename += ". " + tags['ARTIST'] + " - " + tags['TITLE']
    elif 'TITLE' in tags:
        filename += ". " + tags['TITLE']
    elif 'ARTIST' in tags:
        filename += ". " + tags['ARTIST']
    return out_dir / album_dir / truncate_filename(filename.replace('/', '_') + ".flac")

def process_one(args):
    """Process a file."""
    in_path, out_dir, tags, cover_map, disc_padding, track_padding = args
    out_path = gen_output_path(tags, out_dir, disc_padding, track_padding)
    print(f"{track_id_to_string(tags['ALBUM'], tags['DISCNUMBER'], tags['TRACKNUMBER'],
            disc_padding, track_padding)}"
        f" → {out_path.name}"
    )
    with subprocess.Popen(
                ["flac", "--decode", "--stdout", in_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            ) as dec_proc:
        tag_args = []
        for field, value in sorted(tags.items()):
            if field == 'COVER':
                tag_args.append(f"--picture={cover_map[value]}")
            elif field != 'INPUT' and value is not None:
                tag_args.append(f"--tag={field}={value}")
        try:
            subprocess.run(
                ["flac", "--best"] + tag_args + [f"--output-name={out_path}", "-"],
                stdin=dec_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"ERROR: Problem creating output '{out_path}'!", file=sys.stderr)
            return None
        return out_path

def process(info, out_dir, track_map, cover_map, disc_padding, track_padding):
    """Perform compression."""
    ret = {}
    with Pool() as pool:
        album_procs = {}
        for album, discs in info.items():
            album_args = []
            for discnum, tracks in discs.items():
                for num, tags in tracks.items():
                    album_args.append(
                        (tags['INPUT'] / track_map[album][discnum][num], out_dir,
                            tags, cover_map, disc_padding[album], track_padding[album][discnum])
                    )
            album_procs[album] = pool.map_async(process_one, album_args)
        for album, files in album_procs.items():
            ret[album] = list(filter(None, files.get()))
    return ret

def add_replaygain_one(args):
    """Add ReplayGain tags to an album with paths."""
    album, paths = args
    if len(paths) > 0:
        if album is not None:
            print(f"Adding ReplayGain tags to \"{album}\" ...")
        else:
            print("Adding ReplayGain tags to unknown album ...")
        try:
            subprocess.run(
                ["metaflac", "--add-replay-gain"] + paths,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"ERROR: Problem adding ReplayGain tags to \"{album}\"!", file=sys.stderr)
    elif album is not None:
        print(f"WARNING: No files in \"{album}\" to add ReplayGain tags to!")
    else:
        print("WARNING: No files in unknown album to add ReplayGain tags to!")

def add_replaygain(albums):
    """Add ReplayGain tags to group of albums."""
    with Pool() as pool:
        pool.map(add_replaygain_one, albums.items())

def parse_cli(args=None):
    """Parse command line and get input trackinfo and output directory."""
    parser = argparse.ArgumentParser(description="apply tags to FLAC files")
    parser.add_argument("trackinfo", type=Path, metavar="TRACKINFO",
        help="trackinfo file containing new tags")
    parser.add_argument("-o", "--output-dir", default=Path.cwd(), type=Path,
        help="location to place result")
    cli = parser.parse_args(args)
    return (cli.trackinfo.resolve(), cli.output_dir.resolve())

def main(argv=None):
    """Main routine."""
    trackinfo_path, out_dir = parse_cli(argv[1:] if argv is not None else None)

    with tempfile.TemporaryDirectory(prefix="tracktagger-") as work_dir:
        work_path = Path(work_dir)
        print(f"Resolving inputs from trackinfo file: '{trackinfo_path}' ...")
        input_map = resolve_trackinfo_inputs(trackinfo_path, work_path)
        print(f"Parsing trackinfo file meta: '{trackinfo_path}' ...")
        info = parse_trackinfo_meta(trackinfo_path, input_map)
        disc_padding, track_padding = calc_padding(info)
        print("Mapping tracks ...")
        track_map = map_tracks(info)
        print_track_map(track_map, disc_padding, track_padding)
        cover_map = map_covers(info, work_path)
        print("Compressing ...")
        make_album_dirs(out_dir, info)
        albums = process(info, out_dir, track_map, cover_map, disc_padding, track_padding)
        add_replaygain(albums)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
