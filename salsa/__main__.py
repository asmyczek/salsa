# -*- coding: utf-8 -*-

"""
Command line for Salsa API
For details run: python -m salsa -h
"""

import argparse
from salsa import salsa

parser = argparse.ArgumentParser(description='Salsa - South Africa Load Shedding API')
parser.version = "Salsa v0.1"
parser.add_argument('-v', action='version')
parser.add_argument('-c', '--current-status',
                    action='store_true',
                    help='Get current load shedding status.')
parser.add_argument('-l', '--list-suburbs',
                    action='store_true',
                    help='List all suburbs.')
parser.add_argument('-f', '--find-suburb',
                    action='store',
                    metavar='SUBURB-NAME',
                    nargs=argparse.REMAINDER,
                    type=str,
                    default=None,
                    help='Find suburb for string.')
parser.add_argument('-b', '--schedule_by_block',
                    action='store',
                    metavar='BLOCK-ID',
                    type=str,
                    default=None,
                    help='Query schedule by block id, e.g. 3F. Set stage with -s.')
parser.add_argument('-n', '--schedule_by_name',
                    action='store',
                    metavar='SUBURB-NAME',
                    nargs=argparse.REMAINDER,
                    type=str,
                    default=None,
                    help='Query schedule by suburb name, e.g. 3F. Set stage with -s.')
parser.add_argument('-s', '--stage',
                    action='store',
                    metavar='STAGE',
                    type=int,
                    default=1,
                    choices=range(1, 5),
                    help='Schedule for load shedding stage.')
parser.add_argument('-d', '--days',
                    action='store',
                    metavar='COUNT',
                    type=int,
                    default=7,
                    help='Prints schedule from today for d days.')
args = parser.parse_args()


def get_block(block: str = None, name: str = None) -> str:
    if block:
        ublock = block.upper()
        for suburb in salsa.get_suburbs():
            if suburb['block'] == ublock:
                return ublock
        raise ValueError(f'Block {ublock} does not exist')
    elif name:
        suburbs = salsa.find_suburb(name)
        if len(suburbs) == 1:
            return suburbs[0]['block']
        raise ValueError(f'Suburb {name} does not exist' if suburbs else
                         f'Found {len(suburbs)} suburbs {name}, define one.')


def print_schedule(schedule: dict) -> None:
    print(f"- Start: {schedule['start']}")
    print(f"  End:   {schedule['end']}")


def print_schedule_for_block(block: str) -> None:
    for schedule in salsa.get_schedule_for(block, args.stage, days=args.days):
        print_schedule(schedule)


if __name__ == "__main__":
    if args.current_status:
        status = salsa.get_status()
        print(f'Load shedding stage {status}' if status > 0 else "No load shedding")
    elif args.list_suburbs:
        for suburb in salsa.get_suburbs():
            print(f"{suburb['title']} - {suburb['block']}")
    elif args.find_suburb and len(args.find_suburb) > 0:
        for suburb in salsa.find_suburb(" ".join(args.find_suburb)):
            print(f"{suburb['title']} - {suburb['block']}")
    elif args.schedule_by_block:
        print_schedule_for_block(get_block(block=args.schedule_by_block))
    elif args.schedule_by_name:
        print_schedule_for_block(get_block(name=" ".join(args.schedule_by_name)))
