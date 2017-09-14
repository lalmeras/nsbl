# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import copy

import os
from builtins import *
from frkl import frkl
from six import string_types

# from frkl import CHILD_MARKER_NAME, DEFAULT_LEAF_NAME, DEFAULT_LEAFKEY_NAME, KEY_MOVE_MAP_NAME, OTHER_KEYS_NAME, \
    # UrlAbbrevProcessor, EnsureUrlProcessor, EnsurePythonObjectProcessor, FrklProcessor, \
    # IdProcessor, dict_merge, Frkl

# stem key for inventory
ENVS_KEY = "envs"
# meta info for groups/hosts (contains for example 'hosts' for groups)
ENV_META_KEY = "meta"
# name of the group/host
ENV_NAME_KEY = "name"
# type of the environemnt (either group or host)
ENV_TYPE_KEY = "type"
# under meta key, lists hosts of a group
ENV_HOSTS_KEY = "hosts"
# under meta key, lists sub-groups of a group, or which groups a host is member is
ENV_GROUPS_KEY = "groups"
# vars for a host/group
VARS_KEY = "vars"
# tasks for a hosts/group, used to create playbooks
TASKS_KEY = "tasks"

# meta infor for tasks (e.g. 'become')
TASKS_META_KEY = "meta"
# name of the task, can be internal or external role, or an ansible module
TASK_META_NAME_KEY = "name"
# name that the role has, used in the playbook, added automatically according to the type of task that is processed
ROLE_NAME_KEY = "role"
# the type of task
TASK_TYPE_KEY = "task-type"
# key to indicate whether a task/role should be executed with superuser privileges
TASK_BECOME_KEY = "become"
# key to tell nsbl which variable keys are valid if the type is ansible module. ansible modules don't like getting fed keys that are not related to them
TASK_ALLOWED_VARS_KEY = "allowed_vars"
# key to indicate which role dependencies should be added for the ansible environment to be created
TASK_ROLES_KEY = "task-roles"
TASK_DYN_ROLE_DETAILS = "task-dyn-role-details"
# key to indicate allowed keys for an ansible module
VAR_KEYS_KEY = "var-keys"
# name that gets used by ansible, either a module name, or a role name
TASK_NAME_KEY = "task-name"
# (optional) short description of the task
TASK_DESC_KEY = "task-desc"
# name to indicate to use the ansible 'with_items' directive
TASK_WITH_ITEMS_KEY = "with_items"
# id of the task within the task group
TASK_ID_KEY = "_task_id"
# id of the roles of the current task
ROLE_ID_KEY = "_role_id"
# id of the environment tasks are run in
ENV_ID_KEY = "_env_id"
# id of the task within a dynamic role
DYN_TASK_ID_KEY = "_dyn_task_id"
DEFAULT_KEY_KEY = "default-key"
SPLIT_KEY_KEY = "split-key"
WITH_ITEMS_KEY = "with_items"
# indicator for task type internal role (meaning, a role that is in one of the trusted role repos)
INT_ROLE_TASK_TYPE = "int_role"
# indicator for task type external role
EXT_ROLE_TASK_TYPE = "ext_role"
# indicator for task type autogenerated dynamic role (out of DYN_TASK_TYPEs)
DYN_ROLE_TYPE = "dyn_role"
# indicator for task type ansible module
TASK_TASK_TYPE = "task"
# key to indicate what the generated role should be called
ROLE_NAME_KEY = "role-name"
# filename that contains meta information for internal roles
ROLE_META_FILENAME = "meta.yml"
# path where nsbl default roles are located
DEFAULT_ROLES_PATH = os.path.join(os.path.dirname(__file__), "external", "default-roles")
# default task description filename
TASK_DESC_DEFAULT_FILENAME = "task-descs.yml"
ANSIBLE_ROLE_CACHE_DIR = os.path.expanduser("~/.cache/ansible-roles")

LOCAL_ROLE_TYPE = "local"
REMOTE_ROLE_TYPE = "remote"

NSBL_TASKS_TEMPLATE_INIT = {
    "use_environment_vars": True,
    "use_context": True
}

ID_NAME = "id"
NSBL_TASKS_ID_INIT = {
    "id_key": TASKS_META_KEY,
    "id_name": ID_NAME
}

ENV_TYPE_HOST = 'host'
ENV_TYPE_GROUP = 'group'
DEFAULT_ENV_TYPE = ENV_TYPE_GROUP

# tasks that emit 'nsbl'-specific events: nsbl_item_started, nsbl_item_ok, nsbl_item_failed
NSBLIZED_TASKS = ["install"]

DEFAULT_NSBL_TASKS_BOOTSTRAP_FORMAT = {
    frkl.CHILD_MARKER_NAME: TASKS_KEY,
    frkl.DEFAULT_LEAF_NAME: TASKS_META_KEY,
    frkl.DEFAULT_LEAFKEY_NAME: TASK_META_NAME_KEY,
    frkl.KEY_MOVE_MAP_NAME: {'*': (VARS_KEY, 'default')},
    "use_context": True
}
DEFAULT_NSBL_TASKS_BOOTSTRAP_CHAIN = [
    frkl.FrklProcessor(DEFAULT_NSBL_TASKS_BOOTSTRAP_FORMAT)
]

