# -*- coding: utf-8 -*-

# python 3 compatibility
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import pprint
import shutil
from builtins import *

from cookiecutter.main import cookiecutter
from future.builtins.disabled import *
from jinja2 import Environment, PackageLoader

import yaml
from frkl import frkl

from .defaults import *
from .exceptions import NsblException

DEFAULT_TASKS_PRE_CHAIN = [frkl.UrlAbbrevProcessor(), frkl.EnsureUrlProcessor(), frkl.EnsurePythonObjectProcessor()]

def to_nice_yaml(var):
    """util function to convert to yaml in a jinja template"""
    return yaml.safe_dump(var, default_flow_style=False)

def check_role_desc(role_name, role_repos=[]):
    """Utility function to return the local path of a provided role name.

    If the input is a path, and that path exists on the local system, that path is returned.
    Otherwise all role repos will be checked whether they contain a role with the provided name, and if that
    is the case, that local path will be returned.

    Args:
      role_name: the path to or name of the role
      role_repos: all role repositories to check
    Returns:
    dict: a dictionary with the 'url' key being the found path
    """

    if isinstance(role_name, string_types):

        version = None
        src = None
        if os.path.exists(role_name):
            src = role_name
            name = os.path.basename(role_name)
            role_type = LOCAL_ROLE_TYPE
        else:
            for repo in role_repos:
                path = os.path.join(os.path.expanduser(repo), role_name)
                if os.path.exists(path):
                    src = path
                    name = role_name
                    role_type = LOCAL_ROLE_TYPE
                    break

            if not src:
                src = role_name
                role_type = REMOTE_ROLE_TYPE
                if "." in role_name and "/" in role_name:
                    name = role_name.split("/")[-1]
                else:
                    name = role_name.split(".")[-1]

    elif not isinstance(role_name, dict):
        raise NsblException("Type for role needs to be either string or dict: {}".format(role_name))
    else:
        name = role_name.get("name", None)
        src = role_name.get("src", None)
        version = role_name.get("version", None)

        if not name and not src:
            raise NsblException("Role doesn't specify 'name' nor 'src', can't figure out what to do: {}".format(role_name))
        elif not name:
            if os.path.exists(src):
                name = os.path.basename(src)
                role_type = LOCAL_ROLE_TYPE
            else:
                role_type = REMOTE_ROLE_TYPE
                if "." in src and "/" in src:
                    name = src.split("/")[-1]
                else:
                    name = src.split(".")[-1]
        elif not src:
            if os.path.exists(name):
                src = name
                name = os.path.basename(src)
                role_type = LOCAL_ROLE_TYPE
            else:
                role_type = REMOTE_ROLE_TYPE
                src = name
                if "." in src and "/" in src:
                    name = src.split("/")[-1]
                else:
                    name = src.split(".")[-1]
        else:
            if os.path.exists(src):
                role_type = LOCAL_ROLE_TYPE
            else:
                role_type = REMOTE_ROLE_TYPE

    if src.startswith(DYN_ROLE_TYPE):
        role_type = DYN_ROLE_TYPE

    result = {"name": name, "src": src, "type": role_type}
    if version:
            result["version"] = version


    return result

def _add_role_check_duplicates(all_roles, new_role):
    """Adds a new role only if it isn't already in the list of all roles.

    Throws an exception if two roles with the same name but different details exist.

    Args:
      all_roles (list): all current roles
      new_role (dict): new role to add
    """

    new_role_name = new_role["name"]
    new_role_src = new_role["src"]
    new_role_version = new_role.get("version", None)

    match = False
    for role in all_roles:
        role_name = role["name"]
        src = role["src"]
        version = role.get("version")

        if new_role_name != role_name:
            continue

        match = True
        if new_role_src != src:
            raise NsblException("Two roles with the same name ('{}') but different 'src' details: {} <-> {}".format(role_name, new_role, role))
        if new_role_version != version:
            if new_role_version == None:
                continue
            elif version == None:
                role["version"] = new_role_version
            else:
                raise NsblException("Two roles with the same name ('{}') but different 'version' details: {} <-> {}".format(role_name, new_role_version, version))

    if not match:
        all_roles.append(new_role)

