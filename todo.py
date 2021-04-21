#!/bin/python
import argparse
import re
import sys
from AnsiFmt import fmt
from os import environ as env
from shutil import get_terminal_size
from subprocess import run
from textwrap import wrap

desc_re = re.compile(r'^\s+(\w+.+)')
section_re = re.compile(r'^(\w+.*[^\s*])\s*:')
title_re = re.compile(r'^.*\[(.*)\]\s*(\w+.*)')


def clean_trailing_lines(li):
    if li[-1] == '\n':
        li.pop()
        clean_trailing_lines(li)


def wrap_text(string, indentation):
    return wrap(string, get_terminal_size()[0] - indentation * 2)


class Todo:
    '''
    Todo items:
    Has todo or done status
    Has title
    Has description
    '''
    def __init__(self, data: list):
        self._data = data
        assert type(data) == list, "Todo input isn't a list"
        self._title = None
        self._description = None
        self._status = None  # True -> Done. False -> Todo

    def title(self) -> str:
        if self._title is None:
            match = title_re.match(self._data[0])
            if match:
                self._title = match.group(2)
                self._status = match.group(1) == 'x'
        return self._title

    def description(self, wrap_indent_size=20) -> str:
        if self._description is None:
            lines = []
            last_index = 0
            for i, line in enumerate(self._data[1:] + ['\n']):
                if line == '\n':
                    matches = [desc_re.match(m) for m in self._data[last_index+1:i+1]]
                    string = ' '.join([_.group(1) for _ in matches if _ is not None])
                    for new_line in wrap_text(string, wrap_indent_size):
                        lines.append(new_line)
                    lines.append(line)
                    last_index = i + 1
            self._description = lines if lines != [] else self._data[1:]
        try:
            clean_trailing_lines(self._description)
        except IndexError:
            pass
        return self._description

    def status(self) -> bool:
        if self._title is None:
            match = title_re.match(self._data[0])
            if match:
                self._title = match.group(2)
                self._status = match.group(1) == 'x'
        return self._status


def parse_file(file):
    items = {'general': []}  # Dictionary containing sections
    with open(file) as f:
        data = f.readlines()
    nl_count = 0  # Count new lines, if > 2, add to general
    current_section = "general"  # State of the section\key being added to
    for line in data:
        if section_re.match(line):
            nl_count = 0
            current_section = section_re.match(line).group(1)
            if current_section not in items:
                items[current_section] = []
            continue
        elif current_section != "general" and line == '\n':
            nl_count += 1
            if nl_count == 2:
                nl_count = 0
                current_section = "general"
        if title_re.match(line):
            items[current_section].append([line])
            continue
        elif desc_re.match(line):
            nl_count = 0
            items[current_section][-1].append(line)
            continue
        elif line == '\n':
            try:
                items[current_section][-1].append(line)
            except IndexError:
                continue
    return items


def print_item(todo_item, indent_level=8, no_desc=True, do_color=1, done_color=2):
    done = todo_item.status()
    title = todo_item.title()
    description = todo_item.description(indent_level)
    if done:
        main_text = f"{' '*indent_level}{fmt.fg('', done_color)} {fmt.fg(fmt.strike(title), done_color)}"
    else:
        main_text = f"{' '*indent_level}{fmt.fg('', do_color)} {fmt.fg(title, do_color)}"
    print(main_text)
    if not no_desc:
        for line in [l.strip() for l in description]:
            text = fmt.strike(line) if done else line
            print(' '*(indent_level+1), fmt.dim(fmt.fg(text, done_color if done else do_color)))
        else:
            print()


def main():
    parser = argparse.ArgumentParser(prog='Todo')
    parser.add_argument('-l', '--todo-list', type=str, default=f"{env['HOME']}/.todo_list", help='Choose a to-do list file')
    parser.add_argument('-e', '--edit', nargs='*', type=str, default='not_set', help='Edit to-do list')
    parser.add_argument('-i', '--indent-spaces', type=int, help='Number of spaces before each line')
    parser.add_argument('-d', '--no-description', action='store_true', help='Do not print description')
    parser.add_argument('-s', '--no-section', action='store_true', help='Do not print section header')
    parser.add_argument('-c', '--color', nargs=3, default=(15, 1, 2), help='Colors for section, to-do, done')
    args = parser.parse_args()
    edit = args.edit != 'not_set'

    try:
        todo_items = parse_file(args.todo_list)
    except FileNotFoundError:
        sys.stderr.write("File not found. Edit it? (y/N)")
        edit = True if input(': ').lower() == 'y' else False
        args.edit = []
        if not edit:
            return
    finally:
        if edit:
            if args.edit == []:
                args.edit = args.todo_list
            else:
                args.edit = args.edit[0]
            run([env['EDITOR'], args.edit])
            return

    if args.indent_spaces is None and len(todo_items.keys()) == 1:
        args.indent_spaces = 1
    elif args.indent_spaces is None:
        args.indent_spaces = 8

    section_color, todo_color, done_color = args.color

    for section in todo_items.keys():
        if section != "general":
            if not args.no_section:
                print(fmt.fg(fmt.underline(fmt.bold(section)), section_color))
            for item in todo_items[section]:
                todo = Todo(item)
                print_item(todo, args.indent_spaces, args.no_description, todo_color, done_color)
    else:
        general_items = todo_items['general']
        if len(general_items) > 0:
            if len(todo_items.keys()) > 1 and not args.no_section:
                print(fmt.fg(fmt.underline(fmt.bold('General')), section_color))
            for item in general_items:
                todo = Todo(item)
                print_item(todo, args.indent_spaces, args.no_description, todo_color, done_color)


if __name__ == "__main__":
    main()
