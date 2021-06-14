# PlantEye/Nebula

Nebula is a tool to acquire process data over OPC UA and ingest it onto InfluxDB for any further usage. This tool
is initially created for Modular plants but can be used for other purposes as well.

## Usage
To run the script be sure that config-file (config.yaml) is proper and run the script:
```bash
python3 main.py
```
Collection of ready dockerfiles and docker-compose files for PEAs of the P2O-Lab can be found in https://github.com/vkhaydarov/planteye-docker-collection

## Configure
Create a config file (config.yaml) according to the following structure:
```yaml
opcua:
  url: opc.tcp://10.6.51.130:4840
  number_of_reconnections: -1
  reconnect_interval: 10000
buffer:
  max_size: 10000
influxdb:
  host: 127.0.0.1
  port: 8086
  user: root
  password: root
  database: M13
  db_user: db_user
  db_password: db_password
  reconnect_interval: 10000
  write_interval: 10000
event_logger:
  publish: false
  print_level: DEBUG
metrics:
- metric_id: '1'
  measurement: data_assemblies
  tagname: F3021
  variable: V
  nodeNamespace: 4
  nodeId: '|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.Sensors.F3021.V'
  method: polled
  interval: 1000
```
Further nodeIds can be added in the section with Metrics.
In order to generate conform config-files for Process Equipment Assemblies based on MTP-files, please use https://github.com/vkhaydarov/planteye-mtp2cfg.

## Requirements
To install requirements use the following command:
```bash
pip3 install -r requirements.txt
```

## License
Valentin Khaydarov (valentin.khaydarov@tu-dresden.de)\
Process-To-Order-Lab\
TU Dresden