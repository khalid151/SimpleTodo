#!/bin/env python3
import argparse
import re
import AnsiFmt as fmt
from os import environ as env
from shutil import get_terminal_size as term_size
from subprocess import run
from textwrap import wrap

search = {
    'section': re.compile(r'^(\w+.*[^\s*])\s*:'),
    'title': re.compile(r'^\s*\[\s*(x)*\s*\]\s*(\w+.*)'),
    'description': re.compile(r'^\s+(\w+.+)'),
}


def wrap_text(string: str, indentation: int) -> list:
    return wrap(string, term_size()[0] - indentation * 2)


class TodoItem:
    def __init__(self, title: str = None,
                 description: str = None,
                 status: bool = False):
        self._status = status
        self._title = title
        self._description = description

    @property
    def status(self):
        return self._status

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description


def parse_file(filepath: str) -> dict:
    items = {'general': []}  # {'section': [TodoItem]}

    with open(filepath) as f:
        data = f.readlines()

    nl_count = 0  # Count new lines, if > 2, add to general
    current_section = "general"
    # Keep track of current todo item, for parsing
    current_todo = {
        'title': None,
        'description': None,
        'status': None,
        'section': None,
    }

    for line in data:
        if search['section'].match(line):
            nl_count = 0  # Reset lines count
            current_section = search['section'].match(line).group(1)
            # initilize section if it isn't already added
            if current_section not in items:
                items[current_section] = []
            continue
        # set current section to be general if there are two blank lines
        # before the todo item
        elif current_section != "general" and line == '\n':
            nl_count += 1
            if nl_count == 2:
                nl_count = 0
                current_section = "general"
        elif search['title'].match(line):
            match = search['title'].match(line)
            if current_todo['title'] != match.group(2):
                # Add last one after task change but make sure it isn't None
                if current_todo['title'] is not None:
                    title = current_todo['title']
                    description = current_todo['description']
                    status = current_todo['status']
                    todo = TodoItem(title, description, status)
                    items[current_todo['section']].append(todo)
                # re-init
                for k in current_todo.keys():
                    current_todo[k] = None
                current_todo['title'] = match.group(2)
                current_todo['status'] = match.group(1) == 'x'
                current_todo['section'] = current_section
            continue
        elif search['description'].match(line):
            nl_count = 0
            description = search['description'].match(line).group(1)
            if current_todo['description'] is None:
                current_todo['description'] = description + '\n'
            else:
                current_todo['description'] += description
            continue
        elif line == '\n':
            try:
                current_todo['description'] += line
            except TypeError:
                continue
    else:
        if current_todo['title'] is not None:
            title = current_todo['title']
            description = current_todo['description']
            status = current_todo['status']
            todo = TodoItem(title, description, status)
            items[current_todo['section']].append(todo)

    return items


def print_item(item: TodoItem,
               indentation: int = 4,
               print_description: bool = True,
               todo_color=1,
               done_color=2,
               todo_icon: str = '',
               done_icon: str = ''):
    done = item.status
    title = item.title if not done else fmt.strike(item.title)
    description = item.description

    color = done_color if done else todo_color
    icon = done_icon if done else todo_icon

    print(fmt.fg(f"{' ' * indentation}{icon} {title}", color))

    if print_description:
        if description:
            for unwrapped in [_ for _ in description.strip().split('\n')]:
                if unwrapped == '':
                    print()
                for line in [_ for _ in wrap_text(unwrapped, indentation)]:
                    text = fmt.strike(line) if done else line
                    text = fmt.dim(fmt.fg(text, color))
                    print(' ' * (indentation + 1), text)
        print()


def main():
    try:
        default_list = env['SIMPLETODO_LIST']
    except KeyError:
        default_list = env['HOME'] + "/.todo_list"

    parser = argparse.ArgumentParser(prog='SimpleTodo')
    parser.add_argument('section', type=str, default='all', nargs='?',
                        help='Section to print')
    parser.add_argument('-l', '--todo-list', type=str, default=default_list,
                        help='Choose a todo list file')
    parser.add_argument('-e', '--edit', action='store_true',
                        help='Edit todo list')
    parser.add_argument('-d', '--no-description', action='store_true',
                        help='Description will not be printed')
    parser.add_argument('-s', '--no-section', action='store_true',
                        help='Section will not be printed')
    parser.add_argument('-i', '--indent-spaces', type=int,
                        help='Number of spaces before each line')
    parser.add_argument('-c', '--color', nargs=3, default=(15, 1, 2),
                        help='Colors for section, todo, done')

    args = parser.parse_args()

    if args.edit:
        run([env['EDITOR'], args.todo_list])
        return
    try:
        todo_items = parse_file(args.todo_list)
    except FileNotFoundError:
        print("File not found. Edit it? (y/N)")
        if input(': ').lower().startswith('y'):
            run([env['EDITOR'], args.todo_list])
            return

    section_color, todo_color, done_color = args.color

    if args.section != 'all' and args.section not in todo_items.keys():
        print("Section not found")
        return

    sections = todo_items.keys() if args.section == 'all' else [args.section]

    if args.indent_spaces is None and len(sections) == 1 or args.no_section:
        args.indent_spaces = 1
    elif args.indent_spaces is None:
        args.indent_spaces = 4

    for section in sections:
        if len(todo_items[section]) > 0:
            if not args.no_section and len(sections) > 1:
                print(fmt.fg(fmt.underline(section), section_color))
            for item in todo_items[section]:
                print_item(item,
                           args.indent_spaces,
                           not args.no_description,
                           todo_color,
                           done_color)


if __name__ == "__main__":
    main()
