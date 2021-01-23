import yaml
import time
import threading
from opcua import Server
from event_logger import log_event


def run_simulation_server(steps):
    """
    This support function creates a simple OPC UA server with node listed in the config file
    :param steps: Lifecycle of the server
    :return:
    """

    with open('../src_test/config_test.yaml') as config_file:
        cfg = yaml.safe_load(config_file)

    # setup the server
    server = Server()
    server.set_endpoint(cfg['opcua']['url'])

    # setup the namespace
    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    # get objects node
    objects = server.get_objects_node()

    # server start
    server.start()
    log_event(cfg, 'OPCUA TEST SERVER', '', 'INFO', 'OPC UA server started')

    # populating the address space
    myobj = objects.add_object(idx, "TestDataAssembly")

    nodes = []
    metrics = cfg['metrics']
    for metric in metrics:
        metric_id = metric['metric_id']
        meas = metric['measurement']
        tag = metric['tagname']
        var = metric['variable']
        ns = metric['nodeNamespace']
        id = metric['nodeId']
        method = metric['method']
        time_interval = metric['interval']
        node_str = 'ns=' + str(ns) + '; i=' + str(id)
        nodes.append(myobj.add_variable(node_str, var, -1))

    # update variable
    time.sleep(1)
    for it in range(steps):
        for node in nodes:
            node.set_value(node.get_value() + 1)
            time.sleep(0.5)
    time.sleep(2)
    server.stop()
    log_event(cfg, 'OPCUA TEST SERVER', '', 'INFO', 'OPC UA server stopped')

if __name__ == '__main__':
    run_simulation_server(3600)