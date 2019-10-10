# -*- coding: utf-8 -*-
# type: ignore

import pytest

from ..messages import Message
from ..runner import PePuRunner


@pytest.mark.parametrize('text,expected_result', [
    ('pepu open', True),
    ('PePu starts!', True),
    ('pepu is on', True),
    ('pepu is opening', True),
    ('pepU starts now.', True),
    ('Open PePu.', True),
    ('Start PePuing right now!', True),
    ('Begin pepu', True),
    ('No pepu today.', False),
    ('Pepu skipped today.', False),
    ('Ei Pepua tänään.', False),
    ('Sorry, no pepu.', False),
    ('forget pepu', False),
    ('I love pepu', False),
    ('kunnia pepulle', False),
])
def test_is_pepu_start_message(text, expected_result):
    message = Message(
        channel='', ts='', author='',
        text=text, urls_in_text=[], media_urls=[])
    runner = PePuRunner(None)

    result = runner.is_pepu_start_message(message)

    assert result is expected_result
