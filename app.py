import asyncio
from asyncio_mqtt import Client, MqttError
import logging
import sys
from garage_watch.mqtt import mqtt_action
from config import settings
from garage_watch.snapshot import get_snapshot


logging.basicConfig(stream=sys.stdout, level=settings.LOGGER_LEVEL)

_logger = logging.getLogger(settings.LOGGER_NAME)


async def periodic_snapshot(base_url):

    while True:
        # do not wait or care about results
        asyncio.ensure_future(get_snapshot(base_url))
        await asyncio.sleep(settings.PERIODIC_SNAPSHOT_DELAY)


async def main():
    # Run the advanced_example indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 3  # [seconds]
    while True:
        try:
            async with Client(settings.MQTT_HOST) as client:
                task1 = asyncio.create_task(
                    periodic_snapshot(settings.MJPEG_STREAMER_BASE_URL_SURVEILLANCE)
                )
                task2 = asyncio.create_task(mqtt_action(client))
                await asyncio.gather(task1, task2)
        except MqttError as error:
            _logger.error(
                "Error '%s'. Reconnecting in %s seconds.", error, reconnect_interval
            )
        finally:
            await asyncio.sleep(reconnect_interval)


asyncio.run(main())
