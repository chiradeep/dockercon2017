#!/usr/bin/env python
import logging
from netscaler import NetscalerInterface
import consul
import os
import copy


logging.basicConfig(level=logging.CRITICAL,
                    format='%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)-10s]  (%(threadName)s) %(message)s')
logger = logging.getLogger('docker_netscaler')
logger.addFilter(logging.Filter('docker_netscaler'))
logger.setLevel(logging.DEBUG)

CS_VSERVER_NAME = 'WidgetShop'
CS_VSERVER_PORT = 8088
SERVICES = ['login-service', 'cart-service', 'catalog-service']


def get_service_routes():
    c = consul.Consul(host=os.getenv('CONSUL_IP', '127.0.0.1'))

    index, data = c.kv.get('widgetshop/services', recurse=True)
    service_routes = {}
    if data is None:
        return service_routes
    for j in data:
        if j['Key'].endswith('route'):
            svcname = j['Key'].split('/')[2]
            service_routes[svcname] = j['Value']
    return service_routes


def get_service_backends(svcname):
    c = consul.Consul(host=os.getenv('CONSUL_IP', '127.0.0.1'))

    index, data = c.catalog.service(svcname)
    return [(d['ServiceID'].split(':')[0], d['ServicePort']) for d in data]


def watch_for_service_changes(netskaler):
    index = None
    c = consul.Consul(host=os.getenv('CONSUL_IP', '127.0.0.1'))
    svc_count = {s: 0 for s in SERVICES}
    while True:
        index, data = c.catalog.services(index=index)
        new_svc_count = {'login-service': 0, 'cart-service': 0, 'catalog-service': 0}
        svc_instances = c.agent.services()
        for svc_instance in svc_instances:
            svc_descr = svc_instances[svc_instance]
            svc = svc_descr[u'Service']
            if svc in SERVICES:
                # print('Service: ' + svc + ', id=' + svc_descr['ID'] + ', Port=' + str(svc_descr['Port']))
                new_svc_count[svc] += 1
        diffs = [s for s in SERVICES if new_svc_count[s] != svc_count[s]]
        logger.info('Change in service : ' + str(diffs))
        for d in diffs:
            endpoints = get_service_backends(d)
            # logger.info('Endpoints for svc ' + d + ': ' + str(endpoints))
            netskaler.add_remove_services(d, endpoints)
        svc_count = copy.deepcopy(new_svc_count)


if __name__ == '__main__':

    nsport = os.getenv('NS_PORT', 80)
    nsip = os.getenv('NS_IP', '127.0.0.1')
    netskaler = NetscalerInterface(nsip, 'nsroot',
                                   'nsroot', str(nsport))
    services_routes = get_service_routes()
    logger.info('Service routes are ' + str(services_routes))

    netskaler.wait_for_ready()

    # create cs vserver, lb vservers and service groups
    netskaler.configure_cs_frontend(CS_VSERVER_NAME, '127.0.0.1',
                                    CS_VSERVER_PORT, services_routes)

    # populate service group members into service groups
    for svc in SERVICES:
        endpoints = get_service_backends(svc)
        logger.info('Endpoints for svc ' + svc + ': ' + str(endpoints))
        netskaler.add_remove_services(svc, endpoints)

    # watch for changes in service counts
    watch_for_service_changes(netskaler)
