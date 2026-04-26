import discord
import aiohttp
import re
import os
import json
from urllib.parse import urlparse, parse_qs

URL_REGEX = r'https?://[^\s]+'
NORMALIZED_GOOFISH_REGEX = r'https://h5\.m\.goofish\.com/item\?id=\d+'

# Load prior successful conversions, if available - Used in bot status - May need to manually create empty touch.json at first boot
def load_counter():
    if not os.path.exists("count.json"):
        return {}
    with open("count.json", 'r') as c:
        try:
            counters = json.load(c)
        except json.JSONDecodeError:
            counters = {}
    return counters

# Write to count.json
def save_counter(counters):
    with open("count.json", 'w') as c:
        json.dump(counters, c, indent=4)

# "FUCK tb links" - Nicks emporium, probably.
async def convert_tb_link(tb_url: str) -> str | None:
    try:
        # Request tb url
        async with aiohttp.ClientSession() as session:
            async with session.get(tb_url, allow_redirects=True, timeout=10) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

        # Is it what we're looking for? - No? Then i dont CARE. (Ideally shouldnt happen)
        match = re.search(r"var url\s*=\s*'(.*?)';", html)
        if not match:
            return None

        # Yes? Get that shit.
        extracted_url = match.group(1)
        parsed = urlparse(extracted_url)
        query_params = parse_qs(parsed.query)

        # If it STILL somehow isnt what we're looking for.
        if "id" not in query_params:
            return None

        # Mmmmmmm, Links.
        item_id = query_params["id"][0]
        return f"https://h5.m.goofish.com/item?id={item_id}"

    # Proper error handling? Whats that.
    except Exception:
        return None

# Stupid fucking goofish urlss and their long ass parameters.
def normalize_goofish_url(url: str) -> str | None:

    try:
        parsed = urlparse(url)

        # Genuinely cant remember what i was cooking here but it works so i dont care
        path_match = re.search(r'/item/(\d+)', parsed.path)
        if path_match:
            return f"https://h5.m.goofish.com/item?id={path_match.group(1)}"

        query_params = parse_qs(parsed.query)

        if "id" in query_params:
            return f"https://h5.m.goofish.com/item?id={query_params['id'][0]}"

        if "itemId" in query_params:
            return f"https://h5.m.goofish.com/item?id={query_params['itemId'][0]}"

        return None

    except Exception:
        return None

# Here we go
class MyClient(discord.Client):

    # Init
    async def on_ready(self):
        print(f'Logged in as {self.user}, ready.')

    # The business
    async def on_message(self, message):

        # Ping
        if client.user.mentioned_in(message):
            print(f"ℹ️ Activity: Gm. From: {message.author}.")
            await message.channel.send("Gm")

        # No bot processing
        if message.author == self.user:
            return

        # Is it a URL we like? No? then i dont CARE.
        urls = re.findall(URL_REGEX, message.content)
        if not urls:
            return

        converted_urls = []

        # This is where the fun begins
        for url in urls:

            # Regex time
            if re.fullmatch(NORMALIZED_GOOFISH_REGEX, url):
                continue

            # Execute www.goofish conversion
            if "goofish.com" in url:
                await message.edit(suppress=True)

                normalized = normalize_goofish_url(url)
                if normalized:
                    converted_urls.append(normalized)
                else:
                    await message.channel.send(f"{message.author.mention} ⚠️ Invalid or malformed goofish URL.")
                    return
                    
            # Execute m.tb.cn conversion
            elif "m.tb.cn" in url:
                await message.edit(suppress=True)

                loading = self.get_emoji(1475282054274089081)
                if loading:
                    try:
                        await message.add_reaction(loading)
                    except discord.HTTPException:
                        pass

                converted = await convert_tb_link(url)

                # Converted? Proceed or error.
                if converted:
                    converted_urls.append(converted)
                else:
                    await message.channel.send(f"{message.author.mention} ⚠️ Invalid or Expired tb URL.")

                    # Remove silly loading indicator when complete
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    return

        # Successful convert
        if converted_urls:

            # Reply with conversion
            await message.channel.send("\n".join(converted_urls))
            counters = load_counter()

            # Set or Increment success count
            if "success" not in counters:
                counters["success"] = 0
            counters["success"] += 1
            save_counter(counters)

            # Push count update
            await client.change_presence(activity=discord.Game(f"{counters["success"]} Links fixed!"))
            print(f"ℹ️ Activity: Fixed {counters["success"]} Links. Issued by {message.author}.")

        # No reactions, get rid of them.
        try:
            await message.clear_reactions()
        except:
            pass


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents, activity=discord.Game("Looking for goofish url..."))
client.run('')