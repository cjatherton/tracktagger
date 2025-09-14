# tracktagger.py
Neatly tag FLAC files with metadata from specially formatted plain text file.

## Overview
*tracktagger.py* is used to apply tag information stored in a text files (a *"TRACKINFO"* file) to FLAC audio files.

## TRACKINFO File Format
The format of this file is simple. To apply `somevalue` to a `SOMEFIELD`, for track number 2, add a line like this with the track number in brackets.
```text
SOMEFIELD[2]=somevalue
```
A line like this without the number in brackets causes the field to be applied to all following specific tracks mentioned.
```text
SOMEFIELD=somevalue
```

One line is critical and must be placed at the beginning of the file. This is the `INPUT` field, which refers to the directory where the input music files to be tagged are located. Two different forms affect how it works, a relative path...
```text
INPUT=path/to/tracks
```
...or an absolute path...
```text
INPUT=/path/to/tracks
```
In the relative case, the input path is processed relative to the location of the *TRACKINFO* file. Absolute paths simply point directly to the input location. You may have multiple `INPUT`s, to refer to tracks in different locations. This is required if you have multiple discs. The `DISCNUMBER` can be used to refer albums with multiple discs, but since ***tracktagger.py* automatically infers track numbers from the filename**, you must place multiple discs in separate locations and this requires using an `INPUT` line for each disc.

Here's an example.
```text
INPUT=../CD/Random Access Memories
ALBUM=Random Access Memories
ARTIST=Daft Punk
GENRE=Electronic
DATE=2013-05-17
LABEL=Columbia
COVER=cover.jpg
TITLE[1]=Give Life Back to Music
TITLE[2]=The Game of Love
TITLE[3]=Giorgio by Moroder
TITLE[4]=Within
TITLE[5]=Instant Crush (featuring Julian Casablancas)
TITLE[6]=Lose Yourself to Dance (featuring Pharrell Williams)
TITLE[7]=Touch (featuring Paul Williams)
TITLE[8]=Get Lucky (featuring Pharrell Williams and Nile Rodgers)
TITLE[9]=Beyond
TITLE[10]=Motherboard
TITLE[11]=Fragments of Time (featuring Todd Edwards)
TITLE[12]=Doin' It Right (featuring Panda Bear)
TITLE[13]=Contact
```

