# Packages
from opcua import Client
from opcua import ua
import time
import threading
from event_logger import log_event
from Buffer import BufferEntity


class Node:
    """
    Node class collects all relevant parameters and objects of OPC UA listener.
    This class makes it possible a handy transfer of all relevant parameters and objects within only one object.
    """

    def __init__(self, metric_id, meas, tag, var, ns, id, method, time_interval):
        """
        Initialisation
        :param metric_id: Name of the metric that might be a string or number.
        This parameter will be shown in log, but has no other effect.
        :param meas: Measurement name, in which measurement collected data points are to transfer to.
        :param tag: Unique tag name of the source object of data that will be stored as a field in the influx db
        (i.e. sensor tag, data assembly or service parameter tag).
        :param var: Variable name that is allocated to one of the variables of one source object (i.e. upper and lower
        limit of the sensor or V of a data assembly)
        :param ns: Namespace index of the OPC UA variable
        :param id: NodeId of the OPC UA variable (might be of integer or string type)
        :param method: Method of data collection: either polled or subscription (Note: Subscription method is realised
        via external package and might work unstable)
        :param time_interval: Relevant only for polled method and denotes the interval in milliseconds between two data
        requests
        """
        self.metric_id = metric_id
        self.meas = meas
        self.tag = tag
        self.var = var
        self.ns = ns
        self.id = id
        self.obj = ''
        self.method = method
        self.time_interval = time_interval
        self.monitored = False
        self._thread = ''
        self._sub_obj = ''
        self._subs_handle = ''
        self.stop = False


