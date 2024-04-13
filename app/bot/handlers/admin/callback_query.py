from aiogram import Router, F
from aiogram.types import CallbackQuery, User
from aiogram_newsletter.manager import ANManager
from pytonapi.schema.accounts import Account
from pytonapi.schema.jettons import JettonInfo
from pytonapi.schema.nft import NftCollection

from app.db.models import UserDB, ChatDB, TokenDB, AdminDB
from ._filters import AdminFilter
from .windows import AdminWindow
from ..private.windows import Window
from ...manager import Manager
from ...utils.states import AdminState
from ...utils.validations import is_decimal

router = Router()
router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@router.callback_query(AdminState.ADMIN_MENU)
async def admin_menu_callback_query(call: CallbackQuery, manager: Manager, an_manager: ANManager) -> None:
    if call.data == "main":
        await Window.main_menu(manager)

    elif call.data == "chats_menu":
        await AdminWindow.chats_menu(manager)

    elif call.data == "tokens_menu":
        await AdminWindow.tokens_menu(manager)

    elif call.data == "admins_menu":
        await AdminWindow.admins_menu(manager)

    elif call.data == "newsletter":
        users = await UserDB.all(manager.sessionmaker)
        users_ids = [user.id for user in users]

        await an_manager.newsletter_menu(users_ids, AdminWindow.admin_menu)
        await call.message.delete()

    await call.answer()


@router.callback_query(AdminState.CHATS_MENU)
async def chats_menu_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admin_menu(manager)

    elif is_decimal(call.data):
        await manager.state.update_data(chat_id=int(call.data))
        await AdminWindow.chat_info(manager)

    elif call.data.startswith("page"):
        page = int(call.data.split(":")[1])
        await manager.state.update_data(page=page)
        await AdminWindow.chats_menu(manager)

    await call.answer()


@router.callback_query(AdminState.CHAT_INFO)
async def chat_info_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.chats_menu(manager)

    elif call.data == "delete":
        await AdminWindow.chat_confirm_delete(manager)

    await call.answer()


@router.callback_query(AdminState.CHAT_CONFIRM_DELETE)
async def chat_confirm_delete_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.chat_info(manager)

    elif call.data == "confirm":
        state_data = await manager.state.get_data()
        chat = await ChatDB.delete(manager.sessionmaker, state_data["chat_id"])

        text = manager.text_message.get("item_deleted").format(
            item=chat.name, table=ChatDB.__tablename__.title(),
        )
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.chats_menu(manager)

    await call.answer()


@router.callback_query(AdminState.CHAT_CONFIRM_ADD)
async def chat_confirm_add_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await manager.state.update_data(page=1)
        await AdminWindow.chats_menu(manager)

    elif call.data == "confirm":
        await manager.send_loader_message()

        state_data = await manager.state.get_data()
        chat_data = state_data.get("chat")
        bot_me = await manager.bot.get_me()
        chat = await manager.bot.get_chat(chat_data.get("id"))
        name = f"Generated by @{bot_me.username}"
        create_invite = await chat.create_invite_link(name=name, creates_join_request=True)

        chat = await ChatDB.create_or_update(
            manager.sessionmaker,
            id=chat.id,
            name=chat.title,
            type=chat.type,
            invite_link=create_invite.invite_link
        )
        text = manager.text_message.get("item_added").format(
            item=chat.name, table=ChatDB.__tablename__.title(),
        )
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.chats_menu(manager)

    await call.answer()


@router.callback_query(AdminState.TOKENS_MENU)
async def tokens_menu_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admin_menu(manager)

    elif call.data == "add":
        await AdminWindow.token_send_address(manager)

    elif call.data.isdigit():
        await manager.state.update_data(token_id=int(call.data))
        await AdminWindow.token_info(manager)

    elif call.data.startswith("page"):
        page = int(call.data.split(":")[1])
        await manager.state.update_data(page=page)
        await AdminWindow.tokens_menu(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_INFO)