And here's another example for a two disc album.
```text
ALBUM=The 6 Unaccompanied Cello Suites Complete
ARTIST=Yo-Yo Ma
COMPOSER=J.S. Bach
GENRE=Classical
DATE=2012-06-12
INPUT=../CD/The 6 Unaccompanied Cello Suites Complete/Disc 1
COVER=../cover.jpg
DISCNUMBER=1
TITLE[1]=Suite No.1 in G Major, BWV 1007, Prélude
TITLE[2]=Suite No.1 in G Major, BWV 1007, Allemande
TITLE[3]=Suite No.1 in G Major, BWV 1007, Courante
TITLE[4]=Suite No.1 in G Major, BWV 1007, Sarabande
TITLE[5]=Suite No.1 in G Major, BWV 1007, Menuett I and II
TITLE[6]=Suite No.1 in G Major, BWV 1007, Gigue
TITLE[7]=Suite No.4 in E-Flat Major, BWV 1010, Prélude
TITLE[8]=Suite No.4 in E-Flat Major, BWV 1010, Allemande
TITLE[9]=Suite No.4 in E-Flat Major, BWV 1010, Courante
TITLE[10]=Suite No.4 in E-Flat Major, BWV 1010, Sarabande
TITLE[11]=Suite No.4 in E-Flat Major, BWV 1010, Bourrée I and II
TITLE[12]=Suite No.4 in E-Flat Major, BWV 1010, Gigue
TITLE[13]=Suite No.5 in C Minor, BWV 1011, Prélude
TITLE[14]=Suite No.5 in C Minor, BWV 1011, Allemande
TITLE[15]=Suite No.5 in C Minor, BWV 1011, Courante
TITLE[16]=Suite No.5 in C Minor, BWV 1011, Sarabande
TITLE[17]=Suite No.5 in C Minor, BWV 1011, Gavotte I and II
TITLE[18]=Suite No.5 in C Minor, BWV 1011, Gigue
INPUT=../CD/The 6 Unaccompanied Cello Suites Complete/Disc 2
DISCNUMBER=2
TITLE[1]=Suite No.2 in D Minor, BWV 1008, Prélude
TITLE[2]=Suite No.2 in D Minor, BWV 1008, Allemande
TITLE[3]=Suite No.2 in D Minor, BWV 1008, Courante
TITLE[4]=Suite No.2 in D Minor, BWV 1008, Sarabande
TITLE[5]=Suite No.2 in D Minor, BWV 1008, Menuett I and II
TITLE[6]=Suite No.2 in D Minor, BWV 1008, Gigue
TITLE[7]=Suite No.3 in C Major, BWV 1009, Prélude
TITLE[8]=Suite No.3 in C Major, BWV 1009, Allemande
TITLE[9]=Suite No.3 in C Major, BWV 1009, Courante
TITLE[10]=Suite No.3 in C Major, BWV 1009, Sarabande
TITLE[11]=Suite No.3 in C Major, BWV 1009, Bourrée I and II
TITLE[12]=Suite No.3 in C Major, BWV 1009, Gigue
TITLE[13]=Suite No.6 in D Major, BWV 1012, Prélude
TITLE[14]=Suite No.6 in D Major, BWV 1012, Allemande
TITLE[15]=Suite No.6 in D Major, BWV 1012, Courante
TITLE[16]=Suite No.6 in D Major, BWV 1012, Sarabande
TITLE[17]=Suite No.6 in D Major, BWV 1012, Gavotte I and II
TITLE[18]=Suite No.6 in D Major, BWV 1012, Gigue
```

Note the usage of `INPUT` and `DISCNUMBER` in tandem; `INPUT` must precede `DISCNUMBER`.

Also, `COVER` for cover art follows a similar syntax to `INPUT`. A relative `COVER` path is followed relative to the `INPUT`. An absolute `COVER` path points directly to the image file. If `COVER` appears before an `INPUT` has been declared, it is resolved relative to the *TRACKINFO* file location.

The following are considered standard fields.

1. TITLE
2. ARTIST
3. LYRICIST
4. COMPOSER
5. ARRANGER
6. ALBUM
7. DISCNUMBER
8. GENRE
9. DATE
10. LABEL
11. COMMENT

While they are not case-sensitive, the output of *tracktagger.py* will always raise them to uppercase.

## Script Usage
Once the *TRACKINFO* has been created, running *tracktagger.py* is straightforward.
```bash
tracktagger.py "Random Access Memories.tracks"
```
...assuming "Random Access Memories.tracks" is the name of your *TRACKINFO* file. By default, the output is put in a newly created directory with the album name in the current directory. The location of this output directory can be changed with the `-o, --output-dir` option. ReplayGain tags can be automatically added with `-g, --add-replaygain`. The filenames of the output have a certain format that cannot be changed at the moment. They will look like *04. Daft Punk - Within.flac*, or in the multidisc case, *2.07. Yo-Yo Ma - Prélude.flac*.

*tracktagger.py* will autodetect the corresponding track file to the track number in the input directory by looking at the first number appearing in the filename of each file and taking the first matching. Thus, "track03.cdda.flac" will match to track number 3.

*tracktagger.py* can only run on FLAC files currently. WAV files (or any other kind) will first have to be converted to FLAC first.