# bootstrap frkl processor chain for creating the inventory hosts/groups lists
NSBL_INVENTORY_BOOTSTRAP_FORMAT = {
    frkl.CHILD_MARKER_NAME: ENVS_KEY,
    frkl.DEFAULT_LEAF_NAME: ENV_META_KEY,
    frkl.DEFAULT_LEAFKEY_NAME: ENV_NAME_KEY,
    frkl.OTHER_KEYS_NAME: [VARS_KEY, TASKS_KEY],
    frkl.KEY_MOVE_MAP_NAME: VARS_KEY
}
# bootstrap chain used for creating the inventory
NSBL_INVENTORY_BOOTSTRAP_CHAIN = [
    frkl.UrlAbbrevProcessor(), frkl.EnsureUrlProcessor(), frkl.EnsurePythonObjectProcessor(),
    frkl.FrklProcessor(NSBL_INVENTORY_BOOTSTRAP_FORMAT)]

def generate_nsbl_tasks_format(task_descs, tasks_format=DEFAULT_NSBL_TASKS_BOOTSTRAP_FORMAT):
    """Utility method to populate the KEY_MOVE_MAP key for the tasks frkl."""

    result = copy.deepcopy(tasks_format)

    for task_desc in task_descs:
        if DEFAULT_KEY_KEY in task_desc[TASKS_META_KEY].keys():
            # TODO: check for duplicate keys?
            result[frkl.KEY_MOVE_MAP_NAME][task_desc[TASKS_META_KEY][TASK_META_NAME_KEY]] = "vars/{}".format(task_desc[TASKS_META_KEY][DEFAULT_KEY_KEY])

    return result

def get_default_role_repos_and_task_descs(role_repos, task_descs):

    if role_repos:
        role_repos = role_repos
    else:
        role_repos = calculate_role_repos([], use_default_roles=True)

    if task_descs:
        task_descs = task_descs
    else:
        task_descs = calculate_task_descs(None, role_repos)

    return (role_repos, task_descs)


def calculate_role_repos(role_repos, use_default_roles=True):
    """Utility method to calculate which role repos to use.

    Role repos are folders containing ansible roles, and an (optional) task
    description file which is used to translate task-names in a task config
    file into roles or ansible tasks.

    Args:
      role_repos (list): a string or list of strings of local folders containing ansible roles
      use_default_roles (bool): whether to use the default roles that come with nsbl

    Returns:
      list: a list of all local role repos to be used
    """

    if not role_repos:
        role_repos = []

    if isinstance(role_repos, string_types):
        role_repos = [role_repos]
    else:
        role_repos = role_repos

    if not role_repos:
        role_repos.append(DEFAULT_ROLES_PATH)
    elif use_default_roles:
        role_repos.insert(0, DEFAULT_ROLES_PATH)

    return role_repos

def calculate_task_descs(task_descs, role_repos=[], add_upper_case_versions=True):
    """Utility method to calculate which task descriptions to use.

    Task descriptions are yaml files that translate task-names in a task config
    into roles or ansible tasks, optionally with extra default parameters.

    If additional role_repos are provided, we will check whether each of them
    contains a file with the value of TASK_DESC_DEFAULT_FILENAME. If so, those
    will be added to the beginning of the resulting list.

    Args:
      task_descs (list): a string or list of strings of local files
      role_repos (list): a list of role repos (see 'calculate_role_repos' method)
      add_upper_case_versions (bool): if true, will add an upper-case version of every task desc that includes a meta/become = true entry

    Returns:
      list: a list of dicts of all task description configs to be used

    """

    if not task_descs:
        task_descs = []

    if isinstance(task_descs, string_types):
        task_descs = [task_descs]
    elif not isinstance(task_descs, (list, tuple)):
        raise Exception("task_descs needs to be string or list: '{}'".format(task_descs))

    if role_repos:
        repo_task_descs = []
        for repo in role_repos:
            task_desc_file = os.path.join(os.path.expanduser(repo), TASK_DESC_DEFAULT_FILENAME)
            if os.path.exists(task_desc_file):
                repo_task_descs.append(task_desc_file)

        task_descs = repo_task_descs + task_descs

    #TODO: check whether paths exist
    frkl_format = generate_nsbl_tasks_format([])
    task_desk_frkl = frkl.Frkl(task_descs, [frkl.UrlAbbrevProcessor(),
                                       frkl.EnsureUrlProcessor(),
                                       frkl.EnsurePythonObjectProcessor(),
                                       frkl.FrklProcessor(frkl_format)])

    processed_task_descs = task_desk_frkl.process()

    if add_upper_case_versions:
        result = []
        for task in processed_task_descs:
            result.append(task)
            task_become = copy.deepcopy(task)
            task_become[TASKS_META_KEY][TASK_META_NAME_KEY] = task[TASKS_META_KEY][TASK_META_NAME_KEY].upper()
            task_become[TASKS_META_KEY][TASK_BECOME_KEY] = True
            result.append(task_become)

        return result
    else:
        return processed_task_descs