def add_roles(all_roles, role_obj, role_repos=[]):
    """ TODO: desc

    Args:
      all_roles (list): a list of all roles
      role_obj (object): a string (role_name) or dict (roles) or list (role_names/-details)
      role_repos (list): list of local role repos to check

    Returns:
    dict: merged roles
    """

    if isinstance(role_obj, dict):
        if "src" not in role_obj.keys():
            if "name" in role_obj.keys():
                temp = check_role_desc(role_obj, role_repos)
                _add_role_check_duplicates(all_roles, temp)
            else:
                # raise NsblException("Neither 'src' nor 'name' keys in role description, can't parse: {}".format(role_obj))
                for role_name, role_details in role_obj.items():
                    if isinstance(role_details, dict):
                        if "name" in role_details.keys():
                            raise NsblException("Role details can't contain 'name' key, name already provided as key of the parent dict: {}".format(role_obj))
                        role_details["name"] = role_name
                        temp = check_role_desc(role_details, role_repos)
                        _add_role_check_duplicates(all_roles, temp)
                    elif isinstance(role_details, string_types):
                        temp = check_role_desc({"src": role_details, "name": role_name}, role_repos)
                        _add_role_check_duplicates(all_roles, temp)
                    else:
                        raise NsblException("Role description needs to be either string or dict: {}".format(role_details))
        else:
            temp = check_role_desc(role_obj, role_repos)
            _add_role_check_duplicates(all_roles, temp)
    elif isinstance(role_obj, string_types):
        temp = check_role_desc(role_obj, role_repos)
        _add_role_check_duplicates(all_roles, temp)
    elif isinstance(role_obj, (list, tuple)):
        for role_obj_child in role_obj:
            add_roles(all_roles, role_obj_child, role_repos)
    else:
        raise NsblException("Role description needs to be either a list of strings or a dict. Value '{}' is not valid.".format(role_obj))

def get_internal_role_path(role, role_repos=[]):
    """Resolves the local path to the (internal) role with the provided name.

    Args:
      role (str): string or dict of the role, can be either a name of a subdirectory in one of the role_repos, or a path
      role_repos (list): role repos to check whether one of them contains the role name as first level directory
    """

    if isinstance(role, string_types):
        url = role
    elif isinstance(role, dict):
        url = role["src"]
    else:
        raise NsblException("Type '{}' not supported for role description: {}".format(type(role), role))

    if os.path.exists(url):
        return url

    for repo in role_repos:
        path = os.path.join(os.path.expanduser(repo), url)
        if os.path.exists(path):
            return path

    return False

