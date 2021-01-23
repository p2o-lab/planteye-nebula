from opcua_listener import OPCUAListener
from influxdb_writer import InfluxDBWriter
from Buffer import Buffer
import schema
import yaml

if __name__ == '__main__':

    # Import config
    cfg_file = 'config.yaml'
    with open(cfg_file) as config_file:
        cfg = yaml.safe_load(config_file)

    # Validate config
    validation_res, validation_msg = schema.validate_cfg(cfg)
    if not validation_res:
        print(validation_msg)
        exit(1)

    # Initialise buffer
    data_buffer = Buffer(cfg)

    # Start opcua listener
    ua_listener = OPCUAListener(cfg=cfg, buffer=data_buffer)
    ua_listener.connect()

    # Start influxdb writer
    idb = InfluxDBWriter(cfg=cfg, buffer=data_buffer)
    idb.connect()
