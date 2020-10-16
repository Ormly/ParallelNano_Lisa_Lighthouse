# Lighthouse monitoring API

Maintains REST API endpoints for various monitoring tasks on the parallel computer

## Installation 
```shell script
sudo apt install python3-pip
sudo apt install libffi-dev
git clone https://github.com/Ormly/ParallelNano_Lisa_Lighthouse.git
cd ParallelNano_Lisa_Lighthouse
python3 setup.py install --user
``` 

## Usage
```shell script
# start wsgi server with 2 workers as daemon
$ gunicorn -w 2 wsgi:app --daemon
```

To kill daemon(s):

```shell script
$ ps -ef | grep gunicorn
mario      34034    1254  0 17:39 ?        00:00:00 python gunicorn -w 2 wsgi:app --daemon
mario      34036   34034 73 17:39 ?        00:00:00 python gunicorn -w 2 wsgi:app --daemon
mario      34039   34034 69 17:39 ?        00:00:00 python gunicorn -w 2 wsgi:app --daemon
$ kill 34034 34036 34039
```

## Configuration
Agent is configured using the ```config.json``` file residing in the same library.

```json
{
  "ipc_rest_adapters":
  [
    {
      "adapter_name": "computer_nodes",
      "ipc_queue": "/compute_node_beacon",
      "rest_route": "/compute_node_beacon",
      "group_by_attrib": "ip_address"
    }
  ]
}
```
* ```ipc_rest_adapters``` - a list of adapters, matching ipc_queue to a REST endpoint
* ```adapter_name``` - name describing adapter (only used for logging)
* ```ipc_queue``` - id of the POSIX queue to get messages from 
* ```rest_route``` - name of REST endpoint
* ```group_by_attrib``` - Optional, messages may be grouped according to this attribute inside the incoming message

**Daemon should be restarted to apply changes to config file**

## Adding new monitoring sources
Lighthouse can be extended to support additional monitoring sources by following the following workflow

1. Implement a program that places monitoring messages onto an [IPC queue](https://pythonhosted.org/ipcqueue/) similarly to the [Beacon Server](https://github.com/Ormly/ParallelNano_Lisa_Beacon)
1. Add an adapter to the Lighthouse config file, with the appropriate ipc queue name, and the desired REST endpoint URL.
1. Restart Lighthouse

## API Specification
Get nodes information
URL: ```/compute_node_beacon```

Response
```json

{
"127.0.1.1":{"cpu":"x86_64","cpu_usage":3.7,"hostname":"node01","ip_address":"127.0.1.1","mem_usage":8.5540755014172,"platform":"Linux-5.4.0-48-generic-x86_64-with-glibc2.29","system":"Linux"},
"127.0.1.2":{"cpu":"x86_64","cpu_usage":3.7,"hostname":"node02","ip_address":"127.0.1.2","mem_usage":8.5540755014172,"platform":"Linux-5.4.0-48-generic-x86_64-with-glibc2.29","system":"Linux"},
"127.0.1.3":{"cpu":"x86_64","cpu_usage":3.7,"hostname":"node03","ip_address":"127.0.1.3","mem_usage":8.5540755014172,"platform":"Linux-5.4.0-48-generic-x86_64-with-glibc2.29","system":"Linux"}
}
```

Get temperature and humidity

URL: ```/temp_humidity```

Response
```json
{"temperature": 36.6, "humidity": 80.33}
```




```

