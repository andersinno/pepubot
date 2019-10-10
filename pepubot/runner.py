import asyncio
import re
from enum import Enum
from typing import Any, List, Mapping, Optional

import slack

from .lottery_box import get_lottery_box
from .messages import Message, MessageInfo
from .storage import get_default_storage
from .userinfo import get_username

ENTRY_ACCEPTED_EMOJI = 'heavy_check_mark'
ENTRY_SKIPPED_EMOJI = 'white_check_mark'


class PePuState(Enum):
    not_started = 'not_started'
    running = 'running'
    picking_winner = 'picking_winner'


class PePuRunner:
    def __init__(self, slack_client: slack.WebClient) -> None:
        self.slack = slack_client
        self.state: PePuState = PePuState.not_started
        self.start_message: Optional[MessageInfo] = None
        self.round_participants: List[str] = []
        self._lock = asyncio.Lock()

    async def feed_message(self, event_data: Mapping[str, Any]) -> None:
        message = Message.from_message_event(event_data)
        if not message:
            return

        await self._load()

        await self._handle_message(message)

    async def _handle_message(self, message: Message) -> None:
        if self.is_dump_lottery_box_command(message):
            await self.dump_lottery_box(message)
            return

        if self.state == PePuState.not_started:
            if self.is_pepu_start_message(message):
                await self.start_pepu(message)
            return

        await self._handle_message_during_running(message)

    async def _handle_message_during_running(self, message: Message) -> None:
        assert self.start_message

        if message.channel != self.start_message.channel:
            await self.handle_non_pepu_channel_message(message)
            return

        if self.state == PePuState.running:
            if message.media_urls:
                await self.handle_message_with_media(message)
            elif message.urls_in_text:
                await self.handle_message_with_bare_urls(message)
            elif self.is_pepu_end_message(message):
                await self.end_pepu(message)
        elif self.state == PePuState.picking_winner:
            cleaned_text = message.text.strip().strip('.')
            if cleaned_text.isdigit():
                await self.pick_winner(message, int(cleaned_text))

    def is_pepu_start_message(self, message: Message) -> bool:
        """
        Check if the given messge is a PePu starting command.
        """
        return re.match(
            r'^('
            r'(pepu (is )?(open|start|begin|on\b)'
            r')|('
            r'(open|start|begin)(ing)? pepu)'
            r')',
            message.text.strip(),
            re.IGNORECASE) is not None

    def is_pepu_end_message(self, message: Message) -> bool:
        """
        Check if given message is a PePu ending command.
        """
        if not self.start_message:
            # Only started PePu can be ended
            return False
        if message.author != self.start_message.author:
            # Only PePu starter can end it
            return False
        return re.match(
            r'^('
            r'(pepu ((is|has) )?(now )?(over\b|end|off)'
            r')|('
            r'(end|stop|kill) pepu)'
            r')',
            message.text.strip(),
            re.IGNORECASE) is not None

    async def start_pepu(self, message: Message) -> None:
        async with self._lock:
            self.start_message = message.info
            self.state = PePuState.running
            await self._save()
        await self.say('PePu is on!')

    async def say(self, text: str) -> None:
        assert self.start_message
        await self.slack.chat_postMessage(
            channel=self.start_message.channel, text=text)

    async def handle_non_pepu_channel_message(self, message: Message) -> None:
        if self.is_pepu_start_message(message) or (
                self.is_pepu_end_message(message)):
            await self.slack.chat_postMessage(
                channel=message.channel,
                text='Sorry! Currently running PePu on another channel.')

    async def handle_message_with_media(self, message: Message) -> None:
        if message.author in self.round_participants:
            added_participant = False
        else:
            added_participant = await self.add_participant(message)

        try:
            await self.slack.reactions_add(
                name=(ENTRY_ACCEPTED_EMOJI if added_participant else
                      ENTRY_SKIPPED_EMOJI),
                channel=message.channel,
                timestamp=message.ts)
        except slack.errors.SlackApiError as error:
            # Ignore already_reacted errors and re-raise everything else
            if not isinstance(error.response, dict) or (
                    error.response.get('error') != 'already_reacted'):
                raise

    async def add_participant(self, message: Message) -> bool:
        async with self._lock:
            if message.author in self.round_participants:
                return False

            username = await get_username(self.slack, message.author)
            box = await get_lottery_box()
            if not self.round_participants:
                # Add a new version of the lottery box for the new round
                await box.save(add_new_version=True)
            await box.add_ticket(message.info, username)

            self.round_participants.append(message.author)
            await self._save()
            return True

    async def handle_message_with_bare_urls(self, message: Message) -> None:
        pass  # TODO: Should we notify that these are not counted?

    async def end_pepu(self, message: Message) -> None:
        # Make sure new participants are not being added while we are in
        # middle of ending the PePu round
        async with self._lock:
            if self.state != PePuState.running:
                return  # Already (being) ended

            box = await get_lottery_box()

            if not box.tickets:
                await self.say('No tickets, no winners.')
                self.state = PePuState.not_started
                self.start_message = None
                self.round_participants = []
            else:
                # TODO: Clean-up deactivated Slack users
                await box.shuffle()
                box_checksum = await box.get_checksum()
                max_number = len(box.tickets)
                participants_in_box = len(
                    set(x.owner_user_id for x in box.tickets))
                await self.say(f'Ending PePu round.')
                await self.say(
                    f'Added {len(self.round_participants)} new tickets '
                    f'to the lottery box. '
                    f'There are currently {len(box.tickets)} tickets from '
                    f'{participants_in_box} participants. '
                    f'Box checksum is {box_checksum}')
                await self.say(
                    f'Choose a number from *1 to {max_number}* '
                    f'to pick the winning ticket.')
                self.state = PePuState.picking_winner

            await self._save()

    async def pick_winner(self, message: Message, number: int) -> None:
        async with self._lock:
            if self.state != PePuState.picking_winner:
                return

            box = await get_lottery_box()

            if number < 1 or number > len(box.tickets):
                await self.say("That isn't in the specified range. Try again.")
                return

            ticket = box.tickets[number - 1]
            winner = ticket.owner_user_id
            winner_ticket_count = len(
                [x for x in box.tickets if x.owner_user_id == winner])

            await self.say(
                f'Winning ticket is {ticket.id} from {ticket.created_at}. '
                f'The winner had {winner_ticket_count} tickets in the box...')
            await asyncio.sleep(3)
            await self.say(':drumroll: :drumroll: :drumroll:')
            await asyncio.sleep(7)
            await self.say(f'The winner is <@{winner}>! :tada:')
            link_to_ticket_origin = await self.get_permalink(
                channel=ticket.source_message_channel,
                ts=ticket.source_message_ts)
            await self.say(
                f'The winning ticket was created from this message: '
                f'<{link_to_ticket_origin}>')

            await box.save(add_new_version=True)
            await box.remove_tickets_of_person(winner)

            self.state = PePuState.not_started
            self.start_message = None
            self.round_participants = []
            await self._save()

    async def get_permalink(self, *, channel: str, ts: str) -> str:
        response = await self.slack.chat_getPermalink(
            channel=channel, message_ts=ts)
        permalink = response.data.get('permalink')
        assert isinstance(permalink, str)
        return permalink

    def is_dump_lottery_box_command(self, message: Message) -> bool:
        return re.match(
            r'dump ((prev(ious)?)|current)? *(lottery )?box',
            message.text, re.IGNORECASE) is not None

    async def dump_lottery_box(self, message: Message) -> None:
        async with self._lock:
            if self.state == PePuState.picking_winner:
                text = 'Cannot dump the lottery box while picking winner'
            else:
                to_dump = (
                    'current' if (
                        'current' in message.text or 'now' in message.text or (
                            self.state == PePuState.running
                            and 'prev' not in message.text)) else 'previous')
                from_back = {'current': 1, 'previous': 2}[to_dump]
                when = 'in the last lottery' if from_back == 2 else 'right now'
                storage = get_default_storage()
                box_versions = await storage.get_all_versions('lottery_box')
                version = box_versions[-from_back]
                if len(box_versions) < from_back:
                    text = 'There is no lottery box yet'
                else:
                    text = (
                        f'The lottery box contents {when}:\n'
                        '```' + '\n'.join(version.value) + '```')
            await self.slack.chat_postMessage(
                channel=message.channel, text=text)

    async def _load(self) -> None:
        storage = get_default_storage()

        async with self._lock:
            state = await storage.get_item('runner_state')
            start_message = await storage.get_item('runner_start_message')
            participants = await storage.get_item('runner_round_participants')

        self.state = PePuState(state or PePuState.not_started.value)

        self.start_message = (
            None if not start_message else
            MessageInfo(*start_message.split(' ')))

        self.round_participants = (participants or '').splitlines()

    async def _save(self) -> None:
        storage = get_default_storage()
        await storage.store_item('runner_state', self.state.value)
        await storage.store_item('runner_start_message', (
            ' '.join(self.start_message) if self.start_message else ''))
        await storage.store_item('runner_round_participants', (
            '\n'.join(self.round_participants)))
