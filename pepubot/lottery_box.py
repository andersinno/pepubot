import random
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

from dateutil.parser import parse as parse_datetime

from .hashing import sha256
from .messages import MessageInfo
from .storage import Storage, get_default_storage
from .times import now


async def get_lottery_box() -> 'LotteryBox':
    storage = get_default_storage()
    lottery_box_str = await storage.get_item('lottery_box')
    if lottery_box_str is None:
        return LotteryBox(storage=storage)
    return LotteryBox.from_string(lottery_box_str, storage=storage)


async def store_lottery_box(box: 'LotteryBox') -> None:
    await box.save(add_new_version=True)


@dataclass
class Ticket:
    number: int
    created_at: datetime
    source_message_channel: str
    source_message_ts: str
    owner_user_id: str
    owner_username: str

    def __str__(self) -> str:
        return ' '.join([
            self.id,
            f'{self.created_at.isoformat()}',
            f'{self.source_message_channel}',
            f'{self.source_message_ts}',
            f'{self.owner_user_id}',
            f'{self.owner_username}',
        ])

    @property
    def id(self) -> str:
        return f'T{self.number:05}'

    @classmethod
    def from_string(cls, string: str) -> 'Ticket':
        (num, created, msgch, msgts, uid, uname) = string.split(' ', 5)
        if not num.startswith('T'):
            raise ValueError(f'Not a Ticket string: {string}')
        return cls(
            number=int(num[1:]),
            created_at=parse_datetime(created),
            source_message_channel=msgch,
            source_message_ts=msgts,
            owner_user_id=uid,
            owner_username=uname,
        )


class LotteryBox:
    def __init__(
            self,
            tickets: Optional[Iterable[Ticket]] = None,
            next_ticket_number: int = 1,
            *,
            storage: Storage,
    ) -> None:
        assert tickets is None or (
            all(x.number < next_ticket_number for x in tickets))
        self.tickets: List[Ticket] = list(tickets or [])
        self.next_ticket_number = next_ticket_number
        self.storage = storage

    async def add_ticket(
            self,
            message_info: MessageInfo,
            username: str,
    ) -> Ticket:
        new_ticket = Ticket(
            number=self.next_ticket_number,
            created_at=now().replace(microsecond=0),
            source_message_channel=message_info.channel,
            source_message_ts=message_info.ts,
            owner_user_id=message_info.author,
            owner_username=username,
        )
        self.tickets.append(new_ticket)
        self.next_ticket_number += 1
        await self.save()
        return new_ticket

    async def shuffle(self) -> None:
        random.shuffle(self.tickets)
        await self.save()

    async def remove_tickets_of_person(self, user_id: str) -> List[Ticket]:
        removed: List[Ticket] = []
        new_tickets: List[Ticket] = []
        for ticket in self.tickets:
            if ticket.owner_user_id == user_id:
                removed.append(ticket)
            else:
                new_tickets.append(ticket)
        self.tickets = new_tickets
        await self.save()
        return removed

    async def save(self, *, add_new_version: bool = False) -> None:
        await self.storage.store_item(
            'lottery_box', self.to_string(), add_new_version=add_new_version)

    async def get_checksum(self) -> str:
        contents = self.to_string()
        return await sha256(contents.encode('utf-8'))

    def to_string(self) -> str:
        tickets_string = '\n'.join(
            f'{n:4} {x}' for (n, x) in enumerate(self.tickets, 1))
        next_num_string = f'next_ticket_number={self.next_ticket_number}'
        return '\n'.join([tickets_string, next_num_string])

    @classmethod
    def from_string(cls, string: str, storage: Storage) -> 'LotteryBox':
        lines = string.splitlines()
        tickets = [
            Ticket.from_string(x.strip().split(' ', 1)[-1])
            for x in lines[:-1]] if lines[0] and len(lines) >= 2 else []
        last_line = lines[-1]
        if not last_line.startswith('next_ticket_number='):
            raise ValueError('next_ticket_number is missing')
        next_ticket_num = int(last_line.split('=', 1)[-1].rstrip())
        return cls(
            tickets=tickets,
            next_ticket_number=next_ticket_num,
            storage=storage,
        )
