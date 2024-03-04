import requests, guilded, asyncio # i hate python import bullshit
from guilded.ext import commands

token = ''  # apikey.txt
snipeBot = guilded.Client()

allowed_channels = []  # also in apikey.txt
# when a message is sent into snipes, check if the bot should act on it. 

@snipeBot.event
async def on_ready():
    print("Bot is ready.")
    mes = await snipeBot.fetch_channel(allowed_channels[1])
    await mes.send(f"Bot is initialized and is listening...")


@snipeBot.event
async def on_message(message):
    # check the following: robot isn't replying to itself, this message is in snipes, has an attachment, and an @ to tag someone
    if (message.author.id == snipeBot.user.id or message.channel_id not in allowed_channels  
        or len(message.attachments) == 0 or len(message.mentions) == 0):
        print("no snipe")
        # await message.channel.send(f"Message would not trigger a snipe...")
        return
    else:
        print("A snipe has occured...")
        await message.channel.send(f"Snipe!")

snipeBot.run(token)
