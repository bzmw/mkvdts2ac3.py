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

# Mark AC3 track as default (True, False).
default=True

# Path of ffmpeg (if not in path)
#ffmpegpath=

# Force processing when AC3 track is detected (True, False).
#force=False

# Path of mkvextract, mkvinfo and mkvmerge (if not in path)
#mkvtoolnixpath=

# Do not copy over original. Create new adjacent file (True, False).
#new=False

# Overwrite file if already there (True, False).
#overwrite=False

# Make ac3 track stereo instead of 6 channel (True, False).
#stereo=False

# Specify alternate DTS track. If it is not a DTS track it will default to the first DTS track found
#track=

# Specify alternate temporary working directory
#wd=


### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################




import sys

for arg in sys.argv: 
    print arg


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

parser.add_argument("-c", "--custom", metavar="TITLE", help="Custom AC3 track title")
parser.add_argument("-d", "--default", help="Mark AC3 track as default", action="store_true")
parser.add_argument("--destdir", metavar="DIRECTORY", help="Destination Directory")
parser.add_argument("-f", "--force", help="Force processing when AC3 track is detected", action="store_true")
parser.add_argument("--ffmpegpath", metavar="DIRECTORY", help="Path of ffmpeg")
parser.add_argument("--mkvtoolnixpath", metavar="DIRECTORY", help="Path of mkvextract, mkvinfo and mkvmerge")
parser.add_argument("--new", help="Do not copy over original. Create new adjacent file", action="store_true")
parser.add_argument("-o", "--overwrite", help="Overwrite file if already there. This only applies if destdir or sabdestdir is set", action="store_true")
parser.add_argument("-s", "--compress", metavar="MODE", help="Apply header compression to streams (See mkvmerge's --compression)", default='none')
parser.add_argument("--sabdestdir", metavar="DIRECTORY", help="SABnzbd Destination Directory")
parser.add_argument("--stereo", help="Make ac3 track stereo instead of 6 channel", action="store_true")
parser.add_argument("-t", "--track", metavar="TRACKID", help="Specify alternate DTS track. If it is not a DTS track it will default to the first DTS track found")
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

mkvinfo = "mkvinfo"
mkvmerge = "mkvmerge"
mkvextract = "mkvextract"
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