class OPCUAListener:
    """
    This class represents an OPC UA server and offers necessary functionality to connect to an OPC UA server as well as
    collect data points and transfer them into a buffer.
    """

    def __init__(self, cfg, buffer):
        """
        Initialisation
        :param cfg: Set of parameters including connection information and data about metrics
        :param buffer: Link to a buffer object, where to save gathered data points
        """
        # Module name
        self.module_name = 'OPC UA'

        # Extraction of configuration parameters relevant for connectivity of the OPC UA server
        self.cfg = cfg
        self.uri = self.cfg['opcua']['url']
        self.reconnect_interval = self.cfg['opcua']['reconnect_interval']
        self.num_reconnect = self.cfg['opcua']['number_of_reconnections']

        # Creation of OPC UA client object
        self.client = Client(self.uri)

        # Node objects with parameters and objects wrt. each metric
        self.imported_nodes = self._import_nodes()
        self.monitored_nodes = []

        # Connectivity variables
        self.connection_status = False
        self.connectivity_thread = ''
        self.cur_reconnect = self.num_reconnect

        # Buffer
        self.buffer = buffer

        # Exit flag to finish connectivity thread
        self._exit = False

    def _single_connect(self):
        """
        Single connection to the OPC UA server
        :return: True - if connection successfully established and False - if not
        """
        log_event(self.cfg, self.module_name, '', 'INFO', 'Connecting to OPC UA server ' + self.uri + '...')
        try:
            self.client.connect()
            log_event(self.cfg, self.module_name, '', 'INFO', 'Connection established')
            time.sleep(1)
            return True
        except Exception:
            log_event(self.cfg, self.module_name, '', 'ERR', 'Connection failed')
            return False

    def connect(self):
        """
        Creates separate thread to take care of connectivity
        :return:
        """
        self.connectivity_thread = threading.Thread(target=self._connectivity)
        self.connectivity_thread.start()

    def exit(self):
        """
        Initiates closing of threads and disconnection from the OPC UA server
        :return:
        """
        self._exit = True

    def _connectivity(self):
        """
        This function checks connection and reconnect to the OPC UA server as required.
        :return:
        """
        while True:
            # If exit flag received, we stop the thread
            if self._exit:
                self.disconnect()
                time.sleep(1)
                break
            # print('Threads: ', threading.active_count())

            # If connection established, we check connection status periodically
            if self.connection_status:
                try:
                    # Request OPCUA server status
                    self.client.get_node(ua.NodeId(2259, 0)).get_data_value()
                    self.cur_reconnect = self.num_reconnect
                    if self.num_reconnect == 0:
                        self.cur_reconnect -= 1

                except Exception:
                    # In case of missing connection, we do cleanup procedure and wait a little bit to let
                    # opcua-python close subscription threads
                    log_event(self.cfg, self.module_name, '', 'WARN', 'No connection to OPC UA server')
                    self.connection_status = False
                    self.disconnect()
                    time.sleep(1)

            # If connection does not exist yet/anymore, we try to establish one
            else:

                # Extreme cases
                if self.num_reconnect >= 1 and self.cur_reconnect == 0:
                    break
                if self.num_reconnect == 0 and self.cur_reconnect == -1:
                    break

                # Try to connect to OPC UA server
                connected = self._single_connect()
                # In case of successful connection, start monitoring
                if connected:
                    self._start_monitoring()
                    self.connection_status = True
                # In case of unsuccessful connection, repeat again after given reconnection interval
                else:
                    self.cur_reconnect -= 1
                    self.connection_status = False
                    time.sleep(self.reconnect_interval / 1000)

            # Wait a little bit until next connection check
            time.sleep(0.5)

    def get_connection_status(self):
        """
        This function returns current status of connection to the OPC UA server.
        :return: dict with 'code' and 'status' as text
        """
        if self.connection_status:
            return {'code': self.connection_status, 'status': 'Connected'}
        return {'code': self.connection_status, 'status': 'Disconnected'}

    def _import_nodes(self):
        """
        This function reads the config dict and extract metric parameters ain the form of s node objects
        :return: list of node objects
        """
        metrics = self.cfg['metrics']
        nodes = []
        for metric in metrics:
            metric_id = metric['metric_id']
            meas = metric['measurement']
            tag = metric['tagname']
            var = metric['variable']
            ns = metric['nodeNamespace']
            id = metric['nodeId']
            method = metric['method']
            time_interval = metric['interval']
            nodes.append(Node(metric_id=metric_id, meas=meas, tag=tag, var=var, ns=ns, id=id, method=method,
                              time_interval=time_interval))
        return nodes

    def _start_monitoring(self):
        """
        This function adds imported nodes to monitoring items and starts the monitoring procedure
        :return:
        """
        self.monitored_nodes = []
        log_event(self.cfg, self.module_name, '', 'INFO',
                  'Start monitoring of ' + str(len(self.imported_nodes)) + ' nodes')
        for node in self.imported_nodes:
            # Try to node objects from the OPC UA server to be sure given node exists. If does, start monitoring.
            try:
                log_event(self.cfg, self.module_name, '', 'INFO',
                          'Adding node (metric_id=' + str(node.metric_id) + ')... ')
                node.obj = self.client.get_node(ua.NodeId(node.id, node.ns))
                self._start_node_monitoring(node)
                self.monitored_nodes.append(node)
                node.monitored = True
                log_event(self.cfg, self.module_name, '', 'INFO',
                          'Node (metric_id=' + str(node.metric_id) + ') added for monitoring, method = ' + node.method)
            except Exception:
                log_event(self.cfg, self.module_name, '', 'ERR',
                          'Node adding (metric_id=' + str(node.metric_id) + ') failed')

    def _start_node_monitoring(self, node):
        """
        This function starts monitoring depends on the given node monitoring method.
        :param node: node object
        :return:
        """
        node.stop = False
        if node.method == 'polled':
            self._start_polling(node)
        elif node.method == 'subscription':
            self._start_subscription(node)
        else:
            log_event(self.cfg, self.module_name, '', 'INFO',
                      'Wrong method of node (metric_id=' + str(node.metric_id) + ')')
            return

    def _stop_monitoring(self):
        """
        This function closes monitoring process of all nodes but only ones with "polled" method. Subscriptions is to
        terminate by disconnecting
        :return:
        """
        for node in self.monitored_nodes:
            if node.method == 'polled':
                node.stop = True
        time.sleep(5)
        self.monitored_nodes = []

    def disconnect(self):
        """
        This function stop monitoring all monitoring items and tries its best to disconnect from the OPC UA server.
        :return: Success of the disconnection procedure
        """
        log_event(self.cfg, self.module_name, '', 'INFO', 'Disconnecting from OPC UA server ' + self.uri + '...')
        try:
            self._stop_monitoring()
            self.client.disconnect()
            self.connection_status = False
            time.sleep(5)
            log_event(self.cfg, self.module_name, '', 'INFO', 'Disconnection completed on both server and client sides')
            return True
        except Exception:
            # Even if the disconnection failed and session might keep running, subscription threads will be terminated
            time.sleep(5)
            log_event(self.cfg, self.module_name, '', 'WARN', 'Disconnection completed only on client side')
            return False

    def _start_polling(self, node):
        """
        This function begins polling of a node as separate thread
        :param node: node object with "polled" monitoring method
        :return:
        """
        if node.method != 'polled':
            log_event(self.cfg, self.module_name, '', 'WARN',
                      'Wrong monitoring method (metric_id=' + str(node.metric_id) + ')')

        node.stop = False
        node._thread = threading.Thread(target=self._poll_value, args=[node])
        node._thread.setDaemon(True)
        node._thread.start()

    def _start_subscription(self, node):
        """
        This function begins subscription of a node as separate thread (by means of external package)
        :param node: node object with "subscription" monitoring method
        :return:
        """

        handler = SubHandler(node, self.cfg, self.buffer)
        try:
            node._sub_obj = self.client.create_subscription(500, handler)
            var = self.client.get_node(ua.NodeId(node.id, node.ns))
            node._sub_handle = node._sub_obj.subscribe_data_change(var)
        except Exception:
            log_event(self.cfg, self.module_name, '', 'WARN',
                      'Cannot subscribe (metric_id=' + str(node.metric_id) + '), internal error')

    def _poll_value(self, node):
        """
        This function requests a value of the given OPC UA node and as soon as received, place it together with
        the server timestamp into buffer
        :param node: node object
        :return:
        """
        log_event(self.cfg, self.module_name, '', 'INFO', 'Polling values of ' + str(node.tag) + '...')

        # Set initial time point
        cycle_begin = time.time() - node.time_interval / 1000.0
        while True:
            if node.stop:
                node.monitored = False
                return

            # Calculate one cycle length
            cycle_begin = cycle_begin + node.time_interval / 1000.0

            # If last cycle lasted much longer, we need to skip the current polling cycle to catch up in the future
            if cycle_begin + 0.010 < time.time():
                log_event(self.cfg, self.module_name, '', 'ERR', 'Polling skipped (increase time interval)')
                continue

            # Try to get data value and timestamp and add it as a entity into buffer
            try:
                data_variant = node.obj.get_data_value()
                timestamp = data_variant.SourceTimestamp
                value = data_variant.Value.Value
                log_event(self.cfg, self.module_name, '', 'INFO',
                          'Read value (metric_id=' + str(node.metric_id) + ' t=' + str(timestamp) + ')=' + str(value))
            except Exception:
                # If fails, check if connection to the server. If no connection, do not show error message and escape.
                if not self.connection_status or node.stop:
                    node.monitored = False
                else:
                    log_event(self.cfg, self.module_name, '', 'ERR',
                              'Polling (metric_id=' + str(node.metric_id) + ') failed')
                return
            if node.stop:
                node.monitored = False
                return

            buffer_data = {'node': node, 'data_variant': data_variant}
            self.buffer.add_point(BufferEntity(entity_type='opcua', data=buffer_data))

            # Calculate real cycle duration
            cycle_dur = time.time() - cycle_begin

            # If the cycle duration longer than given and no connection issues, jump directly to the next cycle
            if (cycle_dur > node.time_interval / 1000.0) and self.connection_status:
                log_event(self.cfg, self.module_name, '', 'WARN',
                          'Polling takes longer ' + str(cycle_dur) + ' than given time intervals')
            else:
                # Calculate how long we need to wait till the begin of the next cycle
                time.sleep(max(node.time_interval / 1000.0 - (time.time() - cycle_begin), 0))


