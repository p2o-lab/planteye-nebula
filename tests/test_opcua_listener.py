import pytest
import time
import yaml
import threading
from src_test.opcua_simultion_server import run_simulation_server
from Buffer import Buffer
from opcua_listener import OPCUAListener
from event_logger import log_event

@pytest.fixture()
def my_config():
    cfg_file = '../src_test/config_test.yaml'
    with open(cfg_file) as config_file:
        cfg = yaml.safe_load(config_file)
    return cfg


def test_polling_interval(my_config):
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(5)
    ua_listener.exit()
    time.sleep(5)
    server_thread.join()
    print('Buffer length=', my_buffer.len())
    assert 9 <= my_buffer.len() <= 11


def connect_online_disconnect_online(my_config):
    server_thread = threading.Thread(target=run_simulation_server, args=[30])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(30)
    ua_listener.exit()
    time.sleep(15)
    assert my_buffer.len() >=0

def connect_offline_disconnect_online(my_config):
    my_config['opcua']['number_of_reconnections'] = -1
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(30)
    server_thread = threading.Thread(target=run_simulation_server, args=[15])
    server_thread.start()
    time.sleep(30)
    ua_listener.exit()
    time.sleep(15)
    assert my_buffer.len() >= 0

def connect_online_disconnect_offline(my_config):
    server_thread = threading.Thread(target=run_simulation_server, args=[15])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(30)
    ua_listener.exit()
    time.sleep(15)
    assert my_buffer.len() >= 0

def test_reconnection_new_server_no_retries(my_config):
    my_config['opcua']['number_of_reconnections'] = 0
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(30)
    server_thread.join()
    buffer_len_after_first_stop = my_buffer.len()
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    time.sleep(20)
    ua_listener.exit()
    time.sleep(15)
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread.join()
    assert my_buffer.len() == buffer_len_after_first_stop


def test_reconnection_new_server_one_retry(my_config):
    my_config['opcua']['number_of_reconnections'] = 1
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(40)
    server_thread.join()
    buffer_len_after_first_stop = my_buffer.len()
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    time.sleep(20)
    ua_listener.exit()
    time.sleep(15)
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread.join()
    assert my_buffer.len() == buffer_len_after_first_stop


def test_reconnection_new_server_unlimited_retries(my_config):
    my_config['opcua']['number_of_reconnections'] = -1
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(60)
    server_thread.join()
    buffer_len_after_first_stop = my_buffer.len()
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    time.sleep(20)
    ua_listener.exit()
    time.sleep(15)
    log_event(my_config, 'TEST', '', 'INFO', 'Buffer length = ' + str(my_buffer.len()))
    server_thread.join()
    assert my_buffer.len() > buffer_len_after_first_stop


def test_continuous_reading(my_config):
    my_config['opcua']['number_of_reconnections'] = -1

    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(10)
    ua_listener.exit()
    server_thread.join()
    time.sleep(5)

    list_of_metrics = [metric['metric_id'] for metric in my_config['metrics']]
    metric_values = [[] for _ in range(len(list_of_metrics))]

    for buffer_entity in my_buffer.buffer:
        metric_idx = list_of_metrics.index(buffer_entity.data['node'].metric_id)
        metric_values[metric_idx].append(buffer_entity.data['data_variant'].Value.Value)

    increments_equal_one = True
    for metric_value_set in metric_values:
        for i in range(1, len(metric_value_set), 1):
            if metric_value_set[i] != metric_value_set[i - 1] + 1:
                increments_equal_one = False
                break
    assert increments_equal_one == True

def test_continous_reading_negative_case(my_config):
    my_config['opcua']['number_of_reconnections'] = -1
    my_config['metrics'][0]['interval'] = 500

    server_thread = threading.Thread(target=run_simulation_server, args=[20])
    server_thread.start()
    my_buffer = Buffer(my_config)
    ua_listener = OPCUAListener(my_config, my_buffer)
    time.sleep(3)
    ua_listener.connect()
    time.sleep(10)
    ua_listener.exit()
    server_thread.join()
    time.sleep(5)

    list_of_metrics = [metric['metric_id'] for metric in my_config['metrics']]
    metric_values = [[] for _ in range(len(list_of_metrics))]

    for buffer_entity in my_buffer.buffer:
        metric_idx = list_of_metrics.index(buffer_entity.data['node'].metric_id)
        metric_values[metric_idx].append(buffer_entity.data['data_variant'].Value.Value)

    increments_equal_one = True
    for metric_value_set in metric_values:
        for i in range(1, len(metric_value_set), 1):
            if metric_value_set[i] != metric_value_set[i - 1] + 1:
                increments_equal_one = False
                break
    assert increments_equal_one == False
