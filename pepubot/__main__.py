import argparse
import asyncio
import logging
import sys
from typing import Any, Sequence

from . import slack
from .runner import PePuRunner
from .settings import initialize_settings

LOG = logging.getLogger(__name__)


def main(argv: Sequence[str] = sys.argv) -> None:
    args = parse_args(argv)
    initialize_settings(args.config_file)
    logging.basicConfig(level=logging.INFO)
    run_pepubot()


def parse_args(argv: Sequence[str]) -> Any:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config-file', '-c', default='pepubot.conf',
        help='Path to configuration file')
    return parser.parse_args(argv[1:])


def run_pepubot() -> None:
    LOG.info('Initializing the Slack RTM client')
    slack_rtm_client = slack.get_rtm_client()

    LOG.info('Creating PePuRunner with a Slack Web client')
    slack_web_client = slack.get_web_client()
    pepu_runner = PePuRunner(slack_web_client)

    LOG.info('Binging our event handler')
    slack_rtm_client.on(event='message', callback=pepu_runner.feed_message)

    LOG.info('Starting the Slack RTM session in an event loop')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(slack_rtm_client.start())


if __name__ == '__main__':
    main()
