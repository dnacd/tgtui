"""
Main application screen of the Telegram Textual TUI.
Provides a multi-column layout for chat selection and message history.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from telethon import events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import (
    GetAvailableReactionsRequest,
    GetFullChatRequest,
    GetMessageReactionsListRequest,
    GetRecentReactionsRequest,
    SendReactionRequest,
)
from telethon.tl.types import (
    Channel,
    Chat,
    ChatReactionsNone,
    ChatReactionsSome,
    MessageReactions,
    ReactionEmoji,
    User,
)
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, ListView, RichLog, Tabs

from telegram_textual_tui.tui.config.keymap import Keymap
from telegram_textual_tui.tui.controllers.history_controller import HistoryController
from telegram_textual_tui.tui.screens.profile import ProfileScreen
from telegram_textual_tui.tui.widgets.chat_list import ChatItem, ChatList
from telegram_textual_tui.tui.widgets.chat_tabs import ChatTabs
from telegram_textual_tui.utils.formatters import get_telegram_entity_title

if TYPE_CHECKING:
    from telegram_textual_tui.tui.app import TGTApp


class MainScreen(Screen):
    """
    The primary screen of the application where users interact with chats and messages.
    Supports full keyboard navigation and dynamic reaction handling.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the main screen state variables and controllers.
        """
        super().__init__(*args, **kwargs)
        self._selected_dialog_id = None
        self._selected_dialog_entity = None
        self._read_outbox_maximum_id = 0
        self._reaction_target_message_id = None
        self._last_received_message_id = None
        
        # Pagination and caching state
        self._loaded_messages: List[Any] = []
        self._sender_cache: Dict[int, str] = {}
        self._is_loading_more = False

        # Controllers
        self._history_controller = HistoryController(self.app.telegram_manager)

    BINDINGS = Keymap.MAIN_SCREEN

    async def action_next_tab(self) -> None:
        """Switch to the next chat category tab if not typing."""
        if not isinstance(self.focused, Input):
            self.query_one(ChatTabs).action_next_tab()

    async def action_prev_tab(self) -> None:
        """Switch to the previous chat category tab if not typing."""
        if not isinstance(self.focused, Input):
            self.query_one(ChatTabs).action_prev_tab()

    async def action_show_my_profile(self) -> None:
        """
        Switch to the current user's profile screen.
        """
        self.app.push_screen(ProfileScreen())

    async def action_show_partner_profile(self) -> None:
        """
        Show the profile of the current chat partner if available.
        """
        if isinstance(self._selected_dialog_entity, User):
            self.app.push_screen(ProfileScreen(user_id=self._selected_dialog_entity.id))

    async def action_react_to_last_message(self) -> None:
        """
        Open reaction selection for the most recently received message.
        """
        if self._last_received_message_id:
            await self.action_send_reaction(self._last_received_message_id)

    async def action_focus_search(self) -> None:
        """Move focus to the chat search input."""
        self.query_one("#chat-search", Input).focus()

    async def action_focus_chat_list(self) -> None:
        """Move focus to the chat selection list."""
        self.query_one("#chat-list", ChatList).focus()

    async def action_focus_message_input(self) -> None:
        """Move focus to the message input field."""
        self.query_one("#message-input", Input).focus()

    async def action_scroll_messages_up(self) -> None:
        """Scroll the message history log upwards and auto-load more if needed."""
        messages_log = self.query_one("#messages", RichLog)
        messages_log.scroll_up()
        
        if messages_log.scroll_offset.y <= 1:
            await self.action_load_more_history()

    async def action_scroll_messages_down(self) -> None:
        """Scroll the message history log downwards."""
        self.query_one("#messages", RichLog).scroll_down()

    async def action_load_more_history(self) -> None:
        """Fetch older messages and prepend them to the view."""
        if not self._selected_dialog_entity or self._is_loading_more or not self._loaded_messages:
            return

        self._is_loading_more = True
        try:
            oldest_id = self._loaded_messages[0].id
            older_messages = await self._history_controller.get_messages(
                self._selected_dialog_entity, 
                limit=30, 
                offset_id=oldest_id
            )
            
            if older_messages:
                self._loaded_messages = list(reversed(older_messages)) + self._loaded_messages
                await self._render_messages()
        finally:
            self._is_loading_more = False

    async def action_show_user_profile(self, user_id: int) -> None:
        """
        Switch to a user's profile based on their ID.
        """
        if user_id:
            self.app.push_screen(ProfileScreen(user_id=user_id))

    async def action_show_reactions(self, message_id: int) -> None:
        """
        Fetch and display users who reacted to a specific message.
        """
        application_instance: TGTApp = self.app
        try:
            reactions_list = await application_instance.telegram_manager.client(
                GetMessageReactionsListRequest(
                    peer=self._selected_dialog_entity, id=int(message_id), limit=100
                )
            )
            names = [get_telegram_entity_title(user) for user in reactions_list.users]
            if names:
                self.query_one("#messages", RichLog).write(f"[yellow]Reacted by:[/yellow] {', '.join(names)}")
            else:
                self.query_one("#messages", RichLog).write("[dim]No reaction details.[/dim]")
        except Exception as error:
            self.query_one("#messages", RichLog).write(f"[red]Error: {error}[/red]")

    async def action_quick_react(self, message_id: int, emoticon: str) -> None:
        """
        Send a reaction to Telegram and refresh the message view.
        """
        application_instance: TGTApp = self.app
        try:
            await application_instance.telegram_manager.client(
                SendReactionRequest(
                    peer=self._selected_dialog_entity,
                    msg_id=int(message_id),
                    reaction=[ReactionEmoji(emoticon=emoticon)],
                )
            )
            chat_list = self.query_one(ChatList)
            if chat_list.index is not None:
                await self._load_message_history(self._selected_dialog_entity, chat_list.children[chat_list.index])
        except Exception as error:
            self.query_one("#messages", RichLog).write(f"[red]Failed to react: {error}[/red]")

    async def action_send_reaction(self, message_id: int) -> None:
        """
        Dynamically fetch available reactions from Telegram and display as clickable options.
        """
        application_instance: TGTApp = self.app
        messages_log = self.query_one("#messages", RichLog)

        allowed_emojis = []
        
        try:
            available_reactions = await application_instance.telegram_manager.client(
                GetAvailableReactionsRequest(hash=0)
            )
            if hasattr(available_reactions, "reactions"):
                allowed_emojis = [
                    r.reaction.emoticon for r in available_reactions.reactions 
                    if isinstance(r.reaction, ReactionEmoji)
                ]
        except Exception:
            pass

        if not allowed_emojis:
            try:
                recent_reactions = await application_instance.telegram_manager.client(
                    GetRecentReactionsRequest(hash=0, limit=20)
                )
                if hasattr(recent_reactions, "reactions"):
                    allowed_emojis = [r.emoticon for r in recent_reactions.reactions if isinstance(r, ReactionEmoji)]
            except Exception:
                pass

        if isinstance(self._selected_dialog_entity, (Chat, Channel)):
            try:
                if isinstance(self._selected_dialog_entity, Channel):
                    full = await application_instance.telegram_manager.client(GetFullChannelRequest(self._selected_dialog_entity))
                else:
                    full = await application_instance.telegram_manager.client(GetFullChatRequest(self._selected_dialog_id))
                
                settings = full.full_chat.available_reactions
                if isinstance(settings, ChatReactionsNone):
                    messages_log.write("[red]Reactions are disabled here.[/red]")
                    return
                elif isinstance(settings, ChatReactionsSome):
                    allowed_emojis = [r.emoticon for r in settings.reactions if isinstance(r, ReactionEmoji)]
            except Exception:
                pass

        if not allowed_emojis:
            allowed_emojis = ["\U0001F44D", "\U00002764", "\U0001F525", "\U0001F44F"]

        links = [f"[@click=screen.quick_react({message_id},'{e}')]{e}[/@click]" for e in allowed_emojis[:15]]
        messages_log.write(f"[yellow]Reactions:[/yellow] {' '.join(links)}")
        
        input_widget = self.query_one("#message-input", Input)
        input_widget.placeholder = "Enter emoji and press Enter..."
        input_widget.focus()
        self._reaction_target_message_id = message_id

    async def action_reload_all_dialogs(self) -> None:
        """Update the sidebar with the latest 100 dialogs."""
        application_instance: TGTApp = self.app
        chat_list = self.query_one(ChatList)
        chat_list.clear()
        dialogs = await application_instance.telegram_manager.client.get_dialogs(limit=100)
        for dialog in dialogs:
            await chat_list.append(ChatItem(dialog))
        self._sync_chat_filter()

    def compose(self) -> ComposeResult:
        """Compose the main layout components."""
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(placeholder="Search chats...", id="chat-search")
                yield ChatTabs(id="chat-tabs")
                yield ChatList(id="chat-list")
            with Vertical(id="chat-area"):
                yield RichLog(id="messages", highlight=True, markup=True)
                yield Input(placeholder="Type a message...", id="message-input")

    async def on_mount(self) -> None:
        """Initialize event handlers and load initial data."""
        self.query_one("#messages", RichLog).write("[dim]Select a chat to begin...[/dim]")
        
        application_instance: TGTApp = self.app
        if application_instance.telegram_manager:
            application_instance.telegram_manager.client.add_event_handler(
                self._handle_incoming_new_message, events.NewMessage
            )
            await self.action_reload_all_dialogs()

    async def on_unmount(self) -> None:
        """Cleanup event handlers."""
        application_instance: TGTApp = self.app
        if application_instance.telegram_manager:
            application_instance.telegram_manager.client.remove_event_handler(
                self._handle_incoming_new_message, events.NewMessage
            )

    @on(Tabs.TabActivated)
    def on_tab_activated(self) -> None:
        """Handle chat category tab switching."""
        self._sync_chat_filter()
        if not isinstance(self.focused, Input):
            self.query_one(ChatList).focus()

    @on(Input.Changed, "#chat-search")
    def on_search_filter_changed(self) -> None:
        """Filter the chat list sidebar based on search term."""
        self._sync_chat_filter()

    @on(Input.Submitted, "#chat-search")
    def on_search_submitted(self) -> None:
        """Handle search submission by focusing the chat list."""
        chat_list = self.query_one(ChatList)
        if chat_list.index is not None:
            chat_list.focus()

    def _sync_chat_filter(self) -> None:
        """Coordinate filtering between category tabs and search input."""
        try:
            search_term = self.query_one("#chat-search", Input).value
            active_tab = self.query_one(ChatTabs).active_tab
            category = active_tab.id if active_tab else "all"
            self.query_one(ChatList).apply_filter(category, search_term)
        except Exception:
            pass

    def _format_message_reactions(self, message_id: int, data: Optional[MessageReactions]) -> str:
        """Generate a clickable string of reactions for the log."""
        if not data or not data.results:
            return f" [@click=screen.send_reaction({message_id})][dim][React][/dim][/@click]"

        parts = []
        for result in data.results:
            char = result.reaction.emoticon if isinstance(result.reaction, ReactionEmoji) else "C"
            parts.append(f"{char}{result.count}")

        return f" [@click=screen.show_reactions({message_id})][dim][{ ' '.join(parts) }][/dim][/@click] [@click=screen.send_reaction({message_id})][dim][+][/dim][/@click]"

    async def _handle_incoming_new_message(self, event: events.NewMessage.Event) -> None:
        """Process real-time messages and update the UI."""
        application_instance: TGTApp = self.app
        chat_id = event.chat_id
        if self._selected_dialog_id == chat_id:
            self._last_received_message_id = event.message.id
            log = self.query_one("#messages", RichLog)
            
            sid = getattr(event.message, "sender_id", 0)
            if sid not in self._sender_cache:
                sender = await event.get_sender()
                self._sender_cache[sid] = get_telegram_entity_title(sender)
            
            name = self._sender_cache[sid]
            tick = " (v)" if event.out and isinstance(self._selected_dialog_entity, User) else ""
            link = f"[@click=screen.show_user_profile({sid})][bold cyan]{name}[/bold cyan][/@click]"
            log.write(f"{link}: {event.message.text or '[Media]'}{tick}")

            await application_instance.telegram_manager.client.send_read_acknowledge(event.input_chat)
            return

        chat_list = self.query_one(ChatList)
        for item in chat_list.children:
            if isinstance(item, ChatItem) and item.dialog.id == chat_id:
                item.dialog.unread_count += 1
                try:
                    badge = item.query_one(".chat-unread")
                    badge.update(str(item.dialog.unread_count))
                except Exception:
                    await item.mount(Label(str(item.dialog.unread_count), classes="chat-unread"))
                break

    async def _render_messages(self) -> None:
        """Render all loaded messages to the log using an optimized cache-aware process."""
        log = self.query_one("#messages", RichLog)
        log.clear()
        
        is_dm = isinstance(self._selected_dialog_entity, User)
        
        for msg in self._loaded_messages:
            sid = getattr(msg, "sender_id", 0)
            
            if sid not in self._sender_cache:
                sender = await msg.get_sender()
                self._sender_cache[sid] = get_telegram_entity_title(sender)

            name = self._sender_cache[sid]
            status = ""
            if msg.out and is_dm:
                status = " [blue]vv[/blue]" if msg.id <= self._read_outbox_maximum_id else " [dim]v[/dim]"
            
            reacts = self._format_message_reactions(msg.id, getattr(msg, "reactions", None))
            link = f"[@click=screen.show_user_profile({sid})][bold cyan]{name}[/bold cyan][/@click]"
            log.write(f"{link}: {msg.text or '[Media]'}{status}{reacts}")

    async def _load_message_history(self, entity: Any, item: Optional[ChatItem] = None) -> None:
        """Fetch and render initial message history for the selected peer."""
        application_instance: TGTApp = self.app
        self._selected_dialog_id = entity.id
        self._selected_dialog_entity = entity
        
        self._loaded_messages = []
        self._sender_cache = {}

        dialog_data = getattr(item, "dialog", None)
        self._read_outbox_maximum_id = getattr(dialog_data, "read_outbox_max_id", 0)
        if self._read_outbox_maximum_id == 0 and hasattr(dialog_data, "dialog"):
            self._read_outbox_maximum_id = getattr(dialog_data.dialog, "read_outbox_max_id", 0)

        try:
            await application_instance.telegram_manager.client.send_read_acknowledge(entity)
            if item:
                try:
                    item.query_one(".chat-unread").remove()
                except Exception:
                    pass
        except Exception:
            pass

        messages = await self._history_controller.get_messages(entity, limit=30)
        self._loaded_messages = list(reversed(messages))

        if self._loaded_messages:
            self._last_received_message_id = self._loaded_messages[-1].id

        await self._render_messages()

    @on(ListView.Selected, "#chat-list")
    async def on_chat_list_item_selected(self, event: ListView.Selected) -> None:
        """Handle chat selection in the sidebar."""
        if not isinstance(event.item, ChatItem):
            return
        await self._load_message_history(event.item.dialog.entity, event.item)

    @on(Input.Submitted, "#message-input")
    async def on_message_input_submitted(self, event: Input.Submitted) -> None:
        """Handle sending text or emojis."""
        application_instance: TGTApp = self.app
        text = event.value.strip()
        if not text:
            return

        if self._reaction_target_message_id is not None:
            mid = self._reaction_target_message_id
            self._reaction_target_message_id = None
            try:
                await application_instance.telegram_manager.client(SendReactionRequest(
                    peer=self._selected_dialog_entity, msg_id=int(mid), reaction=[ReactionEmoji(emoticon=text)]
                ))
                event.input.value = ""
                event.input.placeholder = "Type a message..."
                chat_list = self.query_one(ChatList)
                if chat_list.index is not None:
                    await self._load_message_history(self._selected_dialog_entity, chat_list.children[chat_list.index])
            except Exception as error:
                self.query_one("#messages", RichLog).write(f"[red]Error: {error}[/red]")
            return

        chat_list = self.query_one(ChatList)
        item = chat_list.children[chat_list.index] if chat_list.index is not None else None
        if isinstance(item, ChatItem):
            await application_instance.telegram_manager.client.send_message(entity=item.dialog.entity, message=text)
            event.input.value = ""
            await self._load_message_history(item.dialog.entity, item)
