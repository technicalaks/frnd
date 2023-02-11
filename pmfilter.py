import asyncio
import re
import ast
import math
import datetime
import time
import string
import random
from datetime import datetime
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script, SECOND_VERIFY_COMPLETE_TEXT, SECOND_VERIFICATION_TEXT, VERIFICATION_TEXT
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, SUPPORT_GROUP, SUPPORT_CHAT, REQUESTS_CHANNEL, FILE_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, NOR_IMG, PICS, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, AUTO_FILTER, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, SPELL_IMG, SPELL_SUG_IMG, MSG_ALRT, FILE_FORWARD, MAIN_CHANNEL, LOG_CHANNEL, LOG_VR_CHANNEL, LOG_NOR_CHANNEL, TUTORIAL_LINK_1, TUTORIAL_LINK_2
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings, get_shortlink
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results, get_bad_files
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
from database.gfilters_mdb import (
    find_gfilter,
    get_gfilters,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}
FILTER_MODE = {}

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_filter(client, message):
    user_id = message.from_user.id
    user_verified = await db.is_user_verified(user_id)
    is_second_shortener = await db.use_second_shortener(user_id)
    how_to_download_link = TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1

    if not user_verified or is_second_shortener:
        verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        await db.create_verify_id(user_id, verify_id)
        buttons = [[InlineKeyboardButton(text="♻️ ᴄʟɪᴄᴋ ᴛᴏ ᴠᴇʀɪғʏ ♻️", url=await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}", is_second_shortener),),], [InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=how_to_download_link)]]
        reply_markup=InlineKeyboardMarkup(buttons)
        bin_text = SECOND_VERIFICATION_TEXT if is_second_shortener else VERIFICATION_TEXT
        dmb = await message.reply_text(
            text=(bin_text.format(message.from_user.mention)),
            protect_content = True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(120) 
        await dmb.delete()
        await message.delete()
        return
    kd = await global_filters(client, message)
    if kd == False:
        if AUTO_FILTER:
            await auto_filter(client, message)
    

@Client.on_message(filters.group & filters.text & filters.incoming)
async def pm_give_filter(client, message):
    await global_filters(client, message)
    if message.chat.id == SUPPORT_GROUP:
        k = await manual_filters(client, message)
        if k == False:
            await auto_filter(client, message)
    else:
        if AUTH_CHANNEL and not await is_subscribed(client, message):  
            try:
                invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
            except ChatAdminRequired:
                logger.error("Make sure bot is admin in forcesub channel.")
                return
            buttons = [[
                InlineKeyboardButton("🛠 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 🛠", url=invite_link.invite_link)
            ],[
                InlineKeyboardButton("♻️ ʀᴇǫᴜᴇsᴛ ᴀɢᴀɪɴ ♻️", callback_data="grp_checksub")
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            k = await message.reply_photo(photo='https://graph.org/file/d34e121171ae13536d93e.jpg',
                caption=f"🍀 ʜᴇʏ {message.from_user.mention},\n\nᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ʀᴇǫᴜᴇsᴛ ᴀɢᴀɪɴ ʙᴜᴛᴛᴏɴ👇",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )
            await asyncio.sleep(300)
            await message.delete()
            await k.delete()
        else:
            k = await manual_filters(client, message)
            if k == False:
                settings = await get_settings(message.chat.id)
            try:
                if settings['auto_filter']:
                    await auto_filter(client, message)
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_filter', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_filter']:
                    await auto_filter(client, message)

                
@Client.on_message(filters.private & filters.text & filters.incoming)
async def give_filter(client, message):
    if AUTH_CHANNEL and not await is_subscribed(client, message):  
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("Make sure bot is admin in forcesub channel.")
            return
        buttons = [[
            InlineKeyboardButton("🛠 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 🛠", url=invite_link.invite_link)
        ],[
            InlineKeyboardButton("♻️ ʀᴇǫᴜᴇsᴛ ᴀɢᴀɪɴ ♻️", callback_data="pm_checksub")
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        k = await message.reply_photo(
            photo='https://graph.org/file/d34e121171ae13536d93e.jpg',
            caption=f"🍀 ʜᴇʏ {message.from_user.mention},\n\nᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ʀᴇǫᴜᴇsᴛ ᴀɢᴀɪɴ ʙᴜᴛᴛᴏɴ👇",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )
        await asyncio.sleep(300)
        await message.delete()
        await k.delete()
    else:
        k = await manual_filters(client, message)
        if k == False:
            if AUTO_FILTER:
                await auto_filter(client, message)
                

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    reqnxt  = query.from_user.id if query.from_user else 0
    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"🐲 {get_size(file.file_size)}≽ {file.file_name}", callback_data=f'files#{reqnxt}#{file.file_id}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}", callback_data=f'files#{reqnxt}#{file.file_id}'
                ),
                InlineKeyboardButton(
                    text=f"🐲 {get_size(file.file_size)}",
                    callback_data=f'files#{reqnxt}#{file.file_id}',
                ),
            ]
            for file in files
        ]
    btn.insert(0, 
        [
            InlineKeyboardButton('⛔️ sᴜʙsᴄʀɪʙᴇ ᴏᴜʀ ʏᴛ ᴄʜᴀɴɴᴇʟ ⛔️', url='https://youtube.com/@technical_aks')
        ]
    )
    btn.insert(1, 
        [
             InlineKeyboardButton(f'♻️ ɪɴꜰᴏ', 'reqinfo'),
             InlineKeyboardButton(f'ᴍᴏᴠɪᴇ', 'minfo'),
             InlineKeyboardButton(f'sᴇʀɪᴇs', 'sinfo'),
             InlineKeyboardButton(f'⚜️ ᴛɪᴘs', 'tinfo')
        ]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"ᴘᴀɢᴇ {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f" {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()

#SpellCheck bug fixing

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movie = movies[(int(movie_))]
    await query.answer(script.TOP_ALRT_MSG)
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            reqstr1 = query.from_user.id if query.from_user else 0
            reqstr = await bot.get_users(reqstr1)
            if LOG_NOR_CHANNEL:
                await bot.send_message(chat_id=LOG_NOR_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, movie)))
                await bot.edit_message_media(
                    query.message.chat.id,
                    query.message.id,
                    InputMediaPhoto('https://graph.org/file/3db3a4e8f0bd159278e0d.jpg'))
            k = await query.message.edit(script.MVE_NT_FND)
            await asyncio.sleep(60)
            await k.delete()
            await query.message.reply_to_message.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer(MSG_ALRT)
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer(MSG_ALRT)

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer(MSG_ALRT)

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer(MSG_ALRT)
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer(MSG_ALRT)
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "gfilteralert" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_gfilter('gfilters', keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        # User Verifying
        user_id = query.from_user.id
        is_second_shortener = await db.use_second_shortener(user_id)
        if not await db.is_user_verified(user_id) or is_second_shortener:
            verify_id = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=7)
            )
            how_to_download_link = (
                TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
            )
            await db.create_verify_id(user_id, verify_id)
            buttons = [
                [
                    InlineKeyboardButton(
                        text="♻️ ᴄʟɪᴄᴋ ᴛᴏ ᴠᴇʀɪғʏ ♻️",
                        url=await get_shortlink(
                            f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}",
                            is_second_shortener,
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=how_to_download_link
                    )
                ],
            ]
            num = 2 if is_second_shortener else 1
            text = f"ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ ᴛᴏᴅᴀʏ 😐,\n\nᴛᴀᴘ ᴏɴ ᴛʜᴇ ᴠᴇʀɪꜰʏ ʟɪɴᴋ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss.\n\n#VERIFICATION_{num}"
            if query.message.chat.type == enums.ChatType.PRIVATE:
                return await query.message.reply_text(
                    text, protect_content = True, reply_markup=InlineKeyboardMarkup(buttons)
                )
        # User Verifying
        ident, req, file_id = query.data.split("#")
        if int(req) != 0 and query.from_user.id != int(req):
            return await query.answer(script.ALRT_TXT, show_alert=True)
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                await query.answer('𝘾𝙝𝙚𝙘𝙠 𝙋𝙈, 𝙄 𝙝𝙖𝙫𝙚 𝙨𝙚𝙣𝙩 𝙛𝙞𝙡𝙚𝙨 𝙞𝙣 𝙥𝙢', show_alert=True)
                return
            else:
                file_send=await client.send_cached_media(
                    chat_id=FILE_CHANNEL,
                    file_id=file_id,
                    caption=script.CHANNEL_CAP.format(query.from_user.mention, title, query.message.chat.title),
                    protect_content=True if ident == "filep" else False,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🔥 ᴄʜᴀɴɴᴇʟ 🔥", url=(MAIN_CHANNEL))
                            ]
                        ]
                    )
                )
                Joel_tgx = await query.message.reply_text(
                    script.FILE_MSG.format(query.from_user.mention, title, size),
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(
                        [
                         [
                          InlineKeyboardButton('📥 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝖫𝗂𝗇𝗄 📥 ', url = file_send.link)
                       ],[
                          InlineKeyboardButton("⚠️ 𝖢𝖺𝗇'𝗍 𝖠𝖼𝖼𝖾𝗌𝗌 ❓ 𝖢𝗅𝗂𝖼𝗄 𝖧𝖾𝗋𝖾 ⚠️", url=(FILE_FORWARD))
                         ]
                        ]
                    )
                )
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await Joel_tgx.delete()
                    await file_send.delete()
        except UserIsBlocked:
            await query.answer('𝐔𝐧𝐛𝐥𝐨𝐜𝐤 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐦𝐚𝐧 !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("checksub"):
        # User Verifying
        user_id = query.from_user.id
        is_second_shortener = await db.use_second_shortener(user_id)
        if not await db.is_user_verified(user_id) or is_second_shortener:
            verify_id = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=7)
            )
            how_to_download_link = (
                TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
            )
            await db.create_verify_id(user_id, verify_id)
            buttons = [
                [
                    InlineKeyboardButton(
                        text="♻️ ᴄʟɪᴄᴋ ᴛᴏ ᴠᴇʀɪғʏ ♻️",
                        url=await get_shortlink(
                            f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}",
                            is_second_shortener,
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=how_to_download_link
                    )
                ],
            ]
            num = 2 if is_second_shortener else 1
            text = f"ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ ᴛᴏᴅᴀʏ 😐,\n\nᴛᴀᴘ ᴏɴ ᴛʜᴇ ᴠᴇʀɪꜰʏ ʟɪɴᴋ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss 🤗\n\n#VERIFICATION_{num}"
            if query.message.chat.type == enums.ChatType.PRIVATE:
                return await query.message.reply_text(
                    text, protect_content = True, reply_markup=InlineKeyboardMarkup(buttons)
                )
        # User Verifying
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('👨‍🎤 ᴘʟᴇᴀsᴇ sʜᴀʀᴇ & sᴜᴘᴘᴏʀᴛ 👩‍🎤', url=f'https://t.me/share/url?url=https://t.me/{temp.U_NAME}')]])
        )
        await client.send_message(chat_id=query.from_user.id, text=f"<b>🌻 нαρρу ∂σωηℓσα∂ιηg αη∂ ¢σмє αgαιη 🌺</b>")

    elif query.data.startswith("pm_checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("😒 ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒", show_alert=True)
            return
        await query.answer(f"🍀 ʜᴇʏ {query.from_user.first_name},\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴍᴇ ᴍᴏᴠɪᴇ ᴏʀ sᴇʀɪᴇs ɴᴀᴍᴇ ᴏɴᴇ ᴍᴏʀᴇ ᴛɪᴍᴇ 😅", show_alert=True)
        await query.message.reply_to_message.delete()
        await query.message.delete()

    elif query.data.startswith("grp_checksub"):
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("😑 ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\n\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ", show_alert=True)
            return
        await query.answer(f"👨‍🎓 ʜᴇʏ {query.from_user.first_name},\n\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴍᴇ ᴍᴏᴠɪᴇ ᴏʀ sᴇʀɪᴇs ɴᴀᴍᴇ ᴏɴᴇ ᴍᴏʀᴇ ᴛɪᴍᴇ 😅", show_alert=True)
        await query.message.reply_to_message.delete()
        await query.message.delete()


    elif query.data == "predvd":
        k = await client.send_message(chat_id=query.message.chat.id, text="<b>Deleting PreDVDs... Please wait...</b>")
        files, next_offset, total = await get_bad_files(
                                                  'predvd',
                                                  offset=0)
        deleted = 0
        for file in files:
            file_ids = file.file_id
            result = await Media.collection.delete_one({
                '_id': file_ids,
            })
            if result.deleted_count:
                logger.info('PreDVD File Found ! Successfully deleted from database.')
            deleted+=1
        deleted = str(deleted)
        await k.edit_text(text=f"<b>Successfully deleted {deleted} PreDVD files.</b>")

    elif query.data == "camrip":
        k = await client.send_message(chat_id=query.message.chat.id, text="<b>Deleting CamRips... Please wait...</b>")
        files, next_offset, total = await get_bad_files(
                                                  'camrip',
                                                  offset=0)
        deleted = 0
        for file in files:
            file_ids = file.file_id
            result = await Media.collection.delete_one({
                '_id': file_ids,
            })
            if result.deleted_count:
                logger.info('CamRip File Found ! Successfully deleted from database.')
            deleted+=1
        deleted = str(deleted)
        await k.edit_text(text=f"<b>Successfully deleted {deleted} CamRip files.</b>")

    elif query.data == "pages":
        await query.answer()

    elif query.data == "reqinfo":
        await query.answer("⚠ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ⚠\n\nᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ\n\nɪꜰ ʏᴏᴜ ᴅᴏ ɴᴏᴛ ꜱᴇᴇ ᴛʜᴇ ʀᴇǫᴜᴇsᴛᴇᴅ ᴍᴏᴠɪᴇ / sᴇʀɪᴇs ꜰɪʟᴇ, ʟᴏᴏᴋ ᴀᴛ ᴛʜᴇ ɴᴇxᴛ ᴘᴀɢᴇ", show_alert=True)

    elif query.data == "minfo":
        await query.answer("⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯\nᴍᴏᴠɪᴇ ʀᴇǫᴜᴇꜱᴛ ꜰᴏʀᴍᴀᴛ\n⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯\n\nɢᴏ ᴛᴏ ɢᴏᴏɢʟᴇ ➠ ᴛʏᴘᴇ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ ➠ ᴄᴏᴘʏ ᴄᴏʀʀᴇᴄᴛ ɴᴀᴍᴇ ➠ ᴘᴀꜱᴛᴇ ᴛʜɪꜱ ɢʀᴏᴜᴘ\n\nᴇxᴀᴍᴘʟᴇ : ᴀᴠᴀᴛᴀʀ: ᴛʜᴇ ᴡᴀʏ ᴏғ ᴡᴀᴛᴇʀ\n\n🚯 ᴅᴏɴᴛ ᴜꜱᴇ ➠ ':(!,./)", show_alert=True)

    elif query.data == "sinfo":
        await query.answer("⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯\nꜱᴇʀɪᴇꜱ ʀᴇǫᴜᴇꜱᴛ ꜰᴏʀᴍᴀᴛ\n⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯\n\nɢᴏ ᴛᴏ ɢᴏᴏɢʟᴇ ➠ ᴛʏᴘᴇ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ ➠ ᴄᴏᴘʏ ᴄᴏʀʀᴇᴄᴛ ɴᴀᴍᴇ ➠ ᴘᴀꜱᴛᴇ ᴛʜɪꜱ ɢʀᴏᴜᴘ\n\nᴇxᴀᴍᴘʟᴇ : ᴍᴏɴᴇʏ ʜᴇɪsᴛ S01E01\n\n🚯 ᴅᴏɴᴛ ᴜꜱᴇ ➠ ':(!,./)", show_alert=True)      

    elif query.data == "tinfo":
        await query.answer("ᴛʏᴘᴇ ᴄᴏʀʀᴇᴄᴛ sᴘᴇʟʟɪɴɢ (ɢᴏᴏɢʟᴇ)\n\n★ ɪғ ʏᴏᴜ ɴᴏᴛ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ ɪɴ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ᴛʜᴇɴ ᴛʜᴇ ɴᴇxᴛ sᴛᴇᴘ ɪs ᴄʟɪᴄᴋ ɴᴇxᴛ ʙᴜᴛᴛᴏɴ.\n\n★ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜɪs ᴍᴇᴛʜᴏᴅ ᴛᴏ ɢᴇᴛᴛɪɴɢ ʏᴏᴜ ғɪʟᴇ", show_alert=True)

    elif query.data == "surprise":
        btn = [[
            InlineKeyboardButton('sᴜʀᴘʀɪsᴇ', callback_data='start')
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.SUR_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('⇆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘs ⇆', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ], [
            InlineKeyboardButton('📽️ ᴍᴏᴠɪᴇ ʟɪɴᴋ', url='https://t.me/Aksbackup'),

            InlineKeyboardButton('👨‍🎓 ʙᴏᴛ ᴏᴡɴᴇʀ', url='https://t.me/Aks_support01_bot')
        ], [
            InlineKeyboardButton('🛠️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📝 ᴀʙᴏᴜᴛ', callback_data='about')
         ],[
            InlineKeyboardButton('🤖 ᴍʏ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@technical_aks')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer(MSG_ALRT)      
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('✏️ ᴍᴀɴᴜᴀʟ', callback_data='manuelfilter'),
            InlineKeyboardButton('🔄 ᴀᴜᴛᴏ', callback_data='autofilter'),
            InlineKeyboardButton('🖇 ᴄᴏɴɴᴇᴄᴛ', callback_data='coct')
        ], [
            InlineKeyboardButton('📚 ᴇxᴛʀᴀ', callback_data='extra'),
            InlineKeyboardButton('🎶 sᴏɴɢ', callback_data='song'),
            InlineKeyboardButton('📯 ᴛᴛs', callback_data='tts')
        ], [
            InlineKeyboardButton('📽 ᴠɪᴅᴇᴏ', callback_data='video'),
            InlineKeyboardButton('📸 ᴛ_ɢʀᴀᴘʜ', callback_data='tele'),
            InlineKeyboardButton('ɴᴇxᴛ', callback_data='aswin')    
        ], [
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='start')      
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "aswin":
        buttons = [[
             InlineKeyboardButton('🎼 ᴀᴜᴅ_ʙᴏᴏᴋ', callback_data='abook'),
             InlineKeyboardButton('🧪 ᴄᴏᴠɪᴅ', callback_data='corona'),
             InlineKeyboardButton('🎲 ɢᴀᴍᴇs', callback_data='fun')
         ], [
             InlineKeyboardButton('📡 ᴘɪɴɢ', callback_data='pings'),
             InlineKeyboardButton('🚫 ᴊsᴏɴᴇ', callback_data='json'),
             InlineKeyboardButton('🎭 sᴛɪᴄᴋ_ɪᴅ', callback_data='sticker')
         ], [
             InlineKeyboardButton('❓️ ᴡʜᴏɪs', callback_data='whois'),
             InlineKeyboardButton('♻️ ᴜʀʟ_sʜᴏʀᴛ', callback_data='urlshort'),
             InlineKeyboardButton('ɴᴇxᴛ', callback_data='aswins')  
        ], [
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')         
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "aswins":
        buttons = [[
             InlineKeyboardButton('🆎️ ғᴏɴᴛ', callback_data='font'),
             InlineKeyboardButton('📝 ɢ_ᴛʀᴀɴs', callback_data='gtrans'),
             InlineKeyboardButton('💎 ᴄᴀʀʙᴏɴ', callback_data='carb'),
        ],  [
             InlineKeyboardButton('🌍 ᴄᴏᴜɴᴛʀʏ', callback_data='country')
        ],  [ 
             InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin'),
             InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('🎪 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴛ ᴄʜᴀɴɴᴇʟ 🎪', url="https://youtube.com/@technical_aks")
        ],[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)   
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        ) 
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )    
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('ʙᴜᴛᴛᴏɴs', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='manuelfilter')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('ᴀᴅᴍɪɴ', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='extra')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "song":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.SONG_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "video":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.VIDEO_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tts":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.TTS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "gtrans":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswins'),
            InlineKeyboardButton('𝙻𝙰𝙽𝙶 𝙲𝙾𝙳𝙴𝚂', url='https://cloud.google.com/translate/docs/languages')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        ) 
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.GTRANS_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "country":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswins'),
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        ) 
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.CON_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tele":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        ) 
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.TELE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "corona":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)   
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.CORONA_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "abook":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.ABOOK_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "sticker":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.STICKER_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "pings":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)   
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.PINGS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "json":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )  
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.JSON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "urlshort":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.URLSHORT_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "whois":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )  
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.WHOIS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "font":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswins')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.FONT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "carb":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswins')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.CARB_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "fun":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="▮▯▯"
        )
        await query.message.edit_text(
            text="▮▮▯"
        )
        await query.message.edit_text(
            text="▮▮▮"
        )
        await query.message.edit_text(
            text=script.FUN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data.startswith("opn_pm_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
            return
        if str(grp_id) != str(grpid):
            await query.message.edit("You are not connected to the group! Please /connect group and then change /settings")
            return
        title = query.message.chat.title
        settings = await get_settings(grpid)
        btn = [[
            InlineKeyboardButton("⟲ ɢᴏ ᴛᴏ ᴄʜᴀᴛ ⟳", url=f"https://t.me/{temp.U_NAME}")
        ]]

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["auto_filter"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴛᴇʀ ʙᴜᴛᴛᴏɴ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('sɪɴɢʟᴇ' if settings["button"] else 'ᴅᴏᴜʙʟᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ʀᴇᴅɪʀᴇᴄᴛ ᴛᴏ', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʙᴏᴛ ᴘᴍ' if settings["botpm"] else 'ᴄʜᴀɴɴᴇʟ',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["file_secure"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["imdb"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["spell_check"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴡᴇʟᴄᴏᴍᴇ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["welcome"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10 ᴍɪɴ' if settings["auto_delete"] else 'ᴏꜰꜰ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
                ]
            ]

            try:
                await client.send_message(
                    chat_id=userid,
                    text=f"ᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ <b>'{title}'</b> ᴀs ʏᴏᴜʀ ᴡɪsʜ ✨",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=enums.ParseMode.HTML
                )
                await query.message.edit_text(f"<b>sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ sᴇɴᴛ ɪɴ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ ☟</b>")
                d = await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
                await asyncio.sleep(300)
                await d.delete()
                await msg.delete()
            except UserIsBlocked:
                return await query.answer('Your blocked me, Unblock me and try again...', show_alert=True)

    elif query.data.startswith("opn_grp_setgs"):
        ident, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
            return
        if str(grp_id) != str(grpid):
            await query.message.edit("You are not connected to the group! Please /connect group and then change /settings")
            return
        title = query.message.chat.title
        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["auto_filter"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴛᴇʀ ʙᴜᴛᴛᴏɴ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('sɪɴɢʟᴇ' if settings["button"] else 'ᴅᴏᴜʙʟᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ʀᴇᴅɪʀᴇᴄᴛ ᴛᴏ', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʙᴏᴛ ᴘᴍ' if settings["botpm"] else 'ᴄʜᴀɴɴᴇʟ',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["file_secure"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["imdb"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["spell_check"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴡᴇʟᴄᴏᴍᴇ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["welcome"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10 ᴍɪɴ' if settings["auto_delete"] else 'ᴏꜰꜰ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(
                text=f"ᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ <b>'{title}'</b> ᴀs ʏᴏᴜʀ ᴡɪsʜ ✨",
                parse_mode=enums.ParseMode.HTML
            )
            d = await query.message.edit_reply_markup(reply_markup)
            await asyncio.sleep(300)
            await d.delete()
            await msg.delete()
            
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer(MSG_ALRT)

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)
        
        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["auto_filter"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴛᴇʀ ʙᴜᴛᴛᴏɴ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('sɪɴɢʟᴇ' if settings["button"] else 'ᴅᴏᴜʙʟᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ʀᴇᴅɪʀᴇᴄᴛ ᴛᴏ', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʙᴏᴛ ᴘᴍ' if settings["botpm"] else 'ᴄʜᴀɴɴᴇʟ',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["file_secure"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["imdb"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["spell_check"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴡᴇʟᴄᴏᴍᴇ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('ʏᴇs ✔️' if settings["welcome"] else 'ɴᴏ ✗',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10 ᴍɪɴ' if settings["auto_delete"] else 'ᴏꜰꜰ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.answer("ᴄʜᴀɴɢᴇᴅ 🌟")
            d = await query.message.edit_reply_markup(reply_markup)
            await asyncio.sleep(300)
            await d.delete()
            await msg.delete()

    elif query.data.startswith("show_options"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("☇ ᴀᴄᴄᴇᴘᴛ ☇", callback_data=f"accept#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("✗ ʀᴇᴊᴇᴄᴛ ✗", callback_data=f"reject#{user_id}#{msg_id}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("reject"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✗ ʀᴇᴊᴇᴄᴛ ✗", callback_data=f"rj_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("⌛ ᴠɪᴇᴡ sᴛᴀᴛᴜs ⌛", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="😑 sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛ ✗", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nsᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛ ✗</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("accept"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✗ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ✗", callback_data=f"not_available#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("☇ ᴜᴘʟᴏᴀᴅᴇᴅ ☇", callback_data=f"uploaded#{user_id}#{msg_id}")
        ],[
            InlineKeyboardButton("⌤ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ⌤", callback_data=f"already_available#{user_id}#{msg_id}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
        else:
            await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)

    elif query.data.startswith("not_available"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("✗ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ✗", callback_data=f"na_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("⌛ ᴠɪᴇᴡ sᴛᴀᴛᴜs ⌛", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nsᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 😢</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("uploaded"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("☇ ᴜᴘʟᴏᴀᴅᴇᴅ ☇", callback_data=f"ul_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("⌛ ᴠɪᴇᴡ sᴛᴀᴛᴜs ⌛", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ ☺️</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("already_available"):
        ident, user_id, msg_id = query.data.split("#")
        chnl_id = query.message.chat.id
        userid = query.from_user.id
        buttons = [[
            InlineKeyboardButton("🫤 ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 🫤", callback_data=f"aa_alert#{user_id}")
        ]]
        btn = [[
            InlineKeyboardButton("⌛ ᴠɪᴇᴡ sᴛᴀᴛᴜs ⌛", url=f"{query.message.link}")
        ]]
        st = await client.get_chat_member(chnl_id, userid)
        if (st.status == enums.ChatMemberStatus.ADMINISTRATOR) or (st.status == enums.ChatMemberStatus.OWNER):
            user = await client.get_users(user_id)
            request = query.message.text
            await query.answer("Message sent requester")
            await query.message.edit_text(f"<s>{request}</s>")
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
            try:
                await client.send_message(chat_id=user_id, text="<b>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋</b>", reply_markup=InlineKeyboardMarkup(btn))
            except UserIsBlocked:
                await client.send_message(SUPPORT_GROUP, text=f"<b>💥 ʜᴇʟʟᴏ {user.mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ 😋</b>", reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=int(msg_id))
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("rj_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ʀᴇᴊᴇᴄᴛ", show_alert=True)
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("na_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("sᴏʀʀʏ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ", show_alert=True)
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("ul_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴜᴘʟᴏᴀᴅᴇᴅ", show_alert=True)
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

    elif query.data.startswith("aa_alert"):
        ident, user_id = query.data.split("#")
        userid = query.from_user.id
        if str(userid) in user_id:
            await query.answer("ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ", show_alert=True)
        else:
            await query.answer("😒 тнιѕ ιѕ ησт ƒσя уσυ 😒", show_alert=True)

async def auto_filter(client, msg, spoll=False):
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(client, msg)
                else:
                    if LOG_NOR_CHANNEL:
                        await client.send_message(chat_id=LOG_NOR_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, search)))
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    pre = 'filep' if settings['file_secure'] else 'file'
    req = message.from_user.id if message.from_user else 0
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"🐲 {get_size(file.file_size)}≽ {file.file_name}", callback_data=f'{pre}#{req}#{file.file_id}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}",
                    callback_data=f'{pre}#{req}#{file.file_id}',
                ),
                InlineKeyboardButton(
                    text=f"🐲 {get_size(file.file_size)}",
                    callback_data=f'{pre}#{req}#{file.file_id}',
                ),
            ]
            for file in files
        ]
    btn.insert(0, 
        [
            InlineKeyboardButton('⛔️ sᴜʙsᴄʀɪʙᴇ ᴏᴜʀ ʏᴛ ᴄʜᴀɴɴᴇʟ ⛔️', url='https://youtube.com/@technical_aks')
        ]
    )
    btn.insert(1, 
         [
             InlineKeyboardButton(f'♻️ ɪɴꜰᴏ', 'reqinfo'),
             InlineKeyboardButton(f'ᴍᴏᴠɪᴇ', 'minfo'),
             InlineKeyboardButton(f'sᴇʀɪᴇs', 'sinfo'),
             InlineKeyboardButton(f'⚜️ ᴛɪᴘs', 'tinfo')
         ]
    )
    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f" 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text=" 1/1", callback_data="pages")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"🎪 ᴛɪᴛɪʟᴇ:- {search}\n\n┏⁉️ ᴀsᴋᴇᴅ ʙʏ:- {message.from_user.mention}\n┣🔆 ᴘᴏᴡᴇʀᴇᴅ ʙʏ:- <a href='https://t.me/{temp.U_NAME}'>Hulk</a>\n┗♻️ ᴄʜᴀɴɴᴇʟ : <a href='https://t.me/Imdb_updates'>imdb updates​</a>\n\n⚠️ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n<b>❇️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ : {message.chat.title}</b>"
    if imdb and imdb.get('poster'):
        try:
            pic_fi=await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await pic_fi.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await pic_fi.delete()
                    await message.delete()
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            pic_fil=await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await pic_fil.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await pic_fil.delete()
                    await message.delete()
        except Exception as e:
            logger.exception(e)
            no_pic=await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await no_pic.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await no_pic.delete()
                    await message.delete()
    else:
        if message.chat.id == SUPPORT_GROUP:
            buttons = [[InlineKeyboardButton('✧ ᴛᴀᴋᴇ ᴍᴏᴠɪᴇ ꜰʀᴏᴍ ʜᴇʀᴇ ✧', url='https://t.me/all_in_one_movies2')]]
            d = await message.reply_photo(photo='https://graph.org/file/be7f44102f87aa00e2879.jpg', caption=f"<b>🍁 ʜᴇʏ {message.from_user.mention}\n\n({total_results}) ʀᴇsᴜʟᴛ ᴀʀᴇ ꜰᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀsᴇ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ [{search}]\n\n👇 ᴛᴀᴋᴇ ᴍᴏᴠɪᴇs & sᴇʀɪᴇs ꜰʀᴏᴍ ʜᴇʀᴇ 👇</b>", reply_markup=InlineKeyboardMarkup(buttons))
            await asyncio.sleep(60)
            await d.delete()
            await message.delete()
        else:
            no_fil=await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(60)
                    await no_fil.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(60)
                    await no_fil.delete()
                    await message.delete()
    if spoll:
        await msg.message.delete()


async def advantage_spell_chok(client, msg):
    mv_id = msg.id
    mv_rqst = msg.text
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    settings = await get_settings(msg.chat.id)
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    RQST = query.strip()
    query = query.strip() + " movie"
    try:
        movies = await get_poster(mv_rqst, bulk=True)
    except Exception as e:
        logger.exception(e)
        await client.send_message(chat_id=LOG_NOR_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        k = await msg.reply(script.I_CUDNT.format(reqstr.mention))
        await asyncio.sleep(8)
        await k.delete()
        await msg.delete()
        return
    movielist = [] #error fixed
    if not movies:
        reqst_gle = mv_rqst.replace(" ", "+")
        button = [[
                   InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={reqst_gle}")
        ]]
        await client.send_message(chat_id=LOG_NOR_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        k = await msg.reply_photo(
            photo=SPELL_IMG, 
            caption=script.I_CUDNT.format(mv_rqst),
            reply_markup=InlineKeyboardMarkup(button)
        )
        await asyncio.sleep(60)
        await k.delete()
        await msg.delete()
        return
    movielist += [movie.get('title') for movie in movies]
    movielist += [f"{movie.get('title')} {movie.get('year')}" for movie in movies]
    SPELL_CHECK[mv_id] = movielist
    btn = [
        [
            InlineKeyboardButton(
                text=movie_name.strip(),
                callback_data=f"spol#{reqstr1}#{k}",
            )
        ]
        for k, movie_name in enumerate(movielist)
    ]
    btn.append([InlineKeyboardButton(text="✗ ᴄʟᴏsᴇ ✗", callback_data=f'spol#{reqstr1}#close_spellcheck')])
    spell_check_del = await msg.reply_photo(
        photo=(SPELL_SUG_IMG),
        caption=(script.CUDNT_FND.format(reqstr.mention)),
        reply_markup=InlineKeyboardMarkup(btn),
        reply_to_message_id=msg.id
        )

    try:
        if settings['auto_delete']:
            await asyncio.sleep(600)
            await spell_check_del.delete()
            await msg.delete() 
    except KeyError:
            grpid = await active_connection(str(message.from_user.id))
            await save_group_settings(grpid, 'auto_delete', True)
            settings = await get_settings(msg.chat.id)
            if settings['auto_delete']:
                await asyncio.sleep(600)
                await spell_check_del.delete()
                await msg.delete()

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            k = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                            await asyncio.sleep(60)
                            await k.delete()
                            await message.reply_to_message.delete()
                    elif btn == "[]":
                        k = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                        await asyncio.sleep(60)
                        await k.delete()
                        await message.reply_to_message.delete()
                    else:
                        button = eval(btn)
                        k = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                        await asyncio.sleep(60)
                        await k.delete()
                        await message.reply_to_message.delete()
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False

async def global_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            k = await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                reply_to_message_id=reply_id
                            )
                            await asyncio.sleep(600)
                            await k.delete()
                            await message.reply_to_message.delete()

                        else:
                            button = eval(btn)
                            k = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                            await asyncio.sleep(600)
                            await k.delete()
                            await message.reply_to_message.delete()

                    elif btn == "[]":
                        k = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                        await asyncio.sleep(600)
                        await k.delete()
                        await message.reply_to_message.delete()

                    else:
                        button = eval(btn)
                        k = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                        await asyncio.sleep(600)
                        await k.delete()
                        await message.reply_to_message.delete()

                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