## Archives
*tracktagger.py* has the ability to extract music from within archives on-the-fly. (It can even look inside archives within archives.) Currently, it can extract from .zip (natively), .rar (with `unar` or `unrar`), .7z (with `unar` or `7za`) and anything `unar` supports (if installed). Refer to the archive just as you would any other input.
```text
INPUT=path/to/archive.zip
```
If the archive is properly wrapped in a container folder (all the contents of the archive expand into a single, top-level folder), it will automatically look inside. Do not refer to this folder in the input path. You can refer to folders buried within the archive. Consider a case where the archive has two discs. The previous example becomes like so...
```text
ALBUM=The 6 Unaccompanied Cello Suites Complete
ARTIST=Yo-Yo Ma
COMPOSER=J.S. Bach
GENRE=Classical
DATE=2012-06-12
INPUT=../CD/The 6 Unaccompanied Cello Suites Complete.zip/Disc 1
COVER=../cover.jpg
DISCNUMBER=1
TITLE[1]=Suite No.1 in G Major, BWV 1007, Prélude
TITLE[2]=Suite No.1 in G Major, BWV 1007, Allemande
TITLE[3]=Suite No.1 in G Major, BWV 1007, Courante
TITLE[4]=Suite No.1 in G Major, BWV 1007, Sarabande
TITLE[5]=Suite No.1 in G Major, BWV 1007, Menuett I and II
TITLE[6]=Suite No.1 in G Major, BWV 1007, Gigue
TITLE[7]=Suite No.4 in E-Flat Major, BWV 1010, Prélude
TITLE[8]=Suite No.4 in E-Flat Major, BWV 1010, Allemande
TITLE[9]=Suite No.4 in E-Flat Major, BWV 1010, Courante
TITLE[10]=Suite No.4 in E-Flat Major, BWV 1010, Sarabande
TITLE[11]=Suite No.4 in E-Flat Major, BWV 1010, Bourrée I and II
TITLE[12]=Suite No.4 in E-Flat Major, BWV 1010, Gigue
TITLE[13]=Suite No.5 in C Minor, BWV 1011, Prélude
TITLE[14]=Suite No.5 in C Minor, BWV 1011, Allemande
TITLE[15]=Suite No.5 in C Minor, BWV 1011, Courante
TITLE[16]=Suite No.5 in C Minor, BWV 1011, Sarabande
TITLE[17]=Suite No.5 in C Minor, BWV 1011, Gavotte I and II
TITLE[18]=Suite No.5 in C Minor, BWV 1011, Gigue
INPUT=../CD/The 6 Unaccompanied Cello Suites Complete.zip/Disc 2
DISCNUMBER=2
TITLE[1]=Suite No.2 in D Minor, BWV 1008, Prélude
TITLE[2]=Suite No.2 in D Minor, BWV 1008, Allemande
TITLE[3]=Suite No.2 in D Minor, BWV 1008, Courante
TITLE[4]=Suite No.2 in D Minor, BWV 1008, Sarabande
TITLE[5]=Suite No.2 in D Minor, BWV 1008, Menuett I and II
TITLE[6]=Suite No.2 in D Minor, BWV 1008, Gigue
TITLE[7]=Suite No.3 in C Major, BWV 1009, Prélude
TITLE[8]=Suite No.3 in C Major, BWV 1009, Allemande
TITLE[9]=Suite No.3 in C Major, BWV 1009, Courante
TITLE[10]=Suite No.3 in C Major, BWV 1009, Sarabande
TITLE[11]=Suite No.3 in C Major, BWV 1009, Bourrée I and II
TITLE[12]=Suite No.3 in C Major, BWV 1009, Gigue
TITLE[13]=Suite No.6 in D Major, BWV 1012, Prélude
TITLE[14]=Suite No.6 in D Major, BWV 1012, Allemande
TITLE[15]=Suite No.6 in D Major, BWV 1012, Courante
TITLE[16]=Suite No.6 in D Major, BWV 1012, Sarabande
TITLE[17]=Suite No.6 in D Major, BWV 1012, Gavotte I and II
TITLE[18]=Suite No.6 in D Major, BWV 1012, Gigue
```
Note that "The 6 Unaccompanied Cello Suites Complete.zip" can have a top-level container folder before "Disc 1" or "Disc 2", although it is technically optional (tarbombing is not advised).

## Cover Art Retrieval
Cover art can also be extracted from a FLAC file that has cover art in it.
```text
COVER=An Audio File.flac
```
Will make use of the cover art in "An Audio File.flac".

## License
This project is licensed under the [MIT License](LICENSE).