Forked from dcthomson/mkvdts2ac3.py and taken to surgery to fit my very specific needs.

`ac3.py` is a python script for linux, windows or os x which can be used
for duplicating any audio track and converting it into AC3.

The script analyzes a file, picks out non-AC3 audio tracks, converts them to AC3 and then remuxes them back into the original file. The video file is simply copied. If the file is in an MP4 container previously it will be output into a MKV container.

The outputted file with have the same file name suffixed with '.new'


Installation
============

Prerequisites
-------------
Make sure the executables for the following libraries are accessible.

1. [python](http://www.python.org/) - Python
2. [mkvtoolnix](http://www.bunkus.org/videotools/mkvtoolnix/) - Matroska tools
3. [ffmpeg](http://ffmpeg.org/) - Audio conversion tool

*Note: If you are a Mac OS X user you may need to compile these libraries.*

Usage
=====

<pre>
usage: mkvdts2ac3.py FileOrDirectory [FileOrDirectory ...]

positional arguments:
  FileOrDirectory       a file or directory (wildcards may be used)
</pre>