class NsblTasks(frkl.FrklCallback):

    def create(config, role_repos, task_descs, env_name=None, env_id=None, meta={}, pre_chain=DEFAULT_TASKS_PRE_CHAIN):

        role_repos, task_descs = get_default_role_repos_and_task_descs(role_repos, task_descs)

        init_params = {}
        if role_repos:
            init_params["role_repos"] = role_repos
        if task_descs:
            init_params["task_descs"] = task_descs

        if env_name:
            init_params["env_name"] = env_name
        if env_id:
            init_params["env_id"] = env_id
        if meta:
            init_params["meta"] = meta

        task_format = generate_nsbl_tasks_format(task_descs)
        chain = pre_chain + [FrklProcessor(task_format), NsblTaskProcessor(init_params), NsblDynamicRoleProcessor(init_params)]
        tasks = NsblTasks(init_params)

        tasks_frkl = Frkl(config, chain)
        tasks_frkl.process(tasks)

        return tasks
    create = staticmethod(create)

    def __init__(self, init_params=None):
        super(NsblTasks, self).__init__(init_params)

        self.roles = []
        self.all_ansible_roles = []
        # whether this play contains external roles
        self.ext_roles = False

    def validate_init(self):

        role_repos = self.init_params.get("role_repos", None)
        task_descs = self.init_params.get("task_descs", None)

        role_repos, task_descs = get_default_role_repos_and_task_descs(role_repos, task_descs)

        self.env_name = self.init_params.get("env_name", "localhost")
        self.env_id = self.init_params["env_id"]

        self.meta = self.init_params.get("meta", {})
        # self.vars = self.init_params.get("vars", {})

        return True

    def get_role(self, role_id):

        for role in self.roles:
            if role.role_id == role_id:
                return role

        return None

    def get_role_names(self):

        names = [role.role_name for role in self.roles]
        return names

    def render_playbook(self, playbook_dir, playbook_name=None, add_ids=True):

        if not os.path.exists(playbook_dir):
            os.makedirs(playbook_dir)

        jinja_env = Environment(loader=PackageLoader('nsbl', 'templates'))
        jinja_env = Environment(loader=PackageLoader('nsbl', 'templates'))
        jinja_env.filters['to_nice_yaml'] = to_nice_yaml

        template = jinja_env.get_template('playbook.yml')
        output_text = template.render(groups=self.env_name, roles=self.roles, meta=self.meta, env_id=self.env_id, add_ids=add_ids)

        if not playbook_name:
            playbook_name = "play_{}_{}.yml".format(self.env_name, self.env_id)
            # else:
                # playbook_name = "play_{}.yml".format(self.env_name)
            playbook_file = os.path.join(playbook_dir, playbook_name)

        with open(playbook_file, "w") as text_file:
            text_file.write(output_text)

        return playbook_name

    def render_roles(self, role_base_dir):

        jinja_env = Environment(loader=PackageLoader('nsbl', 'templates'))
        roles_requirements_file = os.path.join(role_base_dir, "roles_requirements.yml")

        if not os.path.exists(role_base_dir):
            os.makedirs(role_base_dir)

        for role in self.all_ansible_roles:
            role_type = role["type"]
            src = role["src"]
            name = role["name"]
            version = role.get("version", None)

            if role_type == LOCAL_ROLE_TYPE:
                target = os.path.join(role_base_dir, "internal", name)
                shutil.copytree(src, target)
            elif role_type == REMOTE_ROLE_TYPE:
                template = jinja_env.get_template('external_role.yml')
                output_text = template.render(role=role)
                with open(roles_requirements_file, "a") as myfile:
                    myfile.write(output_text)
            elif role_type == DYN_ROLE_TYPE:
                role_id = int(src.split("_")[-1])
                task_role = self.get_role(role_id)
                target_folder = os.path.join(role_base_dir, "dynamic")
                task_role.create_role(target_folder)
            else:
                raise NsblException("Role type '{}' not valid".format(role_type))

    def callback(self, role):

        self.roles.append(role)
        for r in role.roles:
            if r["type"] == REMOTE_ROLE_TYPE:
                self.ext_roles = True

        add_roles(self.all_ansible_roles, role.roles)

    def result(self):

        return self

    def get_lookup_dict(self):

        result = {}
        for role in self.roles:

            id = role.role_id
            result[id] = role.get_lookup_dict()

        return result

    def __repr__(self):

        return "NsblTasks(env_id='{}', env_name='{}', role_names={})".format(self.env_id, self.env_name, self.get_role_names())


