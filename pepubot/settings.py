from __future__ import annotations

import os
import shlex
from os.path import expanduser
from typing import Dict, Mapping, Optional

_DEFAULT_SETTINGS_FILE_PATH = 'pepubot.conf'

_settings_instance: Optional[Settings] = None


def initialize_settings(
        settings_file: str = _DEFAULT_SETTINGS_FILE_PATH,
        env: Mapping[str, str] = os.environ,
) -> Settings:
    global _settings_instance
    if _settings_instance:
        raise RuntimeError('Settings are already initialized')
    _settings_instance = Settings(settings_file, env)
    return _settings_instance


def get_settings() -> Settings:
    global _settings_instance
    if not _settings_instance:
        return initialize_settings()
    return _settings_instance


class Settings:
    SLACK_API_TOKEN: str
    STORAGE_FILE: str = expanduser('~/pepubot-data.json')
    TIMEZONE: str = 'UTC'

    def __init__(
            self,
            settings_file: str,
            env: Mapping[str, str] = os.environ,
    ) -> None:
        self.settings_file = settings_file
        self._settings_file_variables: Optional[Dict[str, str]] = None
        for name in self.__annotations__:
            value: Optional[str] = env.get(name)
            if value is None:
                value = self._get_settings_file_variables().get(name)
                if value is None:
                    value = getattr(type(self), name, None)
                    if value is None:
                        raise RuntimeError(f'No value provided for {name}')
            assert isinstance(value, str)
            setattr(self, name, value)

    def _get_settings_file_variables(self) -> Dict[str, str]:
        if self._settings_file_variables is not None:
            return self._settings_file_variables

        if not os.path.exists(self.settings_file):
            self._settings_file_variables = {}
            return self._settings_file_variables

        result: Dict[str, str] = {}
        with open(self.settings_file, 'rt', encoding='utf-8') as fp:
            for line in fp:
                sline = line.strip()
                if not sline or sline.startswith('#'):
                    continue
                (name, value) = sline.split('=', 1)
                result[name] = shlex.split(value)[0]
        self._settings_file_variables = result
        return result
