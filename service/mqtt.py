# -*- coding: utf-8 -*-

import logging
import paho.mqtt.client as mqtt


def on_connect(client, user_data, flags, rc):
    if rc == 0:
        logging.info('Connected to mqtt broker.')
        client.subscribe(f'{client.config.topic}/sync')
        client.publish(f'{user_data["config"].topic}/status', 'UP', qos=2, retain=False)
    else:
        logging.error(f'Unable to establish connection. Status {rc}')


def on_disconnect(client, user_data, rc):
    client.publish(f'{user_data["config"].topic}/status', 'DOWN', qos=2, retain=False)
    logging.info(f'Disconnected from mqtt broker. Status {rc}')


def process_message(client, user_data, message):
    topic = message.topic
    status = str(message.payload.decode('utf-8'))
    logging.info(f'Status update on {topic} with status {status}.')


def on_publish(client, user_data, mid):
    logging.info(f'Data published with mid {mid}.')


def create_client(mqtt_config):
    client = mqtt.Client(mqtt_config.client_name)
    client.username_pw_set(mqtt_config.user, password=mqtt_config.password)
    client.user_data_set({'config': mqtt_config})

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = process_message
    client.on_publish = on_publish
    client.on_subscribe = lambda c, ud, mid, qos: logging.debug('Subscribed with qos {0}.'.format(qos))
    client.will_set(f'{mqtt_config.topic}/status', 'DOWN', qos=0, retain=False)
    return client


def start_notifier(config) -> mqtt.Client:
    if config.mqtt:
        mqtt_config = config.mqtt
        client = create_client(mqtt_config)
        client.loop_start()
        try:
            logging.info('Starting MQTT notifier.')
            client.connect(mqtt_config.broker, mqtt_config.port)
            return client
        except Exception as e:
            logging.error(e)
            logging.exception('Unable to connect to MQTT broker!')
    else:
        logging.warning('No MQTT config defined, notifier not initialised.')
        return None


def cleanup_notifier(client: mqtt.Client):
    if client is not None:
        client.loop_stop()
        client.disconnect()