class NsblTaskProcessor(frkl.ConfigProcessor):
    """Processor to take a list of (unfrklized) tasks, and frklizes (expands) the data.

    In particular, this extracts roles and tags them with their types.
    """

    def validate_init(self):

        self.role_repos = self.init_params.get('role_repos', [])
        if not self.role_repos:
            self.role_repos = calculate_role_repos([], use_default_roles=True)
        self.task_descs = self.init_params.get('task_descs', [])
        if not self.task_descs:
            self.task_descs = calculate_task_descs(None, self.role_repos)
        return True

    def process_current_config(self):


        new_config = self.current_input_config
        meta_task_name = new_config[TASKS_META_KEY][TASK_META_NAME_KEY]

        meta_roles = []
        add_roles(meta_roles, new_config[TASKS_META_KEY].get(TASK_ROLES_KEY, {}), self.role_repos)
        meta_role_names = [role["name"] for role in meta_roles]

        for task_desc in self.task_descs:

            task_desc_name = task_desc.get(TASKS_META_KEY, {}).get(TASK_META_NAME_KEY, None)

            if not task_desc_name == meta_task_name:
                continue

            new_config = frkl.dict_merge(task_desc, new_config, copy_dct=True)

        task_name = new_config.get(TASKS_META_KEY, {}).get(TASK_NAME_KEY, None)
        if not task_name:
            task_name = meta_task_name
            new_config[TASKS_META_KEY][TASK_NAME_KEY] = task_name

        task_type = new_config.get(TASKS_META_KEY, {}).get(TASK_TYPE_KEY, None)
        roles = new_config.get(TASKS_META_KEY, {}).get(TASK_ROLES_KEY, {})
        task_roles = []
        add_roles(task_roles, roles, self.role_repos)
        task_role_names = [role["name"] for role in task_roles]
        new_config[TASKS_META_KEY][TASK_ROLES_KEY] = task_roles

        int_role_path = get_internal_role_path(task_name, self.role_repos)

        if task_type in [INT_ROLE_TASK_TYPE, EXT_ROLE_TASK_TYPE]:
            if task_name not in task_role_names and task_name not in meta_role_names and not int_role_path:
                    raise NsblException("Task name '{}' not found among role names, but task type is '{}'. This is invalid.".format(task_name, task_type))
        elif not task_type == TASK_TASK_TYPE:
            if int_role_path:
                task_type = INT_ROLE_TASK_TYPE
                add_roles(task_roles, task_name, self.role_repos)
            elif task_name in task_role_names or task_name in meta_role_names:
                task_type = EXT_ROLE_TASK_TYPE
            else:
                task_type = TASK_TASK_TYPE

            new_config[TASKS_META_KEY][TASK_TYPE_KEY] = task_type

        else:
            raise NsblException("Task type needs to be either '{}', '{}' or '{}': {}".format(EXT_ROLE_TASK_TYPE, INT_ROLE_TASK_TYPE, TASK_TASK_TYPE, new_config))

        if VARS_KEY not in new_config.keys():
            new_config[VARS_KEY] = {}

        if task_type == TASK_TASK_TYPE:
            # in case this is a normal task, we need to make sure not to 'forward' vars that the task doesn't accept
            if VAR_KEYS_KEY not in new_config[TASKS_META_KEY].keys() or new_config[TASKS_META_KEY][VAR_KEYS_KEY] == '*':
                new_config[TASKS_META_KEY][VAR_KEYS_KEY] = list(new_config.get(VARS_KEY, {}).keys())

        split_key = new_config[TASKS_META_KEY].get(SPLIT_KEY_KEY, None)
        if split_key:
            splitting = True
        else:
            splitting = False

        if splitting:
            if split_key and isinstance(split_key, string_types):
                split_key = [VARS_KEY] + split_key.split("/")

            split_value = new_config
            for split_token in split_key:
                if not isinstance(split_value, dict):
                    raise NsblException("Can't split config value using split key '{}': {}".format(split_key, new_config))
                split_value = split_value.get(split_token, None)
                if not split_value:
                    break

            if split_value and isinstance(split_value, (list, tuple)):

                for item in split_value:
                    item_new_config = copy.deepcopy(new_config)
                    temp = item_new_config
                    for token in split_key[:-1]:
                        temp = temp[token]

                    temp[split_key[-1]] = item

                    yield item_new_config

            else:
                yield new_config
        else:
            yield new_config


