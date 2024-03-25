import guilded, pickle, os
from typing import Any, List
import const

token = const.API_TOKEN  # purposefully obfuscated
snipeBot = guilded.Client()
allowed_channels = const.ALLOWED_CHANNELS
if not os.path.exists('scores.pickle'):
    with open('scores.pickle', 'wb') as file:
        pickle.dump({}, file)
# when a message is sent into snipes, check if the bot should act on it. 

@snipeBot.event
async def on_ready():
    print("Bot is ready.")
    mes = await snipeBot.fetch_channel(allowed_channels[1])  # note initialization in test channel
    await mes.send(f"Live for score testing.")
    # mes2 = await snipeBot.fetch_channel(allowed_channels[0])
    # await mes2.send(f"Live with very rudamentary features.")


@snipeBot.event
async def on_message(message):
    # check the following: robot isn't replying to itself, this message is in snipes, has an attachment, and an @ to tag someone
    if (message.author.id == snipeBot.user.id 
        or message.channel_id not in allowed_channels  
        or len(message.attachments) == 0 
        or len(message.mentions) == 0
        ):
        return
    print("A snipe has occured...")
    # await message.channel.send("Score keeping has not been implemented yet. Stay tuned...")
    verdict = await update_score(message)
    await message.channel.send(verdict)
    return


async def update_score(message):
    """Update the snipe scores following the snipe. 
    This should update the score, and be accounted for in a person's head to head tallies. """
    # the way this will be indexed: { sniper : sniper_stats, sniper : sniper_stats}
    # statistics: {total:int, deaths:int, playerID1:int, playerID2:int}

    # if sniper has never recorded a snipe, add them to the dictionary. 
    # every user ID is unique. this should be fine. 

    sniper_id = message.author.id
    snipee_ids = [victim.id for victim in message.mentions]

    # grab the pickle file, unpickle it, make changes as needed to update score
    with open('scores.pickle', 'rb') as file:
        scores = pickle.load(file)

    sniper_stats = scores.get(sniper_id, {})
    sniper_stats['kills'] = sniper_stats.get('kills', 0) + len(snipee_ids)  # add as many kills as people were sniped
    sniper_stats['killstreak'] = sniper_stats.get('killstreak', 0) + len(snipee_ids)  # update sniper killstreak
    scores[sniper_id] = sniper_stats

    victims_snap = []
    # victims 
    for snipee_id in snipee_ids:
        sniper_stats[snipee_id] = sniper_stats.get(snipee_id, 0) + 1  # add a kill to head to head

        snipee_stats = scores.get(snipee_id, {})  # get death count
        snipee_stats['deaths'] = snipee_stats.get('deaths', 0) + 1  # update death count
        victims_snap.append(snipee_stats.get('killstreak', 0))
        snipee_stats['killstreak'] = 0  # snap killstreak
        scores[snipee_id] = snipee_stats

    with open('scores.pickle', 'wb') as file:
        pickle.dump(scores, file)
    
    sniper_nick, snipee_nick = await getNicknames(message)
    if len(snipee_ids) == 1:
        return single_kill_msg(sniper_nick, # sniper
                               snipee_nick[0], # victim
                               scores[sniper_id].get('kills', 1), # sniper total kill count
                               scores[sniper_id].get(snipee_ids[0], 0),  # h2h
                               scores[snipee_ids[0]].get('deaths', 1),  # deaths
                               scores[sniper_id].get('killstreak', 1),  # killstreak
                               victims_snap[0])  # snapped victim killstreak (if only 1 victim this is fine, multi will have a list)
                             
    
    head2heads = [scores[sniper_id].get(snipee_id, 1) for snipee_id in snipee_ids]
    deaths = [scores[snipee_id].get('deaths', 1) for snipee_id in snipee_ids]
    return multi_kill_msg(sniper_nick, # sniper
                          snipee_nick, # victims
                          scores[sniper_id].get('kills', 1), # sniper total kill count
                          head2heads,  #h2h list
                          deaths,  # deaths count
                          victims_snap
                          )

async def getNicknames(message):
    """Expects a valid snipe message. """
    # snipee should be a list. 
    serv = message.server
    sniper = await serv.fetch_member(message.author.id)
    snipee = [await serv.fetch_member(mention.id) for mention in message.mentions]
    sniper = get_first_name(sniper)
    snipee = [get_first_name(id) for id in snipee]
    return (sniper, snipee)

def get_first_name(nam):
    try:
        res, *_ = nam.nick.strip().split(' ')
    except AttributeError:
        res, *_ = nam.name.strip().split(' ')
    return res

def single_kill_msg(sniper, snipee, killcount, h2h, death, streak_sniper, snapped):
    # refactor later to just take scores dictionary as opposed to all these variables
    # kill = "snipe" if (sniper <= 1)
    kill = "snipe" if (killcount <= 1) else "snipes"
    time = "time" if (death <= 1) else "times"
    mess = (f"{sniper} sniped {snipee}!\n{sniper} has {killcount} {kill}, with {h2h} being against {snipee}.\n{snipee} has been sniped {death} {time}.")
    mess += (f"\n{sniper} now has a killstreak of {streak_sniper}.") if streak_sniper > 1 else ""
    mess += (f"\nOh no! {snipee} had their killstreak of {snapped} snapped! Womp womp.") if snapped > 1 else ""
    return mess

def multi_kill_msg(sniper, snipees, killcount, h2h, deaths, snapped):
    intro = "Oh baby a triple!" if (len(snipees) == 3) else "Multisnipe!"
    obituary = (f"{sniper} has sniped ")  # funny name lol
    death = ''
    snaplist = ''
    for x in range(len(snipees)):
        time = "time" if (h2h[x] <= 1) else "times"
        # grammar - last element will have "and" with oxford comma
        obituary += f"{snipees[x]} {h2h[x]} {time}, " + ("and " if x == (len(snipees) - 2) else '')
        time = "time" if (int(deaths[x]) <= 1) else "times"
        death += (f"{snipees[x]} has been sniped {deaths[x]} {time}. ")
        snaplist += (f"{snipees[x]} had their killstreak of {snapped[x]} snapped. ") if snapped[x] > 1 else ''
        pass
    obituary = obituary[:-2] + '.'
    return (f"""{intro} {sniper} has sniped {readable_list(snipees)}.\n{sniper} has {killcount} snipes.\n{obituary}\n{death}\n{snaplist}""")
        

def readable_list(s):
  if len(s) < 3:
    return ' and '.join(map(str, s))
  *a, b = s
  return f"{', '.join(map(str, a))}, and {b}"

snipeBot.run(token)
