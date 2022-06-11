import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from random import randrange
from asyncio_mqtt import Client, MqttError
import aiohttp
import aiofile
import json
from datetime import datetime
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

_logger = logging.getLogger('garagewatch')

MQTT_HOST = "hass.local"
BUTTON_TOPIC = "zigbee2mqtt/0x0c4314fffea576f9"
PERIODIC_SNAPSHOT_DELAY = 60

async def advanced_example():
    # We 💛 context managers. Let's create a stack to help
    # us manage them.
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to the MQTT broker
        client = Client("hass.local")
        await stack.enter_async_context(client)

        # You can create any number of topic filters
        topic_filters = (
            BUTTON_TOPIC,
            # 👉 Try to add more filters!
        )
        for topic_filter in topic_filters:
            # Log all messages that matches the filter
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            template = f'[topic_filter="{topic_filter}"] {{}}'
            task = asyncio.create_task(process_mqtt_messages(messages))
            tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe("zigbee2mqtt/0x0c4314fffea576f9")

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)

async def process_mqtt_messages(messages):
    async for message in messages:
        json_payload = json.loads(message.payload)
        if message.topic == BUTTON_TOPIC and json_payload.get('action') == "on":
            # get snapshot without waiting for results
            _logger.info(f"Button pressed (topic %s)", message.topic)
            asyncio.ensure_future(get_snapshot())

async def get_snapshot():
    async with aiohttp.ClientSession() as session:
        timestamp_filename = datetime.now().strftime("%Y%m%d%H%M%S")
        _logger.info("Taking snapshot %s", timestamp_filename)
        async with session.get('http://garage.local:8081/?action=snapshot') as resp:
            if resp.status == 200:
                
                async with aiofile.async_open(f"/home/arrastia/Desktop/snapshot_{timestamp_filename}.jpg", "wb") as f:
                    await f.write(await resp.read())
                    _logger.info("Saved snapshot %s", timestamp_filename)

async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

async def periodic_snapshot():

    while True:
        # do not wait or care about results
        asyncio.ensure_future(get_snapshot())
        await asyncio.sleep(PERIODIC_SNAPSHOT_DELAY)
        

async def main():
    # Run the advanced_example indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 3  # [seconds]
    while True:
        try:
            task1 = asyncio.create_task(periodic_snapshot())
            task2 = asyncio.create_task(advanced_example())
            await asyncio.gather(task1, task2)
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)


asyncio.run(main())
