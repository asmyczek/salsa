# -*- coding: utf-8 -*-

"""
Command line for Salsa API
For details run: python -m salsa -h
"""

import argparse
import sys
from salsa import salsa


sys.tracebacklimit = 0


parser = argparse.ArgumentParser(description='Salsa - South Africa Load Shedding API')
parser.version = "Salsa v0.1"
parser.add_argument('-v', '--version',
                    action='version',
                    help='Print current API version.')
parser.add_argument('command',
                    type=str,
                    help='API command: [stage, list, find, schedule].')
parser.add_argument('-n', '--name',
                    action='store',
                    metavar='SUBURB-NAME',
                    nargs=argparse.REMAINDER,
                    type=str,
                    default=None,
                    help='Name parameter for schedule.')
parser.add_argument('-s', '--stage',
                    action='store',
                    metavar='STAGE',
                    type=int,
                    default=1,
                    choices=range(1, 5),
                    help='Stage parameter for schedule.')
parser.add_argument('-d', '--days',
                    action='store',
                    metavar='COUNT',
                    type=int,
                    default=7,
                    help='Prints schedule from today for d days.')
parser.add_argument('-b', '--block',
                    action='store',
                    metavar='BLOCK-ID',
                    type=str,
                    default=None,
                    help='Block ID for suburb and schedule query.')
args = parser.parse_args()


if __name__ == "__main__":
    if cmd := args.command:
        if cmd == 'stage':
            stage = salsa.get_stage()
            print(f'Load shedding stage {stage}' if stage > 0 else "No load shedding")
        elif cmd == 'list':
            for suburb in salsa.get_suburbs():
                print(f"{suburb['title']} - {suburb['block']}")
        elif cmd == 'find':
            for suburb in salsa.find_suburb(name=" ".join(args.name) if args.name else None,
                                            block=args.block):
                print(f"{suburb['title']} - {suburb['block']}")
        elif cmd == 'schedule':
            schedule = salsa.get_schedule(args.stage,
                                          name=" ".join(args.name) if args.name else None,
                                          block=args.block,
                                          days=args.days)
            print(f'Block: {schedule["block"]} - Stage {schedule["stage"]}')
            for s in schedule['schedule']:
                print(f"  Start: {s['start']}")
                print(f"  End:   {s['end']}")
        else:
            print(f'Invalid command {cmd}.')
