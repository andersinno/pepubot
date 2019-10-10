import slack

from .settings import get_settings


def get_web_client() -> slack.WebClient:
    return slack.WebClient(
        token=get_settings().SLACK_API_TOKEN,
        run_async=True,
    )


def get_rtm_client() -> slack.RTMClient:
    return slack.RTMClient(
        token=get_settings().SLACK_API_TOKEN,
        run_async=True,
    )
