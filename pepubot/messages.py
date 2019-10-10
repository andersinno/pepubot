from __future__ import annotations

import re
from typing import Any, List, Mapping, NamedTuple, Optional


class MessageId(NamedTuple):
    channel: str
    ts: str  # Slack timestamp


class MessageInfo(NamedTuple):
    channel: str
    ts: str  # Slack timestamp
    author: str  # Slack user id


class Message(NamedTuple):
    channel: str
    ts: str  # Slack timestamp
    author: str  # Slack user id
    text: str
    urls_in_text: List[str]
    media_urls: List[str]

    @classmethod
    def from_message_event(
            cls,
            data: Mapping[str, Any],
    ) -> Optional[Message]:
        return _parse_message_data(data)

    @property
    def id(self) -> MessageId:
        return MessageId(self.channel, self.ts)

    @property
    def info(self) -> MessageInfo:
        return MessageInfo(self.channel, self.ts, self.author)


def _parse_message_data(data: Mapping[str, Any]) -> Optional[Message]:
    message = data

    subtype = data.get('subtype')
    submessage = data.get('message')
    if subtype == 'message_changed' and isinstance(submessage, dict):
        message = submessage
    elif subtype:
        # We're only interested in regular "message" or
        # "message_changed" events
        return None

    channel = data.get('channel')
    author = message.get('user')
    ts = message.get('ts')
    text = message.get('text')

    if not channel or not author or not ts or text is None:
        return None

    return Message(
        channel=channel,
        ts=ts,
        author=author,
        text=text,
        urls_in_text=re.findall(r'<(https?://[^>]+)>', text),
        media_urls=_collect_media_urls(message),
    )


def _collect_media_urls(message: Mapping[str, Any]) -> List[str]:
    media_urls: List[str] = []

    attachments = message.get('attachments', [])
    for attachment in attachments:
        image_url = attachment.get('image_url')
        if image_url:
            media_urls.append(image_url)

        video_url = attachment.get('video_url')
        if video_url:
            media_urls.append(video_url)

        original_url = attachment.get('original_url')
        if original_url and attachment.get('video_html'):  # YouTube etc.
            media_urls.append(original_url)

    files = message.get('files', [])
    for file in files:
        if file.get('mimetype', '').startswith(('image/', 'video/')):
            permalink = file.get('permalink')
            if permalink:
                media_urls.append(permalink)

    return media_urls
