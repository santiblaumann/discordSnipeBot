import guilded, csv # i hate python import bullshit
import const

token = const.API_TOKEN  # purposefully obfuscated
snipeBot = guilded.Client()

allowed_channels = const.ALLOWED_CHANNELS
# when a message is sent into snipes, check if the bot should act on it. 

@snipeBot.event
async def on_ready():
    print("Bot is ready.")
    mes = await snipeBot.fetch_channel(allowed_channels[1])  # note initialization in test channel
    await mes.send(f"Bot is initialized and is listening...")


@snipeBot.event
async def on_message(message):
    # check the following: robot isn't replying to itself, this message is in snipes, has an attachment, and an @ to tag someone
    if message.author.id == snipeBot.user.id:
        return
    elif (message.channel_id not in allowed_channels  
        or len(message.attachments) == 0 or len(message.mentions) == 0):
        print("no snipe")
        return
    else:
        print("A snipe has occured...")
        result = await snipe_message(message)
        await message.channel.send(result)
        await update_score(message)

async def snipe_message(message):
    serv = message.server
    sniper = await serv.fetch_member(message.author.id)
    snipee = await serv.fetch_member(message.mentions[0].id)
    try:
        sniper, _ = (sniper.nick).split(' ') if ' ' in sniper.nick else [sniper.nick, '']  # if string has a space get just first name, otherwise leave alone
        snipee, _ = (snipee.nick).split(' ') if ' ' in snipee.nick else [snipee.nick, '']  # same deal here. 
    except:  # if one of them has nick set to None, trigger this as the above would probably fail. 
        sniper = sniper.nick
        snipee = snipee.nick
    if sniper == None or snipee == None:
        return "One of you is missing a nickname. I am beyond upset..."
    return sniper + " sniped " + snipee + ". Brutal..."
    # return "Brutal..."

async def update_score(message):
    """Update the snipe scores following the snipe. 
    This should update the semester score, all time score,
    and be accounted for in a person's head to head tallies. """
    serv = message.server
    sniper = await serv.fetch_member(message.author.id)
    snipee = await serv.fetch_member(message.mentions[0].id)


snipeBot.run(token)
