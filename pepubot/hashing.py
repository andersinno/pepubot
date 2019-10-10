import asyncio
import hashlib


async def sha256(data: bytes) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sha256, data)


def _sha256(data: bytes) -> str:
    hasher = hashlib.sha256(data)
    return hasher.hexdigest()
