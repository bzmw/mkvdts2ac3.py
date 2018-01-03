#!/usr/bin/env python

#Copyright (C) 2012  Drew Thomson
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Convert the DTS audio in MKV files to AC3.
#
# mkvdts2ac3.py is a python script for linux, windows or os x which can be used
# for converting the DTS in Matroska (MKV) files to AC3. It provides you with a
# set of options for controlling the resulting file.

##############################################################################
### OPTIONS                                                                ###

## These options take an argument.

# NZBGet destination directory
#destdir=

# Apply header compression to streams (See mkvmerge's --compression)
#compress=

# Custom AC3 track title
#custom=

# Mark AC3 track as default (True, False).
#default=False

# Leave AC3 track out of file. Does not modify the original matroska file. This overrides '-n' and '-d' arguments (True, False).
#external=False

# Path of ffmpeg (if not in path)
#ffmpegpath=

# Force processing when AC3 track is detected (True, False).
#force=False

# Keep external DTS track (implies '-n') (True, False).
#keepdts=False

# check md5 of files before removing the original if destination directory is on a different device than the original file (True, False).
#mdfive=False

# Path of mkvextract, mkvinfo and mkvmerge (if not in path)
#mkvtoolnixpath=

# Do not copy over original. Create new adjacent file (True, False).
#new=False

# Do not retain the DTS track (True, False).
#nodts=False

# Remove subtitles (True, False).
#no_subtitles=False

# Overwrite file if already there (True, False).
#overwrite=False

# Position of AC3 track in file (initial = First track in file, last = Last track in file, afterdts = After the DTS track)
#position=last

# Make ac3 track stereo instead of 6 channel (True, False).
#stereo=False

# Specify alternate DTS track. If it is not a DTS track it will default to the first DTS track found
#track=

# Process all the DTS tracks (True, False).
#all_tracks=False

# Specify alternate temporary working directory
#wd=

# Create output in mp4 format (True, False).
#mpfour=False

# Also add aac track (True, False).
#aac=False

# Custom AAC track title
#aaccustom=

# Make aac track stereo instead of 6 channel (True, False).
#aacstereo=False

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import argparse
import os
import subprocess
import time
import glob
import re
import tempfile
import sys
import ConfigParser
import shutil
import hashlib
import textwrap
import errno
import stat

version = "1.1"

sab = False
nzbget = False

# create parser
parser = argparse.ArgumentParser(description='convert matroska (.mkv) video files audio portion from dts to ac3')

# set config file arguments
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "mkvdts2ac3.cfg")

if os.path.isfile(configFilename):
    config = ConfigParser.SafeConfigParser()
    config.read(configFilename)
    defaults = dict(config.items("mkvdts2ac3"))
    for key in defaults:
        if key == "verbose":
            defaults["verbose"] = int(defaults["verbose"])

    parser.set_defaults(**defaults)

parser.add_argument('fileordir', metavar='FileOrDirectory', nargs='+', help='a file or directory (wildcards may be used)')

parser.add_argument("--aac", help="Also add aac track", action="store_true")
parser.add_argument("--aacstereo", help="Make aac track stereo instead of 6 channel", action="store_true")
parser.add_argument("--aaccustom", metavar="TITLE", help="Custom AAC track title")
parser.add_argument("-c", "--custom", metavar="TITLE", help="Custom AC3 track title")
parser.add_argument("-d", "--default", help="Mark AC3 track as default", action="store_true")
parser.add_argument("--destdir", metavar="DIRECTORY", help="Destination Directory")
parser.add_argument("-e", "--external", action="store_true",
                    help="Leave AC3 track out of file. Does not modify the original matroska file. This overrides '-n' and '-d' arguments")
