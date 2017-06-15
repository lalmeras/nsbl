# -*- coding: utf-8 -*-

import os
import pprint
import click
import sys
from .nsbl import NsblInventory, Nsbl, NsblRunner
from .env_creator import AnsibleEnvironment, NsblCreateException
from . import __version__ as VERSION
import yaml
import json
import frkl
import click_log

@click.command()
@click.option('--version', help='the version of frkl you are using', is_flag=True)
@click.option('--role-repo', '-r', help='path to a local folder containing ansible roles', multiple=True)
@click.option('--task-desc', '-t', help='path to a local task description yaml file', multiple=True)
@click.option('--stdout-callback', '-c', help='name of or path to callback plugin to be used as default stdout plugin', default="nsbl_internal")
@click.option('--target', '-t', help="target output directory of created ansible environment, defaults to 'nsbl_env' in the current directory", default="nsbl_env")
@click.option('--static/--dynamic', default=True, help="whether to render a dynamic inventory script using the provided config files instead of a plain ini-type config file and group_vars and host_vars folders, default: static")
@click.option('--force/--no-force', help="delete potentially existing target directory", default=True)
@click.argument('config', required=True, nargs=-1)
@click_log.simple_verbosity_option()
@click_log.init("nsbl")
def cli(version, role_repo, task_desc, stdout_callback, target, static, force, config):
    """Console script for nsbl"""

    if version:
        click.echo(VERSION)
        sys.exit(0)

    nsbl_obj = Nsbl(config, task_desc, role_repo)

    runner = NsblRunner(nsbl_obj)

    runner.run(target, static, force, "", stdout_callback)


def output(python_object, format="raw", pager=False):

    if format == 'yaml':
        output = yaml.safe_dump(python_object, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    elif format == 'json':
        output = json.dumps(python_object, sort_keys=4, indent=4)
    elif format == 'raw':
        output = str(python_object)
    elif format == 'pformat':
        output = pprint.pformat(python_object)

    if pager:
        click.echo_via_pager(output)
    else:
        click.echo(output)