class NsblRole(object):

    def __init__(self, meta_dict, vars_dict, role_id):
        self.meta_dict = meta_dict
        self.vars_dict = vars_dict
        self.role_id = role_id
        self.tasks = []

        self.name = self.meta_dict[TASK_META_NAME_KEY]
        self.role_name = self.meta_dict[TASK_NAME_KEY]
        self.roles = self.meta_dict.get(TASK_ROLES_KEY, {})

    def get_vars(self):

        return self.vars_dict

    def get_lookup_dict(self):

        return self.details()

    def details(self):

        return {
            TASK_META_NAME_KEY: self.name,
            TASK_NAME_KEY: self.role_name,
            "role_type": self.role_type,
            "role_id": self.role_id,
            TASK_ROLES_KEY: self.roles,
            TASKS_META_KEY: self.meta_dict,
            VARS_KEY: self.vars_dict
        }

    def get_meta(self):

        return self.meta_dict

    def __repr__(self):

        return "NsblRole(name={}, role_name={}, type={}, role_id={})".format(self.name, self.role_name, self.role_type, self.role_id)


class NsblInternalRole(NsblRole):

    def __init__(self, meta_dict, vars_dict, role_id):

        super(NsblInternalRole, self).__init__(meta_dict, vars_dict, role_id)
        self.role_type = INT_ROLE_TASK_TYPE


class NsblExternalRole(NsblRole):

    def __init__(self, meta_dict, vars_dict, role_id):

        super(NsblExternalRole, self).__init__(meta_dict, vars_dict, role_id)
        self.role_type = EXT_ROLE_TASK_TYPE


class NsblDynRole(NsblRole):

    def __init__(self, tasks, role_id, role_repos={}):
        self.tasks = tasks
        self.role_id = role_id
        self.role_type = DYN_ROLE_TYPE
        self.role_repos = role_repos
        self.role_name = self.tasks[0][TASKS_META_KEY][ROLE_NAME_KEY]
        self.roles = []
        self.meta_dict = {}
        self.vars_dict = {}
        self.task_names = []
        self.parse_tasks()
        self.name = self.role_name
        add_roles(self.roles, {"src": "{}_{}".format(DYN_ROLE_TYPE, self.role_id), "name": self.role_name})

    def __repr__(self):
        return "NsblRole(name={}, role_name={}, type={}, role_id={}, task_names={})".format(self.name, self.role_name, self.role_type, self.role_id, self.task_names)


    def get_lookup_dict(self):

        result = self.details()
        result[TASKS_KEY] = {}
        for task in self.tasks:
            id = task[TASKS_META_KEY][DYN_TASK_ID_KEY]
            result[TASKS_KEY][id] = task

        return result


    def parse_tasks(self):

        for idx, t in enumerate(self.tasks):
            task_id = "{}_{}".format(self.role_name, idx)
            t[TASKS_META_KEY][DYN_TASK_ID_KEY] = task_id
            self.task_names.append(t[TASKS_META_KEY][TASK_META_NAME_KEY])
            add_roles(self.roles, t[TASKS_META_KEY].get(TASK_ROLES_KEY, self.role_repos))
            if TASK_DESC_KEY not in t[TASKS_META_KEY].keys():
                t[TASKS_META_KEY][TASK_DESC_KEY] = t[TASKS_META_KEY][TASK_META_NAME_KEY]
            for key, value in t.get(VARS_KEY, {}).items():
                self.vars_dict["{}_{}".format(task_id, key)] = value


    def create_role(self, target_folder):

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        role_template_local_path = os.path.join(os.path.dirname(__file__), "external", "ansible-role-template")
        # cookiecutter doesn't like input lists, so converting to dict
        tasks = {}

        for task in self.tasks:
            task_name = task[TASKS_META_KEY][DYN_TASK_ID_KEY]
            tasks[task_name] = task
            if VARS_KEY not in task.keys():
                task[VARS_KEY] = {}
            if VAR_KEYS_KEY not in task[TASKS_META_KEY].keys() or task[TASKS_META_KEY][VAR_KEYS_KEY] == '*':
                task[TASKS_META_KEY][VAR_KEYS_KEY] = list(task.get(VARS_KEY, {}).keys())
            else:
                for key in task.get(VARS_KEY, {}).keys():
                    task[TASKS_META_KEY][VAR_KEYS_KEY].append(key)

            # make var_keys items unique
            task[TASKS_META_KEY][VAR_KEYS_KEY] = list(set(task[TASKS_META_KEY][VAR_KEYS_KEY]))
            if WITH_ITEMS_KEY in task[TASKS_META_KEY].keys():
                with_items_key = task[TASKS_META_KEY][WITH_ITEMS_KEY]

                # if with_items_key not in task[VARS_KEY]:
                    # raise NsblException("Can't iterate over variable '{}' using with_items because key does not exist in: {}".format(task[TASK_NAME_KEY][VARS_KEY]))

                # task[TASKS_META_KEY][VARS_KEY] = "item"

        role_dict = {
            "role_name": self.role_name,
            "tasks": tasks,
            "dependencies": ""
        }

        current_dir = os.getcwd()
        os.chdir(target_folder)

        cookiecutter(role_template_local_path, extra_context=role_dict, no_input=True)
        os.chdir(current_dir)