parser.add_argument("-f", "--force", help="Force processing when AC3 track is detected", action="store_true")
parser.add_argument("--ffmpegpath", metavar="DIRECTORY", help="Path of ffmpeg")
parser.add_argument("-k", "--keepdts", help="Keep external DTS track (implies '-n')", action="store_true")
parser.add_argument("--md5", help="check md5 of files before removing the original if destination directory is on a different device than the original file", action="store_true")
parser.add_argument("--mp4", help="create output in mp4 format", action="store_true")
parser.add_argument("--mkvtoolnixpath", metavar="DIRECTORY", help="Path of mkvextract, mkvinfo and mkvmerge")
parser.add_argument("-n", "--nodts", help="Do not retain the DTS track", action="store_true")
parser.add_argument("--new", help="Do not copy over original. Create new adjacent file", action="store_true")
parser.add_argument("--no-subtitles", help="Remove subtitles", action="store_true")
parser.add_argument("-o", "--overwrite", help="Overwrite file if already there. This only applies if destdir or sabdestdir is set", action="store_true")
parser.add_argument("-p", "--position", choices=['initial', 'last', 'afterdts'], default="initial", help="Set position of AC3 track. 'initial' = First track in file, 'last' = Last track in file, 'afterdts' = After the DTS track [default: initial]")
parser.add_argument("-r", "--recursive", help="Recursively descend into directories", action="store_true")
parser.add_argument("-s", "--compress", metavar="MODE", help="Apply header compression to streams (See mkvmerge's --compression)", default='none')
parser.add_argument("--sabdestdir", metavar="DIRECTORY", help="SABnzbd Destination Directory")
parser.add_argument("--stereo", help="Make ac3 track stereo instead of 6 channel", action="store_true")
parser.add_argument("-t", "--track", metavar="TRACKID", help="Specify alternate DTS track. If it is not a DTS track it will default to the first DTS track found")
parser.add_argument("--all-tracks", help="Convert all DTS tracks", action="store_true");
parser.add_argument("-w", "--wd", metavar="FOLDER", help="Specify alternate temporary working directory")
parser.add_argument("-v", "--verbose", help="Turn on verbose output. Use more v's for more verbosity. -v will output what it is doing. -vv will also output the command that it is running. -vvv will also output the command output", action="count")
parser.add_argument("-V", "--version", help="Print script version information", action='version', version='%(prog)s ' + version + ' by Drew Thomson')
parser.add_argument("--test", help="Print commands only, execute nothing", action="store_true")
parser.add_argument("--debug", help="Print commands and pause before executing each", action="store_true")

args = parser.parse_args()

if not args.verbose:
    args.verbose = 0

def winexe(program):
    if sys.platform == "win32" and not program.endswith(".exe"):
        program += ".exe"
    return program

# set ffmpeg and mkvtoolnix paths
if args.mkvtoolnixpath:
    mkvinfo = os.path.join(args.mkvtoolnixpath, "mkvinfo")
    mkvinfo = winexe(mkvinfo)
    mkvmerge = os.path.join(args.mkvtoolnixpath, "mkvmerge")
    mkvmerge = winexe(mkvmerge)
    mkvextract = os.path.join(args.mkvtoolnixpath, "mkvextract")
    mkvextract = winexe(mkvextract)
if not args.mkvtoolnixpath or not os.path.exists(mkvinfo):
    mkvinfo = "mkvinfo"
if not args.mkvtoolnixpath or not os.path.exists(mkvmerge):
    mkvmerge = "mkvmerge"
if not args.mkvtoolnixpath or not os.path.exists(mkvextract):
    mkvextract = "mkvextract"

if args.ffmpegpath:
    ffmpeg = os.path.join(args.ffmpegpath, "ffmpeg")
    ffmpeg = winexe(ffmpeg)
if not args.ffmpegpath or not os.path.exists(ffmpeg):
    ffmpeg = "ffmpeg"


# check paths
def which(program):
    if sys.platform == "win32" and not program.endswith(".exe"):
        program += ".exe"
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath = os.path.split(program)[0]
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

missingprereqs = False
missinglist = []
if not which(mkvextract):
    missingprereqs = True
    missinglist.append("mkvextract")
if not which(mkvinfo):
    missingprereqs = True
    missinglist.append("mkvinfo")
if not which(mkvmerge):
    missingprereqs = True
    missinglist.append("mkvmerge")
if not which(ffmpeg):
    missingprereqs = True
    missinglist.append("ffmpeg")
if missingprereqs:
    sys.stdout.write("You are missing the following prerequisite tools: ")
    for tool in missinglist:
        sys.stdout.write(tool + " ")
    if not args.mkvtoolnixpath and not args.ffmpegpath:
        print "\nYou can use --mkvtoolnixpath and --ffmpegpath to specify the path"
    else:
        print
    sys.exit(1)

if not args.verbose:
    args.verbose = 0

if args.verbose < 2 and (args.test or args.debug):
    args.verbose = 2

