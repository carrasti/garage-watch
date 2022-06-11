from contextlib import AsyncExitStack
from config import settings
import asyncio

import logging
import json


_logger = logging.getLogger("garagewatch.mqtt")


async def mqtt_action(client):
    # We 💛 context managers. Let's create a stack to help
    # us manage them.
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Filtered topics
        topic_filters = (settings.BUTTON_TOPIC,)
        for topic_filter in topic_filters:
            # Create tasks to register listeners for each topic
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            task = asyncio.create_task(process_mqtt_messages(messages))
            tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.
        await client.subscribe(settings.BUTTON_TOPIC)

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)


async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


async def process_mqtt_messages(messages):
    async for message in messages:
        json_payload = json.loads(message.payload)
        if (
            message.topic == settings.BUTTON_TOPIC
            and json_payload.get("action") == "on"
        ):
            # get snapshot without waiting for results
            _logger.info(f"Button pressed (topic %s)", message.topic)
            asyncio.ensure_future(
                get_snapshot(settings.MJPEG_STREAMER_BASE_URL_SURVEILLANCE)
            )