class SubHandler(object):
    """
    This is subscription Handler for receiving events from server for a subscription
    data_change.
    """

    def __init__(self, node, cfg, buffer):
        self.node = node
        self.cfg = cfg
        self.buffer = buffer
        self.module_name = 'OPC UA'

    def datachange_notification(self, node, val, data):
        """
        This function is invoked every time data change event triggers
        :param node: node object
        :param val: value of the monitored item
        :param data: data object received from the OPC UA server
        :return:
        """
        try:
            # Get thread ident (not used for anything)
            self.node._thread = threading.get_ident()

            # Get data object as data variant including value, datatype and source timestamp
            data_variant = data.monitored_item.Value
            timestamp = data_variant.SourceTimestamp
            value = data_variant.Value.Value
            metric_id = self.node.metric_id

            log_event(self.cfg, self.module_name, '', 'INFO',
                      'Read value (metric_id=' + str(metric_id) + ' t=' + str(timestamp) + ')=' + str(value))

            # Add point structure as entity into buffer
            buffer_data = {'node': self.node, 'data_variant': data_variant}
            self.buffer.add_point(BufferEntity(entity_type='opcua', data=buffer_data))
        except Exception:
            log_event(self.cfg, self.module_name, '', 'ERR', 'Adding point into buffer failed')
