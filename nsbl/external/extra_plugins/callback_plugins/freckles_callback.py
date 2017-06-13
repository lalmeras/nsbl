from __future__ import absolute_import, division, print_function

import datetime
import decimal
import json
import pprint
import uuid

from six import string_types
import ansible
from ansible.executor.task_result import TaskResult
from ansible.plugins.callback import CallbackBase
from ansible.playbook.task_include import TaskInclude
from ansible import constants as C

__metaclass__ = type

class CallbackModule(CallbackBase):
    """
    Forward task, play and result objects to freckles.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'freckles_callback'
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self, *args, **kwargs):
        super(CallbackModule, self).__init__(*args, **kwargs)
        self.task = None
        self.play = None

    def get_task_detail(self, detail_key):

        if not self.task:
            return None
        temp = self.task.serialize()
        for level in detail_key.split("."):
            temp = temp.get(level, {})

        return temp

    def get_task_name(self):

        name = self.get_task_detail("name")
        return name

    def get_env_id(self):

        #pprint.pprint(self.task.serialize())
        #pprint.pprint(self.play.serialize())

        id = self.get_task_detail("role._role_params._env_id")

        if isinstance(id, int):
            return id
        else:
            return None


    def get_task_id(self):

        # pprint.pprint(self.task.serialize())
        # pprint.pprint(self.play.serialize())

        id = self.get_task_detail("role._role_params._task_id")

        if isinstance(id, int):
            return id
        else:
            return None

        # parents = self.get_task_detail("role._parents")
        # if  parents:
            # for p in parents:
                # if "freck_id" in p["_role_params"].keys():

                    # return p["_role_params"]["freck_id"]


    def print_output(self, category, result, item=None):

        output = {}
        output["category"] = category
        temp = self.get_task_id()
        output["_task_id"] = temp
        temp = self.get_env_id()
        output["_env_id"] = temp

        temp = self.get_task_name()
        if isinstance(temp, string_types) and temp.startswith("_dyn_task"):
            output["dyn_task"] = True
            output["_dyn_task_id"] = temp
        else:
            output["dyn_task"] = False

        if item:
            output["item"] = item

        action = self.get_task_detail("action")
        if not action:
            action = "n/a"
        output["action"] = action

        name = self.get_task_detail("name")
        if name:
            output["name"] = name

        output["ignore_errors"] = self.get_task_detail("ignore_errors")

        # output["task"] = self.task.serialize()
        # output["play"] = self.play.serialize()
        if category == "play_start" or category == "task_start":
            output["result"] = {}
        else:
            output["result"] = result._result
            msg = output["result"].get("msg", None)
            if msg:
                output["msg"] = msg
            else:
                msg = output["result"].get("stderr", None)
                if msg:
                    output["msg"] = msg
            if result._result.get('changed', False):
                status = 'changed'
            else:
                status = 'ok'
            output["status"] = status

            skipped = result._result.get('skipped', False)
            output["skipped"] = skipped

        print(json.dumps(output))


    def v2_runner_on_ok(self, result, **kwargs):

        self.print_output("ok", result)

    def v2_runner_on_failed(self, result, **kwargs):

        self.print_output("failed", result)

    def v2_runner_on_unreachable(self, result, **kwargs):

        self.print_output("unreachable", result)

    def v2_runner_on_skipped(self, result, **kwargs):

        self.print_output("skipped", result)

    def v2_playbook_on_play_start(self, play):
        self.play = play
        self.print_output("play_start", None)

    def v2_playbook_on_task_start(self, task, is_conditional):

        self.task = task
        self.print_output("task_start", None)

    def v2_runner_item_on_ok(self, result):

        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if isinstance(result._task, TaskInclude):
            return
        elif result._result.get('changed', False):
            status = 'changed'
        else:
            status = 'ok'

        item = self._get_item(result._result)

        self.print_output("item_ok", result, item)

    def v2_runner_item_on_failed(self, result):
        item = self._get_item(result._result)
        self.print_output("item_failed", result, item)

    def v2_runner_item_on_skipped(self, result):
        item = self._get_item(result._result)
        self.print_output("item_skipped", result, item)

    def v2_on_any(self, *args, **kwargs):

        # pprint.pprint(args)
        pass