class NsblDynamicRoleProcessor(frkl.ConfigProcessor):
    """Processor to extract and pre-process single tasks to merge them into one or several roles later on."""

    def __init__(self, init_params=None):

        super(NsblDynamicRoleProcessor, self).__init__(init_params)
        self.current_tasks = []
        self.current_role_name = None
        self.role_id = 0

    def validate_init(self):

        self.role_repos = self.init_params.get('role_repos', [])
        if not self.role_repos:
            self.role_repos = calculate_role_repos([], use_default_roles=True)
        return True

    def handles_last_call(self):

        return True

    def process_current_config(self):

        if not self.last_call:
            new_config = self.current_input_config


            if new_config[TASKS_META_KEY][TASK_TYPE_KEY] == TASK_TASK_TYPE:

                role_name = new_config[TASKS_META_KEY].get(ROLE_NAME_KEY, None)
                if not role_name:
                    if not self.current_role_name:
                        self.current_role_name = "{}_{}".format(DYN_ROLE_TYPE, self.role_id)
                    role_name = self.current_role_name
                    new_config[TASKS_META_KEY][ROLE_NAME_KEY] = role_name
                    self.current_tasks.append(new_config)
                    yield None
                else:
                    if role_name != self.current_role_name:
                        if self.current_tasks:
                            dyn_role = NsblDynRole(self.current_tasks, self.role_id, self.role_repos)
                            self.current_tasks = [new_config]
                            self.current_role_name = role_name
                            yield dyn_role
                            self.role_id += 1
                        else:
                            self.current_role_name = role_name
                            self.current_tasks.append(new_config)
                            yield None
                    else:
                        self.current_tasks.append(new_config)
                        yield None

            elif new_config[TASKS_META_KEY][TASK_TYPE_KEY] in [INT_ROLE_TASK_TYPE, EXT_ROLE_TASK_TYPE]:
                if len(self.current_tasks) > 0:
                    dyn_role = NsblDynRole(self.current_tasks, self.role_id, self.role_repos)
                    self.role_id += 1
                    self.current_tasks = []
                    self.current_role_name = None
                    yield dyn_role
                if new_config[TASKS_META_KEY][TASK_TYPE_KEY] == INT_ROLE_TASK_TYPE:
                    role = NsblInternalRole(new_config[TASKS_META_KEY], new_config.get(VARS_KEY, {}), self.role_id)
                    self.current_role_name = None
                    yield role
                else:
                    role = NsblExternalRole(new_config[TASKS_META_KEY], new_config.get(VARS_KEY, {}), self.role_id)
                    self.current_role_name = None
                    yield role
                self.role_id += 1
            else:
                raise NsblException("Task type needs to be either '{}', '{}' or '{}': {}".format(TASK_TASK_TYPE, EXT_ROLE_TASK_TYPE, INT_ROLE_TASK_TYPE, new_config[TASKS_META_KEY][TASK_TYPE_KEY]))


        else:
            if len(self.current_tasks) > 0:
                role = NsblDynRole(self.current_tasks, self.role_id, self.role_repos)
                yield role
            else:
                yield None
