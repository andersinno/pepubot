from typing import Any, Dict

import slack

UserInfoDict = Dict[str, Any]

_userinfo_cache: Dict[str, UserInfoDict] = {}


async def get_username(slack_client: slack.WebClient, user_id: str) -> str:
    userinfo = await _get_userinfo(slack_client, user_id)
    username = userinfo.get('name')
    if not isinstance(username, str):
        raise RuntimeError(
            f'Slack returned invalid username: {username!r}')
    return username


async def _get_userinfo(
        slack_client: slack.WebClient,
        user_id: str,
) -> UserInfoDict:
    userinfo = _userinfo_cache.get(user_id)
    if userinfo is None:
        response = await slack_client.users_info(user=user_id)
        userinfo = response.data.get('user')
        if not isinstance(userinfo, dict):
            raise RuntimeError('Slack returned invalid userinfo response')
        _userinfo_cache[user_id] = userinfo
    return userinfo
