import pytest
import yaml
from Buffer import Buffer
from random import random


@pytest.fixture
def my_buffer():
    cfg_file = '../src_test/config_test.yaml'
    with open(cfg_file) as config_file:
        cfg = yaml.safe_load(config_file)
    test_buffer = Buffer(cfg)
    for i in range(test_buffer.max_buffer_size-1):
        test_buffer.buffer.append(random() * 1000)
    return test_buffer


def test_add_point(my_buffer):
    buffer_len = my_buffer.len()
    new_point = random() * 1000
    my_buffer.add_point(new_point)
    assert my_buffer.buffer[-1] == new_point
    assert my_buffer.len() == buffer_len + 1

def test_add_point_above_limit(my_buffer):
    buffer_len = my_buffer.len()
    new_point = random() * 1000
    for _ in range(10):
        my_buffer.add_point(new_point)
    assert my_buffer.len() == my_buffer.max_buffer_size

def test_remove_point_from_empty_buffer(my_buffer):
    for _ in range(my_buffer.max_buffer_size+100):
        my_buffer.remove_point(0)
    assert my_buffer.len() == 0

def test_remove_point(my_buffer):
    buffer_len = my_buffer.len()
    my_buffer.remove_point(my_buffer.max_buffer_size+1)
    my_buffer.remove_point(0)
    my_buffer.remove_point(0)
    assert my_buffer.len() == buffer_len - 2

def test_remove_points(my_buffer):
    buffer_len = my_buffer.len()
    to_remove = [my_buffer.max_buffer_size+1, my_buffer.max_buffer_size-1, 0, -1, 10, 25, my_buffer.max_buffer_size+1, 10, 10]
    my_buffer.remove_points(to_remove)
    assert my_buffer.len() == buffer_len - 3

def test_len(my_buffer):
    assert my_buffer.len() == my_buffer.max_buffer_size-1
