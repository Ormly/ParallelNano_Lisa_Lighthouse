from typing import Dict, Any, List, Optional, Union
import json
import threading
import time
import os
import logging
import pathlib
import sys
import importlib

from flask import Flask, make_response
from ipcqueue.posixmq import queue, Queue
from readerwriterlock.rwlock import RWLockRead

from lighthouse.adapter import Target, Source, Adapter

app = Flask(__name__)
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lighthouse.log'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s ',
    level=logging.DEBUG
)
_logger = logging.getLogger("Lighthouse")


class ConfigFileInvalidError(Exception):
    """
    Should be raised to indicate an invalid config file structure
    """
    pass


class RESTAPITarget(Target):
    """
    Information target to be used as a REST API endpoint
    """
    def __init__(self, name: str, group_by_attr: Optional[str] = None):
        _logger.debug(msg=f"Creating new RESTAPITarget with name:{name}, group_by_attr:{group_by_attr}")
        self.name = name
        self.group_by_attr = group_by_attr
        self.persistence: Dict[Any, Any] = {}
        self.container_name = self.name[1:]
        self.response: Dict[str, Any] = {self.container_name: None}
        self.aging_time_sec = 10
        self.rw_lock = RWLockRead()

    def __call__(self, *args, **kwargs):
        response = make_response(self.get_data())
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    def get_data(self) -> Dict[Any, Any]:
        """
        copy the data that hasn't aged from storage to response
        """
        # allow multiple reads from self.persistence
        with self.rw_lock.gen_rlock():
            _logger.debug(f"Generating new response for API request {self.name}")
            return self._prepare_new_response()

    def _prepare_new_response(self):
        response = {}
        now = time.time()
        if self.group_by_attr:
            # if grouped then request contains a list of objects
            response[self.container_name] = []
            
            # only copy data records that haven't aged
            for group, data in self.persistence.items():
                if now - data["timestamp"] < self.aging_time_sec:
                    response[self.container_name].append(data)
        else:
            # when not grouped, response contains only a single object.
            if self.persistence:
                if now - self.persistence["timestamp"] < self.aging_time_sec:
                    response[self.container_name] = self.persistence
        return response

    def feed(self, data: Dict[Any, Any]):
        """

        :param data:
        :return:
        """
        # sync writing to self.persistence
        with self.rw_lock.gen_wlock():
            data["timestamp"] = time.time()
            if self.group_by_attr:
                self.persistence[data[self.group_by_attr]] = data
            else:
                self.persistence = data


class IPCQueueSource(Source):
    """
    Uses an IPC queue as an information source
    """
    def __init__(self, name: str):
        _logger.debug(f"Creating a new IPCQueueSource for POSIX queue with name {name}")
        self.ipc_queue = Queue(name)

    def get_message(self) -> Optional[Dict[Any, Any]]:
        """
        :return:
        """
        try:
            return self.ipc_queue.get_nowait()
        except queue.Empty:
            return None


class Lighthouse(threading.Thread):
    def __init__(self, config: Dict[Any, Any]):
        self._adapters: List[Adapter] = []
        self._init_adapters(config.get("ipc_rest_adapters", []))
        self._init_actions(config.get("rest_actions", []))
        self.is_running = False
        self.parent_thread = threading.current_thread()
        super().__init__()

    def _init_adapters(self, config: List[Dict[Any, Any]]):
        for adapter in config:
            # create target and an API endpoint for it
            target = RESTAPITarget(name=adapter["rest_route"], group_by_attr=adapter.get("group_by_attrib", None))
            self._create_route(target)

            source = IPCQueueSource(name=adapter["ipc_queue"])
            self._adapters.append(Adapter(name=adapter["adapter_name"], source=source, target=target))

    @staticmethod
    def _init_actions(config: List[Dict[Any, Any]]):
        for action in config:
            rest_action = RESTAction(
                name=action["action_name"],
                route=action["rest_route"],
                script_path=action["script_path"],
                argument_list=action["argument_list"]
            )
            rest_action.register()  # make this rest action operational
            # self._create_action_route(rest_action)

    @staticmethod
    def _create_route(endpoint: RESTAPITarget):
        _logger.debug(f"Adding new URL rule. name:{endpoint.name}")
        app.add_url_rule(endpoint.name, endpoint.name[1:], endpoint)

    def run(self):
        self.is_running = True
        _logger.debug("Starting Lighthouse main loop")
        while self.is_running and self.parent_thread.is_alive():
            for adapter in self._adapters:
                adapter.update()
        _logger.debug("Lighthouse main loop exiting")

    def stop(self):
        self.is_running = False


