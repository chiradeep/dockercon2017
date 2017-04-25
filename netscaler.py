#!/usr/bin/env python

from functools import wraps
import logging
import time

from nssrc.com.citrix.netscaler.nitro.exception.nitro_exception \
    import nitro_exception
from nssrc.com.citrix.netscaler.nitro.resource.config.lb.lbvserver \
    import lbvserver
from nssrc.com.citrix.netscaler.nitro.resource.config.cs.csvserver \
    import csvserver
from nssrc.com.citrix.netscaler.nitro.resource.config.cs.cspolicy \
    import cspolicy
from nssrc.com.citrix.netscaler.nitro.resource.config.cs.csvserver_cspolicy_binding \
    import csvserver_cspolicy_binding
from nssrc.com.citrix.netscaler.nitro.service.nitro_service\
    import nitro_service
from nssrc.com.citrix.netscaler.nitro.resource.config.basic.servicegroup\
    import servicegroup
from nssrc.com.citrix.netscaler.nitro.resource.config.lb.lbvserver_servicegroup_binding\
    import lbvserver_servicegroup_binding
from nssrc.com.citrix.netscaler.nitro.resource.config.basic.servicegroup_servicegroupmember_binding\
    import servicegroup_servicegroupmember_binding


logger = logging.getLogger('docker_netscaler')


def ns_session_scope(func):
    @wraps(func)
    def login_logout(self, *args, **kwargs):
        ip = self.nsip + ':' + self.nsport
        self.ns_session = nitro_service(ip, 'HTTP')
        self.ns_session.set_credential(self.nslogin, self.nspasswd)
        self.ns_session.timeout = 600
        self.ns_session.login()
        result = func(self, *args, **kwargs)
        self.ns_session.logout()
        self.ns_session = None
        return result
    return login_logout