async def token_info_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.tokens_menu(manager)

    elif call.data == "edit_min_amount":
        await AdminWindow.token_edit_amount(manager)

    elif call.data == "delete":
        await AdminWindow.token_confirm_delete(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_CONFIRM_DELETE)
async def token_confirm_delete_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.token_info(manager)

    elif call.data == "confirm":
        state_data = await manager.state.get_data()
        token = await TokenDB.delete(manager.sessionmaker, state_data["token_id"])

        text = manager.text_message.get("item_deleted").format(
            item=token.name, table=TokenDB.__tablename__.title(),
        )
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.tokens_menu(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_SEND_ADDRESS)
async def token_send_address_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.tokens_menu(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_SEND_AMOUNT)
async def token_send_amount_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.token_send_address(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_CONFIRM_ADD)
async def token_confirm_add_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.token_send_amount(manager)

    elif call.data == "confirm":
        state_data = await manager.state.get_data()
        account = Account(**state_data.get("account"))

        token_type = state_data.get("token_type")
        if token_type == TokenDB.Type.JettonMaster:
            token = JettonInfo(**state_data.get("token"))
            token_name = f"{token.metadata.name} [{token.metadata.symbol}]"
        else:
            token = NftCollection(**state_data.get("token"))
            token_name = token.metadata.get("name", "Unknown Collection")
        token_min_amount = state_data.get("token_min_amount")

        await TokenDB.create_or_update(
            manager.sessionmaker,
            name=token_name,
            type=token_type,
            address=account.address.to_userfriendly(True),
            min_amount=token_min_amount,
        )
        text = manager.text_message.get("item_added").format(
            item=token_name, table=TokenDB.__tablename__.title(),
        )
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.tokens_menu(manager)

    await call.answer()


@router.callback_query(AdminState.TOKEN_EDIT_AMOUNT)
async def token_edit_amount_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.token_info(manager)

    await call.answer()


@router.callback_query(AdminState.ADMINS_MENU)
async def admins_menu_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admin_menu(manager)

    elif call.data == "add":
        await AdminWindow.admin_send_id(manager)

    elif call.data.isdigit():
        await manager.state.update_data(admin_id=int(call.data))
        await AdminWindow.admin_info(manager)

    elif call.data.startswith("page"):
        page = int(call.data.split(":")[1])
        await manager.state.update_data(page=page)
        await AdminWindow.admins_menu(manager)

    await call.answer()


@router.callback_query(AdminState.ADMIN_INFO)
async def admin_info_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admins_menu(manager)

    elif call.data == "delete":
        await AdminWindow.admin_confirm_delete(manager)

    await call.answer()


@router.callback_query(AdminState.ADMIN_CONFIRM_DELETE)
async def admin_confirm_delete_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admin_info(manager)

    elif call.data == "confirm":
        state_data = await manager.state.get_data()
        admin = await AdminDB.get_with_join(
            manager.sessionmaker,
            primary_key=state_data.get("admin_id"),
            join_tables=[AdminDB.user],
        )

        text = manager.text_message.get("item_deleted").format(
            item=admin.user.full_name, table=AdminDB.__tablename__.title(),
        )
        await AdminDB.delete(manager.sessionmaker, admin.id)
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.admins_menu(manager)

    await call.answer()


@router.callback_query(AdminState.ADMIN_SEND_ID)
async def admin_send_id_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admins_menu(manager)

    await call.answer()


@router.callback_query(AdminState.ADMIN_CONFIRM_ADD)
async def admin_confirm_add_callback_query(call: CallbackQuery, manager: Manager) -> None:
    if call.data == "back":
        await AdminWindow.admin_send_id(manager)

    elif call.data == "confirm":
        state_data = await manager.state.get_data()
        user = User(**state_data.get("user"))

        await AdminDB.create_or_update(
            manager.sessionmaker,
            user_id=user.id,
        )
        text = manager.text_message.get("item_added").format(
            item=user.full_name, table=AdminDB.__tablename__.title(),
        )
        await call.answer(text, show_alert=True)
        await manager.state.update_data(page=1)
        await AdminWindow.chats_menu(manager)

    await call.answer()
