import discord, pickle, os, random, shutil, sys
from typing import Any, List
from dotenv import load_dotenv
import const

load_dotenv()

testing = False # Set to True when testing, false when pushing to remote code
# testing = os.environ.get("TESTING")
token = os.environ.get("API_TOKEN")  # purposefully obfuscated

# set intents for bot
intents = discord.Intents.default()
intents.message_content = True
snipeBot = discord.Client(intents=intents)
current_channel = int(os.environ.get("TEST_CHANNEL")) if testing else int(os.environ.get("SNIPE_CHANNEL"))

# creates scores - only if ran on a new machine, or if scores reset for semester
if not os.path.exists('scores.pickle'):
    with open('scores.pickle', 'wb') as file:
        pickle.dump({}, file)
# create alltime - should only happen on first initalization or if it is deleted
if not os.path.exists('alltime.pickle'):
    with open('alltime.pickle', 'wb') as file:
        # base off of current scores.pickle
        try:
            with open('scores.pickle', 'rb') as reference:
                pickle.dump(pickle.load(reference), file)
        except FileNotFoundError:  # not sure why it wouldn't exist. Better safe than sorry. 
            pickle.dump({}, file)


@snipeBot.event
async def on_ready():
    print("Bot is ready.")
    mes = await snipeBot.fetch_channel(current_channel) if testing else await snipeBot.fetch_channel(os.environ.get("PING_CHANNEL"))
    await mes.send(f"Ready")


@snipeBot.event
async def on_message(message):
#    print(message.channel.id)
    print(current_channel)
    if (message.reference and "!undo" in message.content):
        author_role_ids = [role.id for role in message.author.roles]
        if int(os.environ.get("LEADS_ID")) not in author_role_ids:
            await message.channel.send("Only leads can undo snipes.")
        else:
            print("Undoing a snipe")
            await undo(await message.channel.fetch_message(message.reference.message_id))  # call this on parent message to grab all data
        return
    # check the following: robot isn't replying to itself, this message is in snipes, has an attachment, and an @ to tag someone
    elif (message.author.id == snipeBot.user.id 
        or message.channel.id != current_channel
        or len(message.attachments) == 0 
        or len(message.mentions) == 0 
        ):
        return
    # someone is sniping themselves
    elif message.author.id in [mention.id for mention in message.mentions] and len(message.attachments) != 0:
        print("Self-Snipe detected")
        await message.channel.send(random.choice(const.SELFSNIPE))  # make fun of them
        return
    print("A snipe has occured...")
    # await message.channel.send("Score keeping has not been implemented yet. Stay tuned...")
    verdict = await update_score(message)
    await message.channel.send(verdict)
    await update_score(message, True)
    return
    
    
async def update_score(message, alltime=False):
    """Update the snipe scores following the snipe. 
    This should update the score, and be accounted for in a person's head to head tallies. 
    If alltime is set to true, the alltime score will be updated instead of the regular score. """
    # the way this will be indexed: { sniper : sniper_stats, sniper : sniper_stats}
    # statistics: {total:int, deaths:int, playerID1:int, playerID2:int}

    # if sniper has never recorded a snipe, add them to the dictionary. 
    # every user ID is unique. this should be fine. 
    filename = 'alltime.pickle' if alltime else 'scores.pickle'

    sniper_id = message.author.id
    snipee_ids = [victim.id for victim in message.mentions]

    # make backup
    shutil.copy2(filename, (f"{filename}.bkp"))

    # grab the pickle file, unpickle it, make changes as needed to update score
    with open(filename, 'rb') as file:
        scores = pickle.load(file)

    sniper_stats = scores.get(sniper_id, {})
    sniper_stats['kills'] = sniper_stats.get('kills', 0) + len(snipee_ids)  # add as many kills as people were sniped
    sniper_stats['killstreak'] = sniper_stats.get('killstreak', 0) + len(snipee_ids)
    if alltime and sniper_stats.get('beststreak', 0) < sniper_stats.get('killstreak', 0):
        # only update if you're updating alltime AND current killstreak exceeds killstreak
        # mark that the current streak IS best streak (only exists to know when to undo beststreak)
        sniper_stats['beststreak'] = sniper_stats.get('beststreak', 0) + 1
        sniper_stats['iscurrentbest'] = True
    scores[sniper_id] = sniper_stats

    victims_snap = []
    # victims 
    for snipee_id in snipee_ids:
        sniper_stats[snipee_id] = sniper_stats.get(snipee_id, 0) + 1  # add a kill to head to head
        snipee_stats = scores.get(snipee_id, {})  # get death count
        snipee_stats['deaths'] = snipee_stats.get('deaths', 0) + 1  # update death count
        victims_snap.append(snipee_stats.get('killstreak', 0))
        snipee_stats['lastkillstreak'] = snipee_stats.get('killstreak', 0)
        snipee_stats['killstreak'] = 0  # snap killstreak
        snipee_stats['iscurrentbest'] = False  # as killstreak is snapped, it isn't the best 
        scores[snipee_id] = snipee_stats

    with open(filename, 'wb') as file:
        pickle.dump(scores, file)
    
    if alltime: return '' # if alltime no need to waste time on this calculation

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
                          scores[sniper_id].get('killstreak', 0),  # sniper killstreak
                          victims_snap
                          )

