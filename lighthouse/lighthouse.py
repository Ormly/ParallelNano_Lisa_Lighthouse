from typing import Dict, Any, List, Optional, Union
import json
import threading
import time
import os
import logging

from flask import Flask
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
        self.response: Dict[str, Any] = {self.name: None}
        self.aging_time_sec = 10
        self.rw_lock = RWLockRead()

    def __call__(self, *args, **kwargs):
        return self.get_data()

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
            response[self.name] = []
            
            # only copy data records that haven't aged
            for group, data in self.persistence.items():
                if now - data["timestamp"] < self.aging_time_sec:
                    response[self.name].append(data)
        else:
            # when not grouped, response contains only a single object.
            if now - self.persistence["timestamp"] < self.aging_time_sec:
                response[self.name] = self.persistence
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
    def __init__(self, config: List[Dict[Any, Any]]):
        self._adapters: List[Adapter] = []
        self._init_adapters(config)
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


class LighthouseFactory:

    def create_from_config_file(self, filepath: str) -> Lighthouse:
        with open(filepath, 'r') as f:
            config = json.load(f)
            self._validate_config_file(config)
            _logger.setLevel(config["log_level"])
            return Lighthouse(config["ipc_rest_adapters"])

    @staticmethod
    def _validate_config_file(config: Dict):
        """
        check that config file contains all mandatory fields and raise a ConfigFileInvalidError if not
        :param config:
        :return:
        """
        if not isinstance(config, dict):
            raise ConfigFileInvalidError("Config file is not a valid dictionary")
        if "ipc_rest_adapters" not in config.keys():
            raise ConfigFileInvalidError("if_ip missing in config file")
        if "log_level" not in config.keys():
            raise ConfigFileInvalidError("log_level is missing in config file")
        if config["log_level"] not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ConfigFileInvalidError("unknown log level in config file")

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


factory = LighthouseFactory()
lh = factory.create_from_config_file("lighthouse/config.json")
lh.start()
