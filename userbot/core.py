# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import time
import sys
import psutil
import asyncio
import platform
import traceback
from datetime import datetime
from userbot import util
from telethon import __version__

DELETE_TIMEOUT = 5
if not os.path.exists(ENV.DOWNLOAD_DIRECTORY):
    os.mkdir(ENV.DOWNLOAD_DIRECTORY)


@client.on(events(pattern="reload (?P<shortname>\w+)$"))
async def reload_module(event):
    await event.delete()
    shortname = event.pattern_match["shortname"]
    try:
        if shortname in client._modules:
            client.remove_module(shortname)
        client.load_module(shortname)
        msg = await event.respond(f"Successfully reloaded {shortname}")
        await asyncio.sleep(DELETE_TIMEOUT)
        await msg.delete()
    except Exception as e:
        trace_back = traceback.format_exc()

        logger.warn(f"Failed to (re)load {shortname}: {trace_back}")
        await event.respond(f"Failed to (re)load {shortname}: {e}")


@client.on(events(pattern="(?:unload) (?P<shortname>\w+)$"))
async def remove_module(event):
    await event.delete()
    shortname = event.pattern_match["shortname"]
    if shortname == "_core":
        msg = await event.respond(f"{shortname} can not be removed!")
    elif shortname in client._modules:
        client.remove_module(shortname)
        msg = await event.respond(f"Unloaded {shortname}")
    else:
        msg = await event.respond(f"{shortname} is not loaded!")
    await asyncio.sleep(DELETE_TIMEOUT)
    await msg.delete()


@client.on(events(pattern="load"))
async def install_module(event):
    if event.fwd_from:
        return
    if event.reply_to_msg_id:
        module = await event.get_reply_message()
        loaded = False
        while not loaded:
            try:
                downloaded_file_name = await client.download_media(
                    module,
                    client._module_path
                )
                if "(" not in downloaded_file_name:
                    client.load_module_from_file(
                        downloaded_file_name)
                    await event.edit("Loaded `{}`".format(os.path.basename(downloaded_file_name)))
                    loaded = True
                else:
                    client.remove_module(module.file.name[:-3])
                    os.remove(f"modules/" + str(module.file.name))
                    os.remove(downloaded_file_name)
                    await event.edit("`Module already exists, overwriting..`")
                    await asyncio.sleep(0.25)
            except Exception as e:
                os.remove(downloaded_file_name)
                return await event.edit(str(e))
    await asyncio.sleep(DELETE_TIMEOUT)
    await event.delete()


@client.on(events(pattern="share (.*)", allow_sudo=True))
async def share_module(event):
    if event.fwd_from:
        return
    mone = await event.edit("Searching for required file..")
    input_str = event.pattern_match.group(1)
    module = f"modules/{input_str}.py"
    if os.path.exists(module):
        start = datetime.now()
        c_time = time.time()
        await client.send_file(
            event.chat_id,
            module,
            force_document=True,
            supports_streaming=False,
            allow_cache=False,
            reply_to=event.message.id,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                util.progress(d, t, mone, c_time, "Sharing module..")
            )
        )
        end = datetime.now()
        ms = (end - start).seconds
        await mone.edit(f"Uploaded {input_str} in {ms} seconds.")
    else:
        await mone.edit("404: Module not found")
        await asyncio.sleep(2)
        await mone.delete()


@client.on(events(pattern="help ?(.*)", allow_sudo=True))
async def help(event):
    if event.fwd_from:
        return
    key = event.pattern_match.group(1)
    modcount = 1
    if not key:
        dividor = "// "
        msg = f"The-TG-Bot v3 Modules:\n{dividor}"
        for key in sorted(ENV.HELPER):
            msg += f"{key} {dividor}"
            modcount += 1
        msg += f"\n\nNumber of modules: **{modcount}**\nSend .help <module_name> to get help regarding a module."
        await event.edit(msg)
    else:
        msg = ""
        msg += f"Available commands for **{key}** module:\n\n"
        try:
            msg += ENV.HELPER[key]
        except KeyError:
            msg = f"**{key}** module doesnt exist!"
        await event.edit(msg)


@client.on(events(pattern="alive ?(.*)", allow_sudo=True))
async def alive(event):
    if event.fwd_from:
        return
    await event.edit("**// The-TG-Bot v3 is running //**\n**// Fetching userbot information //**")
    try:
        build_type = ENV.GITHUB_REPO_LINK.split()[1]
    except:
        build_type = "stable"
    help_string = f"**// The-TG-Bot v3 is running //**\n\n`User:` [{me.first_name or ''} {me.last_name or ''}](tg://user?id={me.id})\n`Github:` {ENV.GITHUB_REPO_LINK.split()[0]}\n`Build: {build} ({build_type})`\n\n**By** @justaprudev"
    await client.send_file(
        event.chat_id,
        caption=help_string,
        file=ENV.ALIVE_LOGO or "logo.png",
        force_document=False,
    )
    await event.delete()


@client.on(events(pattern="restart ?(.*)", allow_sudo=True))
async def _restart(message):
    args = message.pattern_match.group(1)
    await message.edit("```The-TG-Bot v3 has been restarted.\nTry .alive or .ping to check if its alive.```")
    client.sync(restart)  # await restart() random crash workaround


async def restart():
    await client.disconnect()
    os.execl(sys.executable, sys.executable, *sys.argv)


def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


ENV.HELPER.update({
    "core": "\
```.load <as_a_reply_to_a_module_file>```\
\nUsage: Load a specified module.\
\n\n```.reload <module_name>```\
\nUsage: Reload any module that was unloaded.\
\n\n```.unload <module_name>```\
\nUsage: Unload any loaded module.\
\n\n```.alive```\
\nUsage: Returns userbot's system stats and some general information.\
\n\n```.help <optional_module_name>```\
\nUsage: Returns help strings for various modules of this userbot.\
\n\n```.share <module_name>```\
\nUsage: Share any loaded module.\
\n\n```.restart```\
\nUsage: Restart the telegram client.\
"
})