class NetscalerInterface:

    def __init__(self, nsip, nslogin, nspasswd, nsport='80'):
        self.nsip = nsip
        self.nsport = nsport
        self.nslogin = nslogin
        self.nspasswd = nspasswd
        self.ns_session = None

    def wait_for_ready(self):
        """Poll the API until we can login.

        When the container boots up, the NS container may just have
        booted up as well and therefore not ready to serve the API.
        """
        time.sleep(15)
        ip = self.nsip + ':' + self.nsport
        ready = False
        while not ready:
            ns_session = nitro_service(ip, 'HTTP')
            ns_session.set_credential(self.nslogin, self.nspasswd)
            ns_session.timeout = 600
            try:
                ns_session.login()
                ready = True
                logger.info('NetScaler is ready at %s' % ip)
                ns_session.logout()
            except Exception:
                logger.info('NetScaler API is not ready')
                time.sleep(5)

    def _create_service_group(self, grpname, service_type='HTTP'):
        try:
            svc_grp = servicegroup.get(self.ns_session, grpname)
            if (svc_grp.servicegroupname == grpname):
                logger.info('Service group %s already configured ' % grpname)
                return
        except nitro_exception:
            pass
        svc_grp = servicegroup()
        svc_grp.servicegroupname = grpname
        svc_grp.servicetype = service_type
        servicegroup.add(self.ns_session, svc_grp)

    def _create_lb(self, lbname):
        try:
            lb = lbvserver.get(self.ns_session, lbname)
            if (lb.name == lbname):
                logger.info('LB %s is already configured ' % lbname)
                return
        except nitro_exception:
            pass

        lb = lbvserver()
        lb.name = lbname
        lb.servicetype = 'HTTP'
        lbvserver.add(self.ns_session, lb)

    def _create_cs_vserver(self, cs_name, vip, port, service_type='HTTP'):
        try:
            cs = csvserver.get(self.ns_session, cs_name)
            if (cs.name == cs_name):
                logger.info('CS %s is already configured ' % cs_name)
                return
        except nitro_exception:
            pass

        cs = csvserver()
        cs.name = cs_name
        cs.servicetype = service_type
        cs.ipv46 = vip
        cs.port = port
        csvserver.add(self.ns_session, cs)

    def _create_cs_url_policy(self, policy_name, url_rule):
        try:
            policy = cspolicy.get(self.ns_session, policy_name)
            if (policy is not None):
                logger.info('CS URL Policy %s already exists ' % policy_name)
                return
        except nitro_exception:
            pass

        policy = cspolicy()
        policy.policyname = policy_name
        policy.url = url_rule
        cspolicy.add(self.ns_session, policy)

    def _bind_csvserver_policy_targetlb(self, cs_name, lb_name, policy_name):
        try:
            bindings = csvserver_cspolicy_binding.get(self.ns_session,
                                                      cs_name)
            for b in bindings:
                if b.name == cs_name and b.policyname == policy_name:
                    logger.info('CS %s is already bound to policy %s'
                                % (cs_name, policy_name))
                    return
        except nitro_exception:
            pass

        binding = csvserver_cspolicy_binding()
        binding.name = cs_name
        binding.policyname = policy_name
        binding.targetlbvserver = lb_name
        csvserver_cspolicy_binding.add(self.ns_session, binding)

    @ns_session_scope
    def add_service(self, grpname, srvr_ip, srvr_port):
        """Add a service(ip, port) to an existing service group."""
        try:
            bindings = servicegroup_servicegroupmember_binding.get(
                self.ns_session, grpname)
            for binding in bindings:
                if binding.ip == srvr_ip and binding.port == srvr_port:
                    logger.info('Service %s:%s is already bound to service \
                                group %s ' % (srvr_ip, srvr_port, grpname))
                    return

        except nitro_exception:
            pass
        binding = servicegroup_servicegroupmember_binding()
        binding.servicegroupname = grpname
        binding.ip = srvr_ip
        binding.port = srvr_port
        servicegroup_servicegroupmember_binding.add(self.ns_session, binding)

    @ns_session_scope
    def add_remove_services(self, grpname, ip_ports):
        """Reconfigure service group membership.
        To be the same as supplied list of ip and port
        """
        to_add = ip_ports
        to_remove = []
        try:
            bindings = servicegroup_servicegroupmember_binding.get(
                self.ns_session, grpname)
            existing = [(b.ip, b.port) for b in bindings if b.port != 0]
            to_remove = list(set(existing) - set(ip_ports))
            to_add = list(set(ip_ports) - set(existing))
            to_leave = list(set(ip_ports) & set(existing))
        except nitro_exception:
            pass  # no bindings
        for s in to_remove:
            binding = servicegroup_servicegroupmember_binding()
            binding.servicegroupname = grpname
            binding.ip = s[0]
            binding.port = s[1]
            logger.info('Unbinding %s:%s from service group %s ' % (s[0], s[1], grpname))
            servicegroup_servicegroupmember_binding.delete(self.ns_session,
                                                           binding)
        for s in to_add:
            binding = servicegroup_servicegroupmember_binding()
            binding.servicegroupname = grpname
            binding.ip = s[0]
            binding.port = s[1]
            logger.info('Binding %s:%s from service group %s ' % (s[0], s[1], grpname))
            servicegroup_servicegroupmember_binding.add(self.ns_session,
                                                        binding)
        for s in to_leave:
            logger.info('Service %s:%s is already bound to  service group %s' % (s[0], s[1], grpname))

    def _bind_service_group_lb(self, lbname, grpname):
        try:
            bindings = lbvserver_servicegroup_binding.get(self.ns_session,
                                                          lbname)
            for b in bindings:
                if b.name == lbname and b.servicegroupname == grpname:
                    logger.info('LB %s is already bound to service group %s'
                                % (lbname, grpname))
                    return
        except nitro_exception:
            pass

        binding = lbvserver_servicegroup_binding()
        binding.name = lbname
        binding.servicegroupname = grpname
        lbvserver_servicegroup_binding.add(self.ns_session, binding)

    def _enable_cs_feature(self):
        try:
            self.ns_session.enable_features(['cs'])
        except Exception as e:
            logger.warn('Exception: %s' % e.message)

    @ns_session_scope
    def configure_cs_frontend(self, cs_name, vip, port, services_dict):
        """Create a CS vserver with provided name, vip and port.
        For each key in the services dict, creates an LB Vserver
        and a service group and binds them together. For each value in
        the services dict, creates a content switching policy and
        binds it to the CS vserver and the respective LB vservers.
        """
        try:
            self._enable_cs_feature()
            self._create_cs_vserver(cs_name, vip, port)
            for service_name in services_dict:
                lb_name = service_name.capitalize() + '_lb'
                grp_name = service_name
                logger.info('LB %s, ServiceGroup %s' % (lb_name, grp_name))
                self._create_service_group(grp_name)
                self._create_lb(lb_name)
                self._bind_service_group_lb(lb_name, grp_name)
                url_rule = services_dict[service_name]
                policy_name = service_name + '_policy'
                logger.info('Policy %s, rule %s' % (policy_name, url_rule))
                self._create_cs_url_policy(policy_name, url_rule)
                logger.info('Policy %s, rule %s' % (policy_name, url_rule))
                self._bind_csvserver_policy_targetlb(cs_name, lb_name,
                                                     policy_name)
        except nitro_exception as ne:
            logger.warn('Nitro Exception: %s' % ne.message)
        except Exception as e:
            logger.warn('Exception: %s' % e.message)
