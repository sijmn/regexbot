import os
import regex as re
from collections import defaultdict, deque

from telethon import TelegramClient, events

SED_PATTERN = r'^s/((?:\\\S|[^/])+)/((?:\\\S|[^/])*)(/.*)?'
GROUP0_RE = re.compile(r'(?<!\\)((?:\\\\)*)\\0')

bot = TelegramClient(None, 6, 'eb06d4abfb49dc3eeb1aeb98ae0f581e')
bot.parse_mode = None

last_msgs = defaultdict(lambda: deque(maxlen=10))


def cleanup_pattern(match):
    from_ = match.group(1)
    to = match.group(2)

    to = to.replace('\\/', '/')
    to = GROUP0_RE.sub(r'\1\\g<0>', to)

    return from_, to


async def doit(message, match):
    fr, to = cleanup_pattern(match)

    try:
        fl = match.group(3)
        if fl is None:
            fl = ''
        fl = fl[1:]
    except IndexError:
        fl = ''

    # Build Python regex flags
    count = 1
    flags = 0
    for f in fl.lower():
        if f == 'i':
            flags |= re.IGNORECASE
        elif f == 'm':
            flags |= re.MULTILINE
        elif f == 's':
            flags |= re.DOTALL
        elif f == 'g':
            count = 0
        elif f == 'x':
            flags |= re.VERBOSE
        else:
            await message.reply('unknown flag: {}'.format(f))
            return

    def substitute(m):
        if not m.raw_text:
            return None

        s, i = re.subn(fr, to, m.raw_text, count=count, flags=flags)
        if i > 0:
            return s

    try:
        msg = None
        substitution = None
        if message.is_reply:
            msg = await message.get_reply_message()
            substitution = substitute(msg)
        else:
            for msg in reversed(last_msgs[message.chat_id]):
                substitution = substitute(msg)
                if substitution is not None:
                    break  # msg is also set

        if substitution is not None:
            return await msg.reply(substitution)

    except Exception as e:
        await message.reply('fuck me\n' + str(e))


@bot.on(events.NewMessage(pattern=SED_PATTERN))
@bot.on(events.MessageEdited(pattern=SED_PATTERN))
async def sed(event):
    message = await doit(event.message, event.pattern_match)
    if message:
        last_msgs[event.chat_id].append(message)

    # Don't save sed commands or we would be able to sed those
    raise events.StopPropagation


@bot.on(events.NewMessage)
async def catch_all(event):
    last_msgs[event.chat_id].append(event.message)


@bot.on(events.MessageEdited)
async def catch_edit(event):
    for i, message in enumerate(last_msgs[event.chat_id]):
        if message.id == event.id:
            last_msgs[event.chat_id][i] = event.message


if __name__ == '__main__':
    with bot.start(bot_token=os.environ['API_KEY']):
        bot.run_until_disconnected()
