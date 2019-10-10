import asyncio
import json
import time
from typing import Dict, List, NamedTuple, Optional, Sequence

import aiofiles

from .settings import get_settings

_default_storage: Optional['Storage'] = None


def get_default_storage() -> 'Storage':
    global _default_storage
    if _default_storage is None:
        _default_storage = Storage(get_settings().STORAGE_FILE)
    return _default_storage


class Version(NamedTuple):
    timestamp: int  # nanoseconds since 1970-01-01T00:00:00Z
    value: Sequence[str]  # value splitted into lines


DataDict = Dict[str, List[Version]]

_load_cache: Dict[str, DataDict] = {}
_load_lock = asyncio.Lock()


class Storage:
    def __init__(self, filename: str) -> None:
        self.filename: str = filename
        self._data: Optional[DataDict] = None

    async def store_item(
            self, name: str,
            value: str,
            *,
            add_new_version: bool = False,
    ) -> None:
        versions: List[Version] = (await self._get_data()).setdefault(name, [])
        if not add_new_version and versions:
            versions.pop()  # Remove the last version
        versions.append(Version(time.time_ns(), value.split('\n')))
        await self._save()

    async def get_item(self, name: str) -> Optional[str]:
        versions = (await self._get_data()).get(name, [])
        return '\n'.join(versions[-1].value) if versions else None

    async def get_all_versions(self, name: str) -> Sequence[Version]:
        return (await self._get_data()).get(name, []).copy()

    async def _get_data(self) -> DataDict:
        if self._data is None:
            self._data = await self._load()
        return self._data

    async def _load(self) -> DataDict:
        cached = _load_cache.get(self.filename)
        if cached:
            return cached
        async with _load_lock:
            if self.filename in _load_cache:  # Re-check while locked
                return _load_cache[self.filename]
            try:
                async with aiofiles.open(
                        self.filename, 'rt', encoding='utf-8') as fp:
                    data = json.loads(await fp.read())
            except FileNotFoundError:
                result: DataDict = {}
            else:
                result = self._convert_data_type(data)
            _load_cache[self.filename] = result
        return result

    async def _save(self) -> None:
        async with aiofiles.open(self.filename, 'wt', encoding='utf-8') as fp:
            encoder = json.JSONEncoder(ensure_ascii=False, indent=2)
            for chunk in encoder.iterencode(self._data):
                await fp.write(chunk)

    @classmethod
    def _convert_data_type(cls, data: object) -> DataDict:
        if not isinstance(data, dict):
            raise TypeError('Storage should be a JSON dict')
        for name in data:
            if not isinstance(name, str):
                raise TypeError('Name of each item should be a string')
            versions = data[name]
            if not isinstance(versions, list):
                raise TypeError('Each name should contain a list of versions')
            for (n, version) in enumerate(versions):
                if not isinstance(version, (list, tuple)) or len(version) != 2:
                    raise TypeError('Each version should be a pair')
                (timestamp, value) = version
                if not isinstance(timestamp, int):
                    raise TypeError('First item of pair should be an integer')
                if not isinstance(value, list):
                    raise TypeError('Second item of pair should be a list')
                if not all(isinstance(x, str) for x in value):
                    raise TypeError('Each value should be a list of strings')
                versions[n] = Version(timestamp, value)
        return data
