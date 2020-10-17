from typing import Dict, Any, List, Optional, Union
import json
import pickle
import threading
import time

from flask import Flask
from ipcqueue.posixmq import queue, Queue

from lighthouse.adapter import Target, Source, Adapter

app = Flask(__name__)


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
        self.name = name
        self.group_by_attr = group_by_attr
        self.persistence: Dict[Any, Any] = {}
        self.response: Dict[str, Any] = {self.name: None}
        self.aging_time_sec = 3

    def __call__(self, *args, **kwargs):
        return self.get_data()

    def get_data(self) -> Dict[Any, Any]:
        """
        copy the data that hasn't aged from storage to response
        """
        self._prepare_new_response()
        return self.response

    def _prepare_new_response(self):
        # clear response with each request
        self.response.clear()
        now = time.time()
        if self.group_by_attr:
            # if grouped then request contains a list of objects
            self.response[self.name] = []
            
            # only copy data records that haven't aged
            for group, data in self.persistence.items():
                if now - data["timestamp"] < self.aging_time_sec:
                    self.response[self.name].append(data)
        else:
            # when not grouped, response contains only a single object.
            if now - self.persistence["timestamp"] < self.aging_time_sec:
                self.response[self.name] = self.persistence

    def feed(self, data: Dict[Any, Any]):
        """

        :param data:
        :return:
        """
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
            target = RESTAPITarget(name=adapter["rest_route"], group_by_attr=adapter.get("group_by_attrib"))
            self._create_route(target)

            source = IPCQueueSource(name=adapter["ipc_queue"])
            self._adapters.append(Adapter(name=adapter["adapter_name"], source=source, target=target))

    @staticmethod
    def _create_route(endpoint: RESTAPITarget):
        app.add_url_rule(endpoint.name, endpoint.name[1:], endpoint)

    def run(self):
        self.is_running = True
        while self.is_running and self.parent_thread.is_alive():
            for adapter in self._adapters:
                adapter.update()

    def stop(self):
        self.is_running = False


class LighthouseFactory:

    def create_from_config_file(self, filepath: str) -> Lighthouse:
        with open(filepath, 'r') as f:
            config = json.load(f)
            self._validate_config_file(config)
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