if sab:
    args.fileordir = [args.fileordir[0]]
    args.verbose = 3

if args.debug and args.verbose == 0:
    args.verbose = 1

def doprint(mystr, v=0):
    if args.verbose >= v:
        sys.stdout.write(mystr)

def silentremove(filename):
    try:
        os.chmod(filename, stat.S_IWRITE )
        os.remove(filename)
    except OSError, e:
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured

def elapsedstr(starttime):
    elapsed = (time.time() - starttime)
    minutes = int(elapsed / 60)
    mplural = 's'
    if minutes == 1:
        mplural = ''
    seconds = int(elapsed) % 60
    splural = 's'
    if seconds == 1:
        splural = ''
    return str(minutes) + " minute" + mplural + " " + str(seconds) + " second" + splural

def getduration(time):
    (hms, ms) = time.split('.')
    (h, m, s) = hms.split(':')
    totalms = int(ms) + (int(s) * 100) + (int(m) * 100 * 60) + (int(h) * 100 * 60 * 60)
    return totalms

def runcommand(title, cmdlist):
    if args.debug:
        raw_input("Press Enter to continue...")
    cmdstarttime = time.time()
    if args.verbose >= 1:
        sys.stdout.write(title)
        if args.verbose >= 2:
            cmdstr = ''
            for e in cmdlist:
                cmdstr += e + ' '
            print
            print "    Running command:"
            print textwrap.fill(cmdstr.rstrip(), initial_indent='      ', subsequent_indent='      ')
    if not args.test:
        if args.verbose >= 3:
            subprocess.call(cmdlist)
        elif args.verbose >= 1:
            if "ffmpeg" in cmdlist[0]:
                proc = subprocess.Popen(cmdlist, stderr=subprocess.PIPE)
                line = ''
                while True:
                    out = proc.stderr.read(1)
                    if out == '' and proc.poll() != None:
                        break
                    if out != '\r':
                        line += out
                    else:
                        if 'size= ' in line:
                            sys.stdout.write('\r')
                            sys.stdout.write(line.strip())
                        line = ''
                    sys.stdout.flush()
                print "\r" + title + elapsedstr(cmdstarttime)
            else:
                proc = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
                line = ''
                progress_regex = re.compile("Progress: (\d+%)")
                while True:
                    out = proc.stdout.read(1)
                    if out == '' and proc.poll() != None:
                        break
                    if out != '\r':
                        line += out
                    else:
                        if 'Progress: ' in line:
                            match = progress_regex.search(line)
                            if match:
                                percentage = match.group(1)
                                sys.stdout.write("\r" + title + percentage)
                        line = ''
                    sys.stdout.flush()
                print "\r" + title + elapsedstr(cmdstarttime)
        else:
            subprocess.call(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path

def getmd5(fname, block_size=2**12):
    md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        doprint(fname + ": " + md5.hexdigest() + "\n", 3)
    return md5.hexdigest()

def check_md5tree(orig, dest):
    rt = True
    orig = os.path.abspath(orig)
    dest = os.path.abspath(dest)
    for ofile in os.listdir(orig):
        if rt == True:
            if os.path.isdir(os.path.join(orig, ofile)):
                doprint("dir: " + os.path.join(orig, ofile) + "\n", 3)
                odir = os.path.join(orig, ofile)
                ddir = os.path.join(dest, ofile)
                rt = check_md5tree(odir, ddir)
            else:
                doprint("file: " + os.path.join(orig, ofile) + "\n", 3)
                if getmd5(os.path.join(orig, ofile)) != getmd5(os.path.join(dest, ofile)):
                    rt = False
    return rt

def process(ford):
    if os.path.isdir(ford):
        doprint("    Processing dir:  " + ford + "\n", 3)
        if args.recursive:
            for f in os.listdir(ford):
                process(os.path.join(ford, f))
    else:
        doprint("    Processing file: " + ford + "\n", 3)
        # check if file is an mkv file
        child = subprocess.Popen([mkvmerge, "-i", ford], stdout=subprocess.PIPE)
        child.communicate()[0]
        if child.returncode == 0:
            starttime = time.time()

            # set up temp dir
            tempdir = False
            if args.wd:
                tempdir = args.wd
                if not os.path.exists(tempdir):
                    os.makedirs(tempdir)
            else:
                tempdir = tempfile.mkdtemp()
                tempdir = os.path.join(tempdir, "mkvdts2ac3")

            (dirName, fileName) = os.path.split(ford)
            fileBaseName = os.path.splitext(fileName)[0]

            doprint("filename: " + fileName + "\n", 1)

            newmkvfile = fileBaseName + '.mkv'
            tempnewmkvfile = os.path.join(tempdir, newmkvfile)
            adjacentmkvfile = os.path.join(dirName, fileBaseName + '.new.mkv')
            mp4file = os.path.join(dirName, fileBaseName + '.mp4')
            files = []
            if not args.external and not args.mp4:
                files.append(fileName)

            # get dts track id and video track id
            output = subprocess.check_output([mkvmerge, "-i", ford])
            lines = output.split("\n")
            altdtstrackid = False
            videotrackid = False
            alreadygotac3 = False
            audiotracks = []
            dtstracks = []
            for line in lines:
                linelist = line.split(' ')
                trackid = False
                if len(linelist) > 2:
                    trackid = linelist[2]
                    linelist = trackid.split(':')
                    trackid = linelist[0]
                if ' audio (' in line:
                    audiotracks.append(trackid)
                if (' audio (A_DTS)' in line
                    or ' audio (DTS' in line
                    or ' audio (A_TrueHD' in line
                    or ' audio (TrueHD' in line
                    or ' audio (A_E-AC-3' in line
                    or ' audio (E-AC-3' in line):
                        dtstracks.append(trackid)
                elif ' video (' in line:
                    videotrackid = trackid
                if args.track:
                    matchObj = re.match( r'Track ID ' + args.track + r': audio \(A?_?DTS', line)
                    if matchObj:
                        altdtstrackid = args.track
            if altdtstrackid:
                dtstracks[:] = []
                dtstracks.append(altdtstrackid)

            if not dtstracks:
                doprint("  No DTS tracks found\n", 1)
            else:
                args.total_dts_files += 1
                args.all_files_affected.append(ford)
                if not args.all_tracks:
                    dtstracks = dtstracks[0:1]

                # 3 jobs per DTS track (Extract DTS, Extract timecodes, Transcode)
                totaljobs = (3 * len(dtstracks))
                # 1 Remux+ 1
                if not args.external:
                    totaljobs += 1
                if args.aac:
                    # 1 extra transcode per DTS track
                    totaljobs += len(dtstracks)
                if args.mp4:
                    # Convert mkv -> mp4
                    totaljobs += 1
                jobnum = 1

                dtsinfo = dict()
                for dtstrackid in dtstracks:
                    dtsfile = fileBaseName + dtstrackid + '.dts'
                    tempdtsfile = os.path.join(tempdir, dtsfile)
                    ac3file = fileBaseName + dtstrackid + '.ac3'
                    tempac3file = os.path.join(tempdir, ac3file)
                    aacfile = fileBaseName + dtstrackid + '.aac'
                    tempaacfile = os.path.join(tempdir, aacfile)
                    tcfile = fileBaseName + dtstrackid + '.tc'
                    temptcfile = os.path.join(tempdir, tcfile)

                    # get dtstrack info
                    try:
                        output = subprocess.check_output([mkvinfo, "--ui-language", "en", ford])
                    except subprocess.CalledProcessError as error:
                        print error
                        return
                    lines = output.split("\n")
                    dtstrackinfo = []
                    startcount = 0
                    for line in lines:
                        match = re.search(r'^\|( *)\+', line)
                        linespaces = startcount
                        if match:
                            linespaces = len(match.group(1))
                        if startcount == 0:
                            if "track ID for mkvmerge & mkvextract:" in line:
                                if "track ID for mkvmerge & mkvextract: " + dtstrackid in line:
                                    startcount = linespaces
                            elif "+ Track number: " + dtstrackid in line:
                                startcount = linespaces
                        if linespaces < startcount:
                            break
                        if startcount != 0:
                            dtstrackinfo.append(line)

                    # get dts language
                    dtslang = "eng"
                    for line in dtstrackinfo:
                        if "Language" in line:
                            dtslang = line.split()[-1]

                    # get ac3 track name
                    ac3name = False
                    if args.custom:
                        ac3name = args.custom
                    else:
                        for line in dtstrackinfo:
                            if "+ Name: " in line:
                                ac3name = line.split("+ Name: ")[-1]
                                ac3name = ac3name.replace("DTS", "AC3")
                                ac3name = ac3name.replace("dts", "ac3")
                                if args.stereo:
                                    ac3name = ac3name.replace("5.1", "Stereo")

                    # get aac track name
                    aacname = False
                    if args.aaccustom:
                        aacname = args.aaccustom
                    else:
                        for line in dtstrackinfo:
                            if "+ Name: " in line:
                                aacname = line.split("+ Name: ")[-1]
                                aacname = aacname.replace("DTS", "AAC")
                                aacname = aacname.replace("dts", "aac")
                                if args.aacstereo:
                                    aacname = aacname.replace("5.1", "Stereo")

                    # extract timecodes
                    tctitle = "  Extracting Timecodes  [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                    jobnum += 1
                    tccmd = [mkvextract, "timecodes_v2", ford, dtstrackid + ":" + temptcfile]
                    runcommand(tctitle, tccmd)

                    delay = False
                    if not args.test:
                        # get the delay if there is any
                        fp = open(temptcfile)
                        for i, line in enumerate(fp):
                            if i == 1:
                                delay = line
                                break
                        fp.close()

                    # extract dts track
                    extracttitle = "  Extracting DTS track  [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                    jobnum += 1
                    extractcmd = [mkvextract, "tracks", ford, dtstrackid + ':' + tempdtsfile]
                    runcommand(extracttitle, extractcmd)

                    # convert DTS to AC3
                    audio_bitrate = "640k"
                    converttitle = "  Converting DTS to AC3 [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                    jobnum += 1
                    audiochannels = 6
                    if args.stereo:
                        audiochannels = 2
                    convertcmd = [ffmpeg, "-y", "-v", "info", "-i", tempdtsfile, "-acodec", "ac3", "-ac", str(audiochannels), "-ab", audio_bitrate, tempac3file]
                    runcommand(converttitle, convertcmd)

                    if args.aac:
                        converttitle = "  Converting DTS to AAC [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                        jobnum += 1
                        audiochannels = 6
                        if args.aacstereo:
                            audiochannels = 2
                        convertcmd = [ffmpeg, "-y", "-i", tempdtsfile, "-acodec", "libfaac", "-ac", str(audiochannels), "-ab", audio_bitrate, tempaacfile]
                        runcommand(converttitle, convertcmd)
                        if not os.path.isfile(tempaacfile) or os.path.getsize(tempaacfile) == 0:
                            convertcmd = [ffmpeg, "-y", "-i", tempdtsfile, "-acodec", "libvo_aacenc", "-ac", str(audiochannels), "-ab", audio_bitrate, tempaacfile]
                            runcommand(converttitle, convertcmd)
                        if not os.path.isfile(tempaacfile) or os.path.getsize(tempaacfile) == 0:
                            convertcmd = [ffmpeg, "-y", "-i", tempdtsfile, "-acodec", "aac", "-strict", "experimental", "-ac", str(audiochannels), "-ab", audio_bitrate, tempaacfile]
                            runcommand(converttitle, convertcmd)
                        if not os.path.isfile(tempaacfile) or os.path.getsize(tempaacfile) == 0:
                            args.aac = False
                            print "ERROR: ffmpeg can't use any aac codecs. Please try to get libfaac, libvo_aacenc, or a newer version of ffmpeg with the experimental aac codec installed"

                    # Save information about current DTS track
                    dtsinfo[dtstrackid] = {
                      'dtsfile': tempdtsfile,
                      'ac3file': tempac3file,
                      'aacfile': tempaacfile,
                      'tcfile': temptcfile,
                      'lang': dtslang,
                      'ac3name': ac3name,
                      'aacname': aacname,
                      'delay': delay
                    }

                    if args.external:
                        if not args.test:
                            trackIdentifier = ''
                            if args.all_tracks and len(dtstracks) > 1:
                                trackIdentifier = '_' + dtstrackid
                            outputac3file = fileBaseName + trackIdentifier + '.ac3'
                            shutil.move(tempac3file, os.path.join(dirName, outputac3file))
                            files.append(outputac3file)
                            if args.aac:
                                outputaacfile = fileBaseName + trackIdentifier + '.aac'
                                shutil.move(tempaacfile, os.path.join(dirName, outputaacfile))
                                files.append(outputaacfile)

                if not args.external:
                    # remux
                    remuxtitle = "  Remuxing AC3 into MKV [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                    jobnum += 1
                    # Start to "build" command
                    remux = [mkvmerge]

                    comp = 'none'
                    if args.compress:
                        comp = args.compress

                    # Remove subtitles
                    if args.no_subtitles:
                        remux.append("--no-subtitles")

                    # Change the default position of the tracks if requested
                    if args.position != 'last':
                        remux.append("--track-order")
                        tracklist = []
                        if args.position == "initial":
                            totaltracks = len(dtstracks)
                            if args.aac:
                                totaltracks *= 2
                            for trackid in range(1, int(totaltracks) + 1):
                                tracklist.append('%d:0' % trackid)
                        elif args.position == "afterdts":
                            currenttrack = 0
                            for dtstrackid in dtstracks:
                                # Tracks up to the DTS track
                                for trackid in range(currenttrack, int(dtstrackid)):
                                    tracklist.append('0:%d' % trackid)
                                # DTS track
                                if not (args.nodts or args.keepdts):
                                    tracklist.append('0:%d' % int(dtstrackid))
                                # AC3 track
                                tracklist.append('1:0')
                                # AAC track
                                if args.aac:
                                    tracklist.append('2:0')
                                currenttrack = int(dtstrackid) + 1
                            # The remaining tracks
                            for trackid in range(currenttrack, len(audiotracks)):
                                tracklist.append('0:%d' % trackid)
                        remux.append(','.join(tracklist))

                    # If user doesn't want the original DTS track drop it
                    if args.nodts or args.keepdts:
                        audiotracks = [audiotrack for audiotrack in audiotracks if audiotrack not in dtstracks]
                        if len(audiotracks) == 0:
                            remux.append("--no-audio")
                        else:
                            remux.append("--audio-tracks")
                            remux.append(",".join(audiotracks))
                            for tid in audiotracks:
                                remux.append("--compression")
                                remux.append(tid + ":" + comp)

                    # Add original MKV file, set header compression scheme
                    remux.append("--compression")
                    remux.append(videotrackid + ":" + comp)
                    remux.append(ford)

                    # If user wants new AC3 as default then add appropriate arguments to command
                    if args.default:
                        remux.append("--default-track")
                        remux.append("0:1")

                    # Add parameters for each DTS track processed
                    for dtstrackid in dtstracks:

                        # Set the language
                        remux.append("--language")
                        remux.append("0:" + dtsinfo[dtstrackid]['lang'])

                        # If the name was set for the original DTS track set it for the AC3
                        if ac3name:
                            remux.append("--track-name")
                            remux.append("0:\"" + dtsinfo[dtstrackid]['ac3name'].rstrip() + "\"")

                        # set delay if there is any
                        if delay:
                            remux.append("--sync")
                            remux.append("0:" + dtsinfo[dtstrackid]['delay'].rstrip())

                        # Set track compression scheme and append new AC3
                        remux.append("--compression")
                        remux.append("0:" + comp)
                        remux.append(dtsinfo[dtstrackid]['ac3file'])

                        if args.aac:
                            # If the name was set for the original DTS track set it for the AAC
                            if aacname:
                                remux.append("--track-name")
                                remux.append("0:\"" + dtsinfo[dtstrackid]['aacname'].rstrip() + "\"")

                            # Set track compression scheme and append new AAC
                            remux.append("--compression")
                            remux.append("0:" + comp)
                            remux.append(dtsinfo[dtstrackid]['aacfile'])

                    # Declare output file
                    remux.append("-o")
                    remux.append(tempnewmkvfile)

                    runcommand(remuxtitle, remux)

                    if not args.test:
                        if args.mp4:
                            converttitle = "  Converting MKV to MP4 [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                            convertcmd = [ffmpeg, "-i", tempnewmkvfile, "-map", "0", "-vcodec", "copy", "-acodec", "copy", "-c:s", "mov_text", mp4file]
                            runcommand(converttitle, convertcmd)
                            if not args.new:
                                silentremove(ford)
                            silentremove(tempnewmkvfile)
                            files.append(fileBaseName + '.mp4')
                        else:
                            #~ replace old mkv with new mkv
                            if args.new:
                                shutil.move(tempnewmkvfile, adjacentmkvfile)
                            else:
                                tmp_ford = ford + 'tmp'
                                print 'tmp_move'
                                print tmp_ford
                                shutil.move(ford, tmp_ford)
                                print 'move'
                                print tempnewmkvfile
                                print ford
                                shutil.move(tempnewmkvfile, ford)
                                silentremove(ford + 'tmp')

                #~ clean up temp folder
                if not args.test:
                    if args.keepdts and not args.external:
                        if len(dtstracks) > 1:
                            for dtstrackid in dtstracks:
                                outputdtsfile = fileBaseName + '_' + dtstrackid + '.dts'
                                shutil.move(dtsinfo[dtstrackid]['dtsfile'], os.path.join(dirName, outputdtsfile))
                                files.append(outputdtsfile)
                        else:
                            outputdtsfile = fileBaseName + ".dts"
                            shutil.move(tempdtsfile, os.path.join(dirName, outputdtsfile))
                            files.append(outputdtsfile)
                    for dtstrackid in dtstracks:
                        silentremove(dtsinfo[dtstrackid]['dtsfile'])
                        silentremove(dtsinfo[dtstrackid]['ac3file'])
                        silentremove(dtsinfo[dtstrackid]['aacfile'])
                        silentremove(dtsinfo[dtstrackid]['tcfile'])
                    if not os.listdir(tempdir):
                        os.rmdir(tempdir)

                #~ print out time taken
                elapsed = (time.time() - starttime)
                minutes = int(elapsed / 60)
                seconds = int(elapsed) % 60
                doprint("  " + fileName + " finished in: " + str(minutes) + " minutes " + str(seconds) + " seconds\n", 1)

            return files


totalstime = time.time()

args.total_dts_files = 0
args.all_files_affected = []
for a in args.fileordir:
    for ford in glob.glob(a):
        files = []
        if os.path.isdir(ford):
            for f in os.listdir(ford):
                process(os.path.join(ford, f))
        else:
            files = process(ford)
        destdir = False
        if args.destdir:
            destdir = args.destdir
        if sab and args.sabdestdir:
            destdir = args.sabdestdir
        if destdir:
            if len(files):
                for fname in files:
                    (dirName, fileName) = os.path.split(ford)
                    destfile = os.path.join(destdir, fname)
                    origfile = os.path.join(dirName, fname)
                    if args.md5 and (find_mount_point(dirName) != find_mount_point(destdir)):
                        if os.path.exists(destfile):
                            if args.overwrite:
                                silentremove(destfile)
                                shutil.copyfile(origfile, destfile)
                                if getmd5(origfile) == getmd5(destfile):
                                    silentremove(origfile)
                                else:
                                    print "MD5's don't match."
                            else:
                                print "File " + destfile + " already exists"
                        else:
                            doprint("copying: " + origfile + " --> " + destfile + "\n", 3)
                            shutil.copyfile(origfile, destfile)
                            if getmd5(origfile) == getmd5(destfile):
                                silentremove(origfile)
                            else:
                                print "MD5's don't match."
                    else:
                        if os.path.exists(destfile):
                            if args.overwrite:
                                silentremove(destfile)
                                shutil.move(origfile, destfile)
                            else:
                                print "File " + destfile + " already exists"
                        else:
                            shutil.move(origfile, destfile)
            else:
                origpath = os.path.abspath(ford)
                destpath = os.path.join(destdir, os.path.basename(os.path.normpath(ford)))
                if args.md5 and (find_mount_point(origpath) != find_mount_point(destpath)):
                    if os.path.exists(destpath) and args.overwrite:
                        shutil.rmtree(destpath)
                    elif os.path.exists(destpath):
                        print "Directory " + destpath + " already exists"
                    else:
                        shutil.copytree(origpath, destpath)
                        if check_md5tree(origpath, destpath):
                            shutil.rmtree(origpath)
                        else:
                            print "MD5's don't match."
                else:
                    shutil.move(origpath, destpath)

doprint("Total DTS Files: " + str(args.total_dts_files) + "\n", 1)
doprint("All files that will be affected: \n " + ','.join(args.all_files_affected) + '\n')
doprint("Total Time: " + elapsedstr(totalstime) + "\n", 1)

if nzbget:
    sys.exit(POSTPROCESS_SUCCESS)