async def undo(message):
    """undo the snipe by working backwards - allows a snipe undo to occur later. 
    This method will undo the snipe of the current message passed through - NOT the parent message."""
    # grab original message, and undo the snipe. 
    # open both dictionaries to iterate over them. This logic is messy but avoids any crashes that could result from file not existing
    if not message.attachments or not message.mentions:
        await message.channel.send("Undo can only be called on a snipe message.")
        print("Snipe was called on an invalid message.")
        return
    await message.channel.send("Undoing snipe...")
    scoresheets = []  # this will be a list containing scores.pickle, alltime.pickle
    # all logic should assume two copies of dictionary are in play 
    try:
        with open('scores.pickle', 'rb') as file:
            scoresheets.append((pickle.load(file), 'scores.pickle'))  # grab scoresheet, and denote that its current
        if scoresheets[0] == {}:
            await message.channel.send("No scores exist for this semester yet. Attempting to remove from alltime scoring...")  # this is a hyper niche situation but could happen on semester reset
    except FileNotFoundError:
        await message.channel.send("scores.pickle not found. Please wait for bot to reset at Noon/Midnight to retry.")
        return
    try:
        with open('alltime.pickle', 'rb') as file:
            scoresheets.append((pickle.load(file), 'alltime.pickle'))  # grab scoresheet and denote its alltime
    except FileNotFoundError:
        await message.channel.send("No alltime scorefile can be found. If you're seeing this, something really fucked up.")
        return
    # this shouldn't be necessary?
    # now, go through this list, removing the snipe from each one
    victimcount = len(message.mentions)
    scoresheetsnipers = [(message.author.id, records[0].get(message.author.id, {})) for records in scoresheets]  # [(current, "scores"), (alltime, "alltime")]
    for _, scores in scoresheetsnipers:
        # sniper general
        scores['kills'] = scores.get('kills', victimcount) - victimcount
        scores['killstreak'] = max(scores.get('killstreak', victimcount) - victimcount, 0)
        if scores.get('iscurrentbest', False):  # this would only run on alltime
            scores['beststreak'] = scores.get('beststreak', victimcount) - victimcount  # this should never pull default value, but... lol
        # victim specific
        for victim in message.mentions:
            scores[victim.id] = scores.get(victim.id, 1) - 1

    victimlists = [[(victim.id, score[0].get(victim.id, {})) for victim in message.mentions] for score in scoresheets]  # grab scoresheets for all victims across both pickled dictionaries
    for victimscores in victimlists:
        for _, victimdict in victimscores:  # victimdict is each individual dictionary
            # how to do killstreak?
            victimdict['deaths'] = victimdict.get('deaths', 1) - 1  # remove death
            victimdict['killstreak'] = victimdict.get('lastkillstreak', 0)  # restore previous killstreak

    # TODO: all should be undone, now put back into files
    for index in range(len(scoresheets)):
        # as scoresheets is used to make both snipelist and victimlist indexes should match
        # snipe[index][0] is sniper id, snipe[index][1] is their dictionary
        scoresheets[index][0][scoresheetsnipers[index][0]] = scoresheetsnipers[index][1]  # sniper update
        for victimid, victimdict in victimlists[index]:
            scoresheets[index][0][victimid] = victimdict  # victim update
        with open(scoresheets[index][1], 'wb') as file:
            pickle.dump(scoresheets[index][0], file)
    
    await message.channel.send("Done.")
    return

async def getNicknames(message):
    """Expects a valid snipe message. 
    
    Returns: tuple containing:
    Sniper: str - First name of either nickname or discord name
    Snipee: list[str] - list of first names of snipe victims"""
    sniper = get_first_name(message.author)  
    snipee = [get_first_name(victim) for victim in message.mentions]
    return (sniper, snipee)

def get_first_name(nam):
    res, *_ = nam.display_name.strip().split(' ')
    return res


def single_kill_msg(sniper, snipee, killcount, h2h, death, sniper_killstreak, snapped):
    """Create the string the bot uses when a single person has been sniped. """
    # refactor later to just take scores dictionary as opposed to all these variables
    # kill = "snipe" if (sniper <= 1)
    kill = "snipe" if (killcount <= 1) else "snipes"
    time = "time" if (death <= 1) else "times"
    mess = (f"{sniper} sniped {snipee}!\n{sniper} has {killcount} {kill}, with {h2h} being against {snipee}.\n{snipee} has been sniped {death} {time}.")
    mess += (f"\n{sniper} now has a killstreak of {sniper_killstreak}.") if sniper_killstreak > 1 else ""
    mess += (f"\nOh no! {snipee} had their killstreak of {snapped} snapped! {random.choice(const.STREAKBREAK)}") if snapped > 1 else ""
    return mess

def multi_kill_msg(sniper, snipees, killcount, h2h, deaths, sniper_killstreak, snapped):
    # TODO: Add an update to sniper killstreak, as it will change. 
    intro = "Oh baby a triple!" if (len(snipees) == 3) else "Multisnipe!"
    obituary = (f"{sniper} has sniped ")  # lists kills
    death = ''
    snaplist = ''
    # generate informative part of kill message
    for x in range(len(snipees)):
        time = "time" if (h2h[x] <= 1) else "times"
        obituary += f"{snipees[x]} {h2h[x]} {time}, " + ("and " if x == (len(snipees) - 2) else '')
        time = "time" if (int(deaths[x]) <= 1) else "times"
        death += (f"{snipees[x]} has been sniped {deaths[x]} {time}. ")
        snaplist += (f"{snipees[x]} had their killstreak of {snapped[x]} snapped. ") if snapped[x] > 1 else ''
        pass
    obituary = obituary[:-2] + '.'
    killstreak = (f"{sniper} now has a killstreak of {sniper_killstreak}.")
    return (f"""{intro} {sniper} has sniped {readable_list(snipees)}.\n{sniper} has {killcount} snipes.\n{obituary}\n{death}\n{snaplist}\n{killstreak}""")
        

def readable_list(s):
  if len(s) < 3:
    return ' and '.join(map(str, s))
  *a, b = s
  return f"{', '.join(map(str, a))}, and {b}"

snipeBot.run(token)