class RESTAction:
    """
    Represents a REST API call that performes some action by calling a python script stored somewhere
    with the given list of parameters. This object is responsible for registering the rest endpoint
    and invoking the actual action via the __call__ method.
    """
    def __init__(self, name: str, route: str, script_path: str, argument_list: List[Dict]):
        self.name = name
        self.route = route
        self.script_path = script_path
        self.argument_list = argument_list
        self._append_arguments_to_url()
        self._register_exception_handlers()

    def __call__(self, *args, **kwargs):
        """
        Called by Flask. Does what this action is expected to do i.e.
        invoke the required script, with the given argument, and provide the appropriate response
        """
        # try:
        # get directory path of script, add to sys.path
        script_home = os.path.dirname(self.script_path)
        sys.path.insert(0, script_home)

        # import module
        module_name = os.path.basename(self.script_path[:-3])  # remove .py suffix
        module = importlib.import_module(module_name)

        arguments = []
        for k, v in kwargs.items():
            if k in [arg["name"] for arg in self.argument_list]:
                arguments.append(v)
            else:
                raise ValueError(f"Unexpected argument provided: {k} with value: {v}")
        # run module.main() with args

        _logger.debug(msg=f"Invoking main method of module in path: {script_home}, with arguments: {arguments}")
        result = module.main(*arguments)
        _logger.debug(msg=f"Result: {result}")

        response = {
                    "status": "OK",
                    "response": result
        }
        response = make_response(response)
        response.headers["Access-Control-Allow-Origin"] = "*"

        return response

    def _register_exception_handlers(self):
        app.register_error_handler(ModuleNotFoundError, self._handle_module_not_found_error)
        app.register_error_handler(AttributeError, self._handle_module_does_comply_with_expected_format)
        app.register_error_handler(ValueError, self._handle_unexpected_argument_provided)

    @staticmethod
    def _handle_module_not_found_error(e):
        return {
            "status": "application error",
            "description": "The module specified by this call was not found in the provided path"
        }, 500

    @staticmethod
    def _handle_module_does_comply_with_expected_format(e):
        return {
            "status": "application error",
            "description": "The module specified by this call does not contain the expected function"
        }, 500

    @staticmethod
    def _handle_unexpected_argument_provided(self):
        return {
            "status": "application error",
            "description": "An unexpected argument was provided to this call"
        }, 500

    def _append_arguments_to_url(self):
        for arg in self.argument_list:
            self.route += "/<" + arg["type"] + ":" + arg["name"] + ">"

    def register(self):
        """
        makes this REST action operational by registering its URL + arguments with Flask, as well as setting
        __call__ as the called method on this endpoint
        """
        self._register_endpoint()

    def _register_endpoint(self):
        app.add_url_rule(rule=self.route, endpoint=self.name, view_func=self)


class LighthouseFactory:
    def create_from_config_file(self, filepath: str) -> Lighthouse:
        with open(filepath, 'r') as f:
            config = json.load(f)
            self._validate_config_file(config)
            _logger.setLevel(config["log_level"])
            return Lighthouse(config)

    @staticmethod
    def _validate_config_file(config: Dict):
        """
        check that config file contains all mandatory fields and raise a ConfigFileInvalidError if not
        :param config:
        :return:
        """
        if not isinstance(config, dict):
            raise ConfigFileInvalidError("Config file is not a valid dictionary")
        if "log_level" not in config.keys():
            raise ConfigFileInvalidError("log_level is missing in config file")
        if config["log_level"] not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ConfigFileInvalidError("unknown log level in config file")

        if "ipc_rest_adapters" in config.keys():
            adapters = config["ipc_rest_adapters"]
            if not isinstance(adapters, list):
                raise ConfigFileInvalidError("ipc_rest_adapters not a list")

            for adapter in adapters:
                if "adapter_name" not in adapter.keys():
                    raise ConfigFileInvalidError("adapter_name missing in adapter")
                if "ipc_queue" not in adapter.keys():
                    raise ConfigFileInvalidError(f"ipc_queue missing in adapter: {adapter['adapter_name']}")
                if "rest_route" not in adapter.keys():
                    raise ConfigFileInvalidError(f"rest_route missing in adapter: {adapter['adapter_name']}")

        if "rest_actions" in config.keys():
            actions = config["rest_actions"]

            for action in actions:
                if "action_name" not in action.keys():
                    raise ConfigFileInvalidError("action name missing in action")
                if "rest_route" not in action.keys():
                    raise ConfigFileInvalidError("rest_route missing in action")
                if "script_path" not in action.keys():
                    raise ConfigFileInvalidError("script_path missing in action")
                if "argument_list" not in action.keys():
                    raise ConfigFileInvalidError("argument_list missing in actino")
                if not isinstance(action["argument_list"], list):
                    raise ConfigFileInvalidError(
                        f"argument_list expected to be list, instead: {type(action['argument_list'])}"
                    )


factory = LighthouseFactory()
lh = factory.create_from_config_file(str(pathlib.Path(__file__).parent) + "/config.json")
lh.start()
