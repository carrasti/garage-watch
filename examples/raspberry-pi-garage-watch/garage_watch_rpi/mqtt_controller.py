import json
from mqtt.client.factory import MQTTFactory

from twisted.internet.defer       import inlineCallbacks, DeferredList
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet             import task
from twisted.internet.endpoints   import clientFromString

BROKER = "tcp:hass.local:1883"

device_config = {
    "ids": '1FEA34',
    "name": 'GaragePi',
    "mf": 'Carlos A',
    "mdl": 'Raspberry garage',
    "sw": "Raspberry pi with sensor in the garage for Carlos A",
}

import logging

_logger = logging.getLogger(__name__)

# -----------------------
# MQTT Publishing Service
# -----------------------

class MQTTService(ClientService):

    def __init__(self, reactor):
        self.reactor = reactor
        factory    = MQTTFactory(profile=MQTTFactory.PUBLISHER)
        endpoint = clientFromString(reactor, BROKER)
        ClientService.__init__(self, endpoint, factory, retryPolicy=backoffPolicy())
        self.connected = False

    def startService(self):
        _logger.info("starting MQTT Client Publisher Service")
        # invoke whenConnected() inherited method
        self.whenConnected().addCallback(self.connectToBroker)
        ClientService.startService(self)


    @inlineCallbacks
    def connectToBroker(self, protocol):
        '''
        Connect to MQTT broker
        '''
        self.protocol                 = protocol
        self.protocol.onDisconnection = self.onDisconnection
        # We are issuing 3 publish in a row
        # if order matters, then set window size to 1
        # Publish requests beyond window size are enqueued
        self.protocol.setWindowSize(3) 
        
        try:
            yield self.protocol.connect("TwistedMQTT-pub", keepalive=60)
        except Exception as e:
            _logger.error("MQTT connecting to %s raised %s", BROKER, e)
        else:
            _logger.info("MQTT client connected to %s", BROKER)
            self.connected = True
            self.publish_discovery()


    def onDisconnection(self, reason):
        '''
        get notfied of disconnections
        and get a deferred for a new protocol object (next retry)
        '''
        _logger.info("Connection to mqtt broker was lost, reason=%s", reason)
        self.connected = False
        self.whenConnected().addCallback(self.connectToBroker)


    def publish_discovery(self):
        self.publish(f"homeassistant/binary_sensor/{device_config['ids']}_GARAGE_DOOR_OPEN/config", json.dumps({
            "name": "Garage Door Open",
            "uniq_id": device_config['ids'] + "_GARAGE_DOOR_OPEN",
            "device_class": "garage_door",
            "state_topic": f"homeassistant/binary_sensor/{device_config['ids']}_GARAGE_DOOR_OPEN/state",
            "device": device_config,
            "retain": True,
        }))

    def publish(self, topic, message):
        def _logFailure(failure):
            _logger.info("Failure publishing MQTT message %s", failure.getErrorMessage())
            return failure

        #def _logAll(*args):
        #    _logger.info("MQTT publihing complete. args=%s", args)

        #_logger.info("Publishing message ")
        d1 = self.protocol.publish(topic=topic, qos=0, message=message)
        d1.addErrback(_logFailure)
        dlist = DeferredList([d1], consumeErrors=True)

        #dlist.addCallback(_logAll)
        return dlist

    def report_door_open(self):
        _logger.info('Reporting door open')
        self.publish(f"homeassistant/binary_sensor/{device_config['ids']}_GARAGE_DOOR_OPEN/state", "ON")
    
    def report_door_closed(self):
        _logger.info('Reporting door closed')
        self.publish(f"homeassistant/binary_sensor/{device_config['ids']}_GARAGE_DOOR_OPEN/state", "OFF")