def process(fileordirectory):
    print fileordirectory
    if os.path.isdir(fileordirectory):
        doprint("    Processing dir:  " + fileordirectory + "\n", 3)
        for f in os.listdir(fileordirectory):
            process(os.path.join(fileordirectory, f))
    else:
        doprint("    Processing file: " + fileordirectory + "\n", 3)
        # check if file is an mkv file
        child = subprocess.Popen([mkvmerge, "-i", fileordirectory], stdout=subprocess.PIPE)
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
                
            print("Temp Directory: " + tempdir)

            (dirName, fileName) = os.path.split(fileordirectory)
            fileBaseName = os.path.splitext(fileName)[0]

            doprint("filename: " + fileName + "\n", 1)

            newmkvfile = fileBaseName + '.mkv'
            tempnewmkvfile = os.path.join(tempdir, newmkvfile)
            adjacentmkvfile = os.path.join(dirName, fileBaseName + '.new.mkv')
            files = []

            # get dts track id and video track id
            output = subprocess.check_output([mkvmerge, "-i", fileordirectory])
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
                    or ' audio (AAC' in line
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
                dtstracks = [dtstracks[0]]
                print dtstracks
                
                args.total_dts_files += 1
                args.all_files_affected.append(fileordirectory)

                # 3 jobs per DTS track (Extract DTS, Extract timecodes, Transcode)
                totaljobs = (3 * len(dtstracks))
                # 1 Remux+ 1
                totaljobs += 1
                jobnum = 1

                dtsinfo = dict()
                for dtstrackid in dtstracks:
                    dtsfile = fileBaseName + dtstrackid + '.dts'
                    tempdtsfile = os.path.join(tempdir, dtsfile)
                    ac3file = fileBaseName + dtstrackid + '.ac3'
                    tempac3file = os.path.join(tempdir, ac3file)
                    tcfile = fileBaseName + dtstrackid + '.tc'
                    temptcfile = os.path.join(tempdir, tcfile)

                    # get dtstrack info
                    try:
                        output = subprocess.check_output([mkvinfo, "--ui-language", "en", fileordirectory])
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
                    for line in dtstrackinfo:
                        if "+ Name: " in line:
                            ac3name = line.split("+ Name: ")[-1]
                            ac3name = ac3name.replace("DTS", "AC3")
                            ac3name = ac3name.replace("dts", "ac3")
                            if args.stereo:
                                ac3name = ac3name.replace("5.1", "Stereo")

                    # extract timecodes
                    tctitle = "  Extracting Timecodes  [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                    jobnum += 1
                    tccmd = [mkvextract, "timecodes_v2", fileordirectory, dtstrackid + ":" + temptcfile]
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
                    extractcmd = [mkvextract, "tracks", fileordirectory, dtstrackid + ':' + tempdtsfile]
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
                    
                    # Save information about current DTS track
                    dtsinfo[dtstrackid] = {
                      'dtsfile': tempdtsfile,
                      'ac3file': tempac3file,
                      'tcfile': temptcfile,
                      'lang': dtslang,
                      'ac3name': ac3name,
                      'delay': delay
                    }
                # remux
                remuxtitle = "  Remuxing AC3 into MKV [" + str(jobnum) + "/" + str(totaljobs) + "]..."
                jobnum += 1
                # Start to "build" command
                remux = [mkvmerge]

                comp = 'none'
                
                if args.compress:
                    comp = args.compress

                time.sleep(2)
                # Change the default position of the tracks so that AC3 is last
                currenttrack = 0
                remux.append("--track-order")
                tracklist = []
                for dtstrackid in dtstracks:
                    # Tracks up to the DTS track
                    for trackid in range(currenttrack, int(dtstrackid)):
                        tracklist.append('0:%d' % trackid)
                    # DTS track
                    tracklist.append('0:%d' % int(dtstrackid))
                    # AC3 track
                    tracklist.append('1:0')
                    currenttrack = int(dtstrackid) + 1
                    
                # The remaining tracks
                for trackid in range(currenttrack, len(audiotracks)):
                    tracklist.append('0:%d' % trackid)
                remux.append(','.join(tracklist))

                # Add original MKV file, set header compression scheme
                remux.append("--compression")
                remux.append(videotrackid + ":" + comp)
                remux.append(fileordirectory)

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

                # Declare output file
                remux.append("-o")
                remux.append(tempnewmkvfile)

                runcommand(remuxtitle, remux)

                if not args.test:
                    #~ replace old mkv with new mkv
                    if args.new:
                        shutil.move(tempnewmkvfile, adjacentmkvfile)
                    else:
                        tmp_fileordirectory = fileordirectory + 'tmp'
                        print 'tmp_move'
                        print tmp_fileordirectory
                        shutil.move(fileordirectory, tmp_fileordirectory)
                        print 'move'
                        print tempnewmkvfile
                        print fileordirectory
                        shutil.move(tempnewmkvfile, fileordirectory)
                        silentremove(fileordirectory + 'tmp')

               #~ clean up temp folder
                for dtstrackid in dtstracks:
                    silentremove(dtsinfo[dtstrackid]['dtsfile'])
                    silentremove(dtsinfo[dtstrackid]['ac3file'])
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
for fileordirectory in args.fileordir:
    print fileordirectory
    print os.path.isdir(fileordirectory)
    files = []
    if os.path.isdir(fileordirectory):
        for f in os.listdir(fileordirectory):
            process(os.path.join(fileordirectory, f))
    else:
        files = process(fileordirectory)
    destdir = False
    if args.destdir:
        destdir = args.destdir
    if sab and args.sabdestdir:
        destdir = args.sabdestdir
    if destdir:
        if len(files):
            for fname in files:
                (dirName, fileName) = os.path.split(fileordirectory)
                destfile = os.path.join(destdir, fname)
                origfile = os.path.join(dirName, fname)
                if os.path.exists(destfile):
                    if args.overwrite:
                        silentremove(destfile)
                        shutil.move(origfile, destfile)
                    else:
                        print "File " + destfile + " already exists"
                else:
                    shutil.move(origfile, destfile)
        else:
            origpath = os.path.abspath(fileordirectory)
            destpath = os.path.join(destdir, os.path.basename(os.path.normpath(fileordirectory)))

doprint("Total DTS Files: " + str(args.total_dts_files) + "\n", 1)
doprint("All files that will be affected: \n " + '\n'.join(args.all_files_affected) + '\n')
doprint("Total Time: " + elapsedstr(totalstime) + "\n", 1)


# wait for enter, otherwise we'll just close on exit
raw_input()