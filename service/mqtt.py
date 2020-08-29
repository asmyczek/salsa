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


def create_client(config):
    client = mqtt.Client(config('mqtt', 'client_name'))
    client.username_pw_set(config('mqtt', 'user'), password=config.get('mqtt', 'password'))
    client.user_data_set({'config': config})

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = process_message
    client.on_publish = on_publish
    client.on_subscribe = lambda c, ud, mid, qos: logging.debug('Subscribed with qos {0}.'.format(qos))
    client.will_set(f'{config("mqtt", "topic")}/status', 'DOWN', qos=0, retain=False)
    return client


def start_notifier(config) -> mqtt.Client:
    if config('mqtt'):
        client = create_client(config)
        client.loop_start()
        try:
            logging.info('Starting MQTT notifier.')
            client.connect(config('mqtt', 'broker'), config('mqtt', 'port'))
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
