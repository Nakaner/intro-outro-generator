#!/usr/bin/env python3
# vim: tabstop=4 shiftwidth=4 expandtab

import subprocess
import renderlib
import argparse
import tempfile
import shlex
import time
import sys
import os
import platform
from shutil import copyfile

# Parse arguments
parser = argparse.ArgumentParser(
    description='C3VOC Intro-Outro-Generator - Variant to use with Adobe After Effects Files',
    usage="./make-adobe-after-effects.py yourproject/ https://url/to/schedule.xml",
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('project', action="store", metavar='Project folder', type=str, help='''
    Path to your project folder with After Effects Files (intro.aep/scpt/jsx)
    ''')
parser.add_argument('schedule', action="store", metavar='Schedule-URL', type=str, nargs='?', help='''
    URL or Path to your schedule.xml
    ''')

parser.add_argument('--debug', action="store_true", default=False, help='''
    Run script in debug mode and render with placeholder texts,
    not parsing or accessing a schedule. Schedule-URL can be left blank when
    used with --debug
    This argument must not be used together with --id
    Usage: ./make-adobe-after-effects.py yourproject/ --debug
    ''')

parser.add_argument('--id', dest='ids', nargs='+', action="store", type=int, help='''
    Only render the given ID(s) from your projects schedule.
    This argument must not be used together with --debug
    Usage: ./make-adobe-after-effects.py yourproject/ --id 4711 0815 4223 1337
    ''')

parser.add_argument('--room', dest='rooms', nargs='+', action="store", type=str, help='''
    Only render the given room(s) from your projects schedule.
    This argument must not be used together with --debug
    Usage: ./make-adobe-after-effects.py yourproject/ --room "HfG_Studio" "ZKM_Vortragssaal"
    ''')

parser.add_argument('--pause', action="store_true", default=False, help='''
    Render a pause loop from the pause.aep file in the project folder.
    ''')

parser.add_argument('--force', action="store_true", default=False, help='''
    Force render if file exists.
    ''')

parser.add_argument('--no-finalize', dest='nof', action="store_true", default=False, help='''
    Skip finalize job.
    ''')

parser.add_argument('--outro', action="store_true", default=False, help='''
    Render outro from the outro.aep file in the project folder.
    ''')

parser.add_argument('--bgloop', action="store_true", default=False, help='''
    Render background loop from the bgloop.aep file in the project folder.
    ''')

args = parser.parse_args()


def headline(str):
    print("##################################################")
    print(str)
    print("##################################################")
    print()


def error(str):
    headline(str)
    parser.print_help()
    sys.exit(1)


if not args.project:
    error("The Path to your project with After Effect Files is a required argument")

if not args.debug and not args.pause and not args.outro and not args.bgloop and not args.schedule:
    error("Either specify --debug, --pause, --outro or supply a schedule")

if args.debug:
    persons = ['watz']
    events = [{
        'id': 1,
        'title': 'Eröffnungsveranstaltung',
        'subtitle': 'Easterhegg 2018',
        'persons': persons,
        'personnames': ', '.join(persons),
        'room': 'Heisenberg 1',
    }]

elif args.pause:
    events = [{
        'id': 'pause',
        'title': 'Pause Loop',
    }]

elif args.outro:
    events = [{
        'id': 'outro',
        'title': 'Outro',
    }]

elif args.bgloop:
    events = [{
        'id': 'bgloop',
        'title': 'Background Loop',
    }]

else:
    events = list(renderlib.events(args.schedule))


def describe_event(event):
    return "#{}: {}".format(event['id'], event['title'])


def event_print(event, message):
    print("{} – {}".format(describe_event(event), message))


tempdir = tempfile.TemporaryDirectory()
print('working in ' + tempdir.name)


def fmt_command(command, **kwargs):
    args = {}
    for key, value in kwargs.items():
        args[key] = shlex.quote(value)

    command = command.format(**args)
    return shlex.split(command)


def run_once(command, **kwargs):
    DETACHED_PROCESS = 0x00000008
    return subprocess.Popen(
        fmt_command(command, **kwargs),
        shell=False,
        stdin=None,
        stdout=None,
        stderr=None,
        close_fds=True,
        creationflags=DETACHED_PROCESS)


def run(command, **kwargs):
    return subprocess.check_call(
        fmt_command(command, **kwargs),
        stderr=subprocess.STDOUT,
        stdout=subprocess.DEVNULL)


def enqueue_job(event):
    event_id = str(event['id'])
    if (os.path.exists(os.path.join(args.project, event_id + '.ts')) or os.path.exists(os.path.join(args.project, event_id + '.mov'))) and not args.force:
        event_print(event, "file exist, skipping " + str(event['id']))
        return
    work_doc = os.path.join(tempdir.name, event_id + '.aep')
    script_doc = os.path.join(tempdir.name, event_id + '.jsx')
    ascript_doc = os.path.join(tempdir.name, event_id + '.scpt')
    intermediate_clip = os.path.join(tempdir.name, event_id + '.mov')

    if event_id == 'pause' or event_id == 'outro' or event_id == 'bgloop':
        copyfile(args.project + event_id + '.aep', work_doc)
        if platform.system() == 'Darwin':
            run(r'/Applications/Adobe\ After\ Effects\ CC\ 2019/aerender -project {jobpath} -comp {comp} -output {locationpath}',
                jobpath=work_doc,
                comp=event_id,
                locationpath=intermediate_clip)

        if platform.system() == 'Windows':
            run(r'C:/Program\ Files/Adobe/Adobe\ After\ Effects\ CC\ 2019/Support\ Files/aerender.exe -project {jobpath} -comp {comp} -output {locationpath}',
                jobpath=work_doc,
                comp=event_id,
                locationpath=intermediate_clip)

    else:
        with open(args.project + 'intro.jsx', 'r') as fp:
            scriptstr = fp.read()

        for key, value in event.items():
            value = str(value).replace('"', '\\"')
            scriptstr = scriptstr.replace("$" + str(key), value)

        with open(script_doc, 'w', encoding='utf-8') as fp:
            fp.write(scriptstr)

        copyfile(args.project + 'intro.aep', work_doc)

        if platform.system() == 'Darwin':
            copyfile(args.project + 'intro.scpt', ascript_doc)
            run('osascript {ascript_path} {jobpath} {scriptpath}',
                jobpath=work_doc,
                scriptpath=script_doc,
                ascript_path=ascript_doc)

            run(r'/Applications/Adobe\ After\ Effects\ CC\ 2019/aerender -project {jobpath} -comp "intro" -output {locationpath}',
                jobpath=work_doc,
                locationpath=intermediate_clip)

        if platform.system() == 'Windows':
            run_once(r'C:/Program\ Files/Adobe/Adobe\ After\ Effects\ CC\ 2019/Support\ Files/AfterFX.exe -noui {jobpath}',
                     jobpath=work_doc)
            time.sleep(15)

            run_once(r'C:/Program\ Files/Adobe/Adobe\ After\ Effects\ CC\ 2019/Support\ Files/AfterFX.exe -noui -r {scriptpath}',
                     scriptpath=script_doc)
            time.sleep(5)

            run(r'C:/Program\ Files/Adobe/Adobe\ After\ Effects\ CC\ 2019/Support\ Files/aerender.exe -project {jobpath} -comp "intro" -output {locationpath}',
                jobpath=work_doc,
                locationpath=intermediate_clip)

    return event_id


def finalize_job(job_id, event):
    event_id = str(event['id'])
    intermediate_clip = os.path.join(tempdir.name, event_id + '.mov')
    final_clip = os.path.join(os.path.dirname(args.project), event_id + '.ts')

    run('ffmpeg -y -hide_banner -loglevel error -i {input} -map 0:0 -c:v mpeg2video -q:v 2 -aspect 16:9 -map 0:1 -c:a mp2 -b:a 384k -shortest -f mpegts {output}',
    #run('ffmpeg -y -hide_banner -loglevel error -i {input} -map 0:0 -c:v mpeg2video -q:v 2 -aspect 16:9 -map 1:0 -c:a mp2 -map 2:0 -c:a mp2 -shortest -f mpegts {output}',
    #run('ffmpeg -y -hide_banner -loglevel error -i {input} -f lavfi -i anullsrc -ar 48000 -ac 2 -map 0:v -c:v mpeg2video -q:v 0 -aspect 16:9 -map 1:0 -c:a copy -map 2:0 -c:a copy -shortest -f mpegts {output}',
        input=intermediate_clip,
        output=final_clip)

    if event_id == 'pause' or event_id == 'outro' or event_id == 'bgloop':
        event_print(event, "finalized " + str(event_id) + " to " + final_clip)
    else:
        event_print(event, "finalized intro to " + final_clip)


if args.ids:
    if len(args.ids) == 1:
        print("enqueuing {} job into aerender".format(len(args.ids)))
    else:
        print("enqueuing {} jobs into aerender".format(len(args.ids)))
else:
    if len(events) == 1:
        print("enqueuing {} job into aerender".format(len(events)))
    else:
        print("enqueuing {} jobs into aerender".format(len(events)))

for event in events:
    if args.ids and event['id'] not in args.ids:
        continue

    if args.rooms and event['room'] not in args.rooms:
        print("skipping room %s (%s)" % (event['room'], event['title']))
        continue

    event_print(event, "enqueued as " + str(event['id']))

    job_id = enqueue_job(event)
    if not job_id:
        event_print(event, "job was not enqueued successfully, skipping postprocessing")
        continue

    if not args.nof:
        event_print(event, "finalizing job")
        finalize_job(job_id, event)
    else:
        event_id = str(event['id'])
        event_print(event, "skipping finalizing job")
        if platform.system() == 'Windows':
            intermediate_clip = os.path.join(tempdir.name, event_id + '.avi')
            final_clip = os.path.join(os.path.dirname(args.project), event_id + '.avi')
        else:
            intermediate_clip = os.path.join(tempdir.name, event_id + '.mov')
            final_clip = os.path.join(os.path.dirname(args.project), event_id + '.mov')
        copyfile(intermediate_clip, final_clip)
        event_print(event, "copied intermediate clip to " + final_clip)

print('all done, cleaning up ' + tempdir.name)
tempdir.cleanup()
