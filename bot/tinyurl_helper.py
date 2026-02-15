import aiohttp

async def shorten_url(long_url):
    """
    Shortens a URL using TinyURL.
    Returns the short link if successful, otherwise returns the original long link.
    """
    api_url = f"http://tinyurl.com/api-create.php?url={long_url}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"❌ TinyURL Error: {response.status}")
                    return long_url
    except Exception as e:
        print(f"❌ TinyURL Exception: {e}")
        return long_url
