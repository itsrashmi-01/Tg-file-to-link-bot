import aiohttp

async def shorten_url(long_url):
    api_url = f"http://tinyurl.com/api-create.php?url={long_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.text()
    except:
        return None