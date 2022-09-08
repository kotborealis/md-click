#!/usr/bin/env python3

import pathlib
import importlib
import itertools
import os

import click

# Edit this template to change markdown output
md_base_template = """# {command_name}

{description}

**Usage:** `{usage}`

**Options:**

{options}

"""


def trim_empty_lines(data: str):
    """
    Remove empty lines from start and end of text.
    """
    def empty(x):
        return x == ""

    lines = data.splitlines()
    lines = list(itertools.dropwhile(empty, lines))
    lines = reversed(lines)
    lines = list(itertools.dropwhile(empty, lines))
    lines = reversed(lines)
    return '\n'.join(lines)


def trim_docstring(data):
    """
    Remove common indentation from documentation string.
    Example: "  Hello,\n   World!" -> "Hello,\n World!"
             Lines have common indentation of 2 spaces,
             which will be removed by this function.
    """
    lines = trim_empty_lines(data).splitlines()

    print(lines)

    common_indentation = min([
        len(list(itertools.takewhile(
            lambda x: x == ' ' or x == '\t',
            line
        ))) for line in lines if line
    ])

    return '\n'.join([line[common_indentation:] for line in lines])


def recursive_help(cmd, parent=None):
    """
    Recursively get help options from command and it's children.
    """
    ctx = click.core.Context(cmd, info_name=cmd.name, parent=parent)

    yield {
        "command": cmd,
        "help": cmd.get_help(ctx),
        "parent": parent.info_name if parent else '',
        "usage": cmd.get_usage(ctx),
        "params": cmd.get_params(ctx),
        "options": cmd.collect_usage_pieces(ctx)
    }

    commands = getattr(cmd, 'commands', {})
    for sub in commands.values():
        for helpdct in recursive_help(sub, ctx):
            yield helpdct


def format_option(opt):
    usage = ', '.join(opt.get('usage').splitlines())
    required = ' (REQUIRED)' if opt.get('required') else ''
    default_value = opt.get('default', None)

    # special case
    if default_value == os.getcwd():
        default_value = "<current directory>"

    res = f"* `{usage}`{required}: {opt.get('help') or ''}\n"

    if default_value is not None:
        res += f"  * Default value: `{default_value}`\n"

    return res


def dump_helper(base_command, docs_dir):
    """ Dumping help usage files from Click Help files into an md """
    docs_path = pathlib.Path(docs_dir)
    for helpdct in recursive_help(base_command):
        command = helpdct.get("command")
        helptxt = helpdct.get("help")
        usage = helpdct.get("usage")

        options = {
            opt.name: {
                "usage": '\n'.join(opt.opts),
                "prompt": getattr(opt, "prompt", None),
                "required": getattr(opt, "required", None),
                "default": getattr(opt, "default", None),
                "help": getattr(opt, "help", None),
                "type": str(getattr(opt, "type", None))
            }
            for opt in helpdct.get('params', [])
        }

        md_template = md_base_template.format(
            command_name=command.name,
            description=trim_docstring(command.help),
            usage=usage,
            options="".join([
                format_option(opt)
                for _, opt in options.items()
            ]),
            help=helptxt
        )

        if not docs_path.exists():
            # Create md file dir if needed
            docs_path.mkdir(parents=True, exist_ok=False)

        md_file_path = docs_path.joinpath(command.name.replace(' ', '-').lower() + '.md').absolute()

        # Create the file per each command
        with open(md_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(md_template)


@click.group()
def cli():
    pass


@cli.command('dumps')
@click.option('--baseModule', help='The base command module path to import', required=True)
@click.option('--baseCommand', help='The base command function to import', required=True)
@click.option('--docsPath', help='The docs dir path to write the md files', required=True)
def dumps(**kwargs):
    """
    # Click-md
    Create md files per each command,
    in format of `command.md`,
    under the `--docsPath` directory.
    """
    base_module = kwargs.get('basemodule')
    base_command = kwargs.get('basecommand')
    docs_path = kwargs.get('docspath')

    click.secho(f'Creating a new documents from {base_module}.{base_command} into {docs_path}',
                color='green')

    try:
        # Import the module
        module_ = importlib.import_module(base_module)
    except Exception as e:
        click.echo(f'Could not find module: {base_module}. Error: {str(e)}')
        return

    try:
        # Import the base command (group of command) function inside the module
        command_ = getattr(module_, base_command)
    except AttributeError:
        click.echo(f'Could not find command {base_command} on module {base_module}')
        return

    try:
        dump_helper(command_, docs_dir=docs_path)
        click.secho(f'Created docs under {docs_path}', color='green')
    except Exception as e:
        click.secho(f'Dumps command failed: {str(e)}', color='red')
        raise

    return


cli.add_command(cli)
cli()
