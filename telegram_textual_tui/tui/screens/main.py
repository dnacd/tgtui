"""
Main application screen of the Telegram Textual TUI.
Provides a multi-column layout for chat selection and message history.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
import time

from telethon import events, utils
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import (
    Channel,
    Chat,
    ChatReactionsNone,
    ChatReactionsSome,
    ReactionEmoji,
    User,
)
from rich.panel import Panel
from rich.text import Text
from textual import events as textual_events, on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, ListView, RichLog, Tabs

from telegram_textual_tui.tui.config.keymap import Keymap
from telegram_textual_tui.tui.controllers.chat_controller import ChatController
from telegram_textual_tui.tui.controllers.history_controller import HistoryController
from telegram_textual_tui.tui.controllers.message_controller import MessageController
from telegram_textual_tui.tui.screens.profile import ProfileScreen
from telegram_textual_tui.tui.widgets.chat_list import ChatItem, ChatList
from telegram_textual_tui.tui.widgets.chat_tabs import ChatTabs
from telegram_textual_tui.utils.formatters import (
    get_telegram_entity_title,
    get_message_sender_id,
    format_message_reactions,
)

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
        self._me = None
        self._read_outbox_maximum_id = 0
        self._reaction_target_message_id = None
        self._last_received_message_id = None
        
        self._loaded_messages: List[Any] = []
        self._sender_cache: Dict[int, str] = {}
        self._is_loading_more = False
        self._last_load_time = 0.0

        self._history_controller = HistoryController(self.app.telegram_manager)
        self._message_controller = MessageController(self.app.telegram_manager)
        self._chat_controller = ChatController(self.app.telegram_manager)

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
        """Switch to the current user's profile screen."""
        self.app.push_screen(ProfileScreen())

    async def action_show_partner_profile(self) -> None:
        """Show the profile of the current chat partner if available."""
        if isinstance(self._selected_dialog_entity, User):
            self.app.push_screen(ProfileScreen(user_id=self._selected_dialog_entity.id))

    async def action_react_to_last_message(self) -> None:
        """Open reaction selection for the most recently received message."""
        if self._last_received_message_id:
            await self.action_send_reaction(self._last_received_message_id)

    async def action_focus_search(self) -> None:
        """Move focus to the chat search input."""
        self.query_one("#chat-search", Input).focus()

    async def action_focus_chat_list(self) -> None:
        """Move focus to the chat selection list."""
        self.query_one("#chat-list", ChatList).focus()

    async def action_focus_message_input(self) -> None:
        """Move focus to the message input field or messages log if input is disabled."""
        input_widget = self.query_one("#message-input", Input)
        if not input_widget.disabled:
            input_widget.focus()
        else:
            self.query_one("#messages", RichLog).focus()

    async def action_scroll_messages_up(self) -> None:
        """Scroll the message history log upwards and trigger pagination if at top."""
        messages_log = self.query_one("#messages", RichLog)
        messages_log.scroll_up()
        if messages_log.scroll_offset.y <= 1:
            await self.action_load_more_history()

    async def action_scroll_messages_down(self) -> None:
        """Scroll the message history log downwards."""
        self.query_one("#messages", RichLog).scroll_down()

    async def action_load_more_history(self) -> None:
        """Fetch older messages and prepend them to the view with debouncing."""
        if not self._selected_dialog_entity or self._is_loading_more or not self._loaded_messages:
            return
            
        current_time = time.time()
        if current_time - self._last_load_time < 1.5:
            return

        self._is_loading_more = True
        self._last_load_time = current_time
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
        """Switch to a user's profile based on their ID."""
        if user_id:
            self.app.push_screen(ProfileScreen(user_id=user_id))

    async def action_show_reactions(self, message_id: int) -> None:
        """Fetch and display users who reacted to a specific message."""
        try:
            users = await self._message_controller.get_message_reactions_users(
                self._selected_dialog_entity, int(message_id)
            )
            names = [get_telegram_entity_title(user) for user in users]
            log = self.query_one("#messages", RichLog)
            if names:
                log.write(f"[yellow]Reacted by:[/yellow] {', '.join(names)}")
            else:
                log.write("[dim]No reaction details.[/dim]")
        except Exception as error:
            self.query_one("#messages", RichLog).write(f"[red]Error: {error}[/red]")

    async def action_quick_react(self, message_id: int, emoticon: str) -> None:
        """Send a reaction to Telegram and refresh the message view."""
        try:
            await self._message_controller.send_reaction(
                self._selected_dialog_entity, int(message_id), emoticon
            )
            chat_list = self.query_one(ChatList)
            if chat_list.index is not None:
                await self._load_message_history(
                    self._selected_dialog_entity, 
                    chat_list.children[chat_list.index]
                )
        except Exception as error:
            self.query_one("#messages", RichLog).write(f"[red]Failed to react: {error}[/red]")

    async def action_send_reaction(self, message_id: int) -> None:
        """Dynamically fetch available reactions from Telegram and display as clickable options."""
        application_instance: TGTApp = self.app
        messages_log = self.query_one("#messages", RichLog)

        allowed_emojis = await self._message_controller.get_available_reactions()
        if not allowed_emojis:
            allowed_emojis = await self._message_controller.get_recent_reactions()

        if isinstance(self._selected_dialog_entity, (Chat, Channel)):
            try:
                if isinstance(self._selected_dialog_entity, Channel):
                    full = await application_instance.telegram_manager.client(
                        GetFullChannelRequest(self._selected_dialog_entity)
                    )
                else:
                    full = await application_instance.telegram_manager.client(
                        GetFullChatRequest(self._selected_dialog_id)
                    )
                
                settings = full.full_chat.available_reactions
                if isinstance(settings, ChatReactionsNone):
                    messages_log.write("[red]Reactions are disabled here.[/red]")
                    return
                elif isinstance(settings, ChatReactionsSome):
                    allowed_emojis = [
                        r.emoticon for r in settings.reactions 
                        if isinstance(r, ReactionEmoji)
                    ]
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
        chat_list = self.query_one(ChatList)
        chat_list.clear()
        dialogs = await self._chat_controller.fetch_dialogs(limit=100)
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
        messages_log = self.query_one("#messages", RichLog)
        messages_log.can_focus = True
        messages_log.write("[dim]Select a chat to begin...[/dim]")
        
        application_instance: TGTApp = self.app
        if application_instance.telegram_manager:
            self._me = await application_instance.telegram_manager.get_authenticated_user_details()
            if self._me:
                self._sender_cache[self._me.id] = get_telegram_entity_title(self._me)

            application_instance.telegram_manager.client.add_event_handler(
                self._handle_incoming_new_message, events.NewMessage
            )
            application_instance.telegram_manager.client.add_event_handler(
                self._handle_message_read, events.MessageRead
            )
            
            self.set_interval(5.0, self._poll_read_status)
            await self.action_reload_all_dialogs()

    async def _poll_read_status(self) -> None:
        """Periodically check for read status updates to ensure UI consistency."""
        if not self._selected_dialog_entity or not self._selected_dialog_id:
            return

        new_max_id = await self._chat_controller.get_read_outbox_max_id(self._selected_dialog_entity)
        if new_max_id > self._read_outbox_maximum_id:
            self._read_outbox_maximum_id = new_max_id
            await self._render_messages()
            chat_list = self.query_one(ChatList)
            for item in chat_list.children:
                if isinstance(item, ChatItem) and item.dialog.id == self._selected_dialog_id:
                    item.dialog.read_outbox_max_id = new_max_id
                    break

    async def on_unmount(self) -> None:
        """Cleanup event handlers."""
        application_instance: TGTApp = self.app
        if application_instance.telegram_manager:
            application_instance.telegram_manager.client.remove_event_handler(
                self._handle_incoming_new_message, events.NewMessage
            )
            application_instance.telegram_manager.client.remove_event_handler(
                self._handle_message_read, events.MessageRead
            )

    async def _handle_message_read(self, event: events.MessageRead.Event) -> None:
        """Update read status indicators and chat list badges when messages are read."""
        event_peer_id = utils.get_peer_id(event.peer)
        
        chat_list = self.query_one(ChatList)
        for item in chat_list.children:
            if isinstance(item, ChatItem) and item.dialog.id == event_peer_id:
                if event.out:
                    if event.max_id > getattr(item.dialog, "read_outbox_max_id", 0):
                        item.dialog.read_outbox_max_id = event.max_id
                else:
                    item.dialog.unread_count = 0
                    try:
                        item.query_one(".chat-unread").remove()
                    except Exception:
                        pass
                break

        if self._selected_dialog_id == event_peer_id:
            if event.out:
                if event.max_id > self._read_outbox_maximum_id:
                    self._read_outbox_maximum_id = event.max_id
                    await self._render_messages()
                    self.notify("Message read", severity="information", timeout=2)

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

    async def on_key(self, event: textual_events.Key) -> None:
        """Handle global key events for history loading triggers."""
        if event.key in ("up", "pageup"):
            messages_log = self.query_one("#messages", RichLog)
            if messages_log.scroll_offset.y <= 1:
                await self.action_load_more_history()

    def _sync_chat_filter(self) -> None:
        """Coordinate filtering between category tabs and search input."""
        try:
            search_term = self.query_one("#chat-search", Input).value
            active_tab = self.query_one(ChatTabs).active_tab
            category = active_tab.id if active_tab else "all"
            self.query_one(ChatList).apply_filter(category, search_term)
        except Exception:
            pass

    async def _handle_incoming_new_message(self, event: events.NewMessage.Event) -> None:
        """Process real-time messages and update the UI."""
        chat_id = event.chat_id
        if self._selected_dialog_id == chat_id:
            if any(msg.id == event.message.id for msg in self._loaded_messages):
                return

            self._last_received_message_id = event.message.id
            self._loaded_messages.append(event.message)
            await self._append_message_to_log(event.message)
            await self._chat_controller.mark_as_read(event.input_chat)
            return

        if event.message.out:
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

    async def _get_message_panel(self, msg: Any) -> Panel:
        """Create a Rich Panel for a single message, utilizing cache for sender names."""
        sid = get_message_sender_id(msg)
        
        if sid is None and msg.out and self._me:
            sid = self._me.id
        
        if sid is not None and sid not in self._sender_cache:
            try:
                sender = await msg.get_sender()
                self._sender_cache[sid] = get_telegram_entity_title(sender)
            except Exception:
                self._sender_cache[sid] = "Unknown"

        name = self._sender_cache.get(sid, "Unknown")
        timestamp = msg.date.strftime("%H:%M")
        
        status_dot = ""
        if msg.out:
            is_saved_messages = self._me and self._selected_dialog_id == self._me.id
            is_read = is_saved_messages or (self._read_outbox_maximum_id > 0 and msg.id <= self._read_outbox_maximum_id)
            dot_color = "bold purple" if is_read else "dim"
            status_dot = f" [{dot_color}]•[/{dot_color}]"
        
        title = f"[bold cyan]{name}[/] [dim]• {timestamp}[/]"
        subtitle = f"{status_dot}{format_message_reactions(msg.id, getattr(msg, 'reactions', None))}"
        
        return Panel(
            Text.from_markup(msg.text or "[dim][Media][/dim]"),
            title=Text.from_markup(title),
            subtitle=Text.from_markup(subtitle),
            title_align="left",
            subtitle_align="right",
            border_style="blue" if msg.out else "white",
            padding=(0, 1),
            expand=True
        )

    async def _append_message_to_log(self, msg: Any) -> None:
        """Add a single message to the bottom of the log and scroll to it."""
        log = self.query_one("#messages", RichLog)
        panel = await self._get_message_panel(msg)
        log.write(panel)
        log.scroll_end()

    async def _render_messages(self) -> None:
        """Render all loaded messages to the log using an optimized cache-aware process."""
        log = self.query_one("#messages", RichLog)
        log.clear()
        
        for msg in self._loaded_messages:
            panel = await self._get_message_panel(msg)
            log.write(panel)
        
        log.scroll_end()

    async def _load_message_history(self, entity: Any, item: Optional[ChatItem] = None) -> None:
        """
        Fetch and render initial message history for the selected peer.
        """
        self._selected_dialog_id = utils.get_peer_id(entity)
        self._selected_dialog_entity = entity
        
        self._loaded_messages = []
        self._sender_cache = {}
        self._read_outbox_maximum_id = 0
        
        if self._me:
            self._sender_cache[self._me.id] = get_telegram_entity_title(self._me)

        if item and hasattr(item.dialog, "read_outbox_max_id"):
            self._read_outbox_maximum_id = item.dialog.read_outbox_max_id
        else:
            self._read_outbox_maximum_id = await self._chat_controller.get_read_outbox_max_id(entity)

        log = self.query_one("#messages", RichLog)
        log.clear()

        can_send, placeholder = self._message_controller.get_messaging_status(entity)
        input_widget = self.query_one("#message-input", Input)
        input_widget.disabled = not can_send
        input_widget.placeholder = placeholder
        input_widget.value = ""

        if can_send:
            input_widget.focus()
        else:
            log.focus()

        await self._chat_controller.mark_as_read(entity)
        if item:
            try:
                item.query_one(".chat-unread").remove()
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
        if isinstance(event.item, ChatItem):
            await self._load_message_history(event.item.dialog.entity, event.item)

    @on(Input.Submitted, "#message-input")
    async def on_message_input_submitted(self, event: Input.Submitted) -> None:
        """Handle sending text or emojis based on the current input context."""
        text = event.value.strip()
        if not text:
            return

        if self._reaction_target_message_id is not None:
            mid = self._reaction_target_message_id
            self._reaction_target_message_id = None
            try:
                await self._message_controller.send_reaction(
                    self._selected_dialog_entity, int(mid), text
                )
                event.input.value = ""
                event.input.placeholder = "Type a message..."
                
                chat_list = self.query_one(ChatList)
                if chat_list.index is not None:
                    await self._load_message_history(
                        self._selected_dialog_entity, 
                        chat_list.children[chat_list.index]
                    )
            except Exception as error:
                self.query_one("#messages", RichLog).write(f"[red]Error: {error}[/red]")
            return

        chat_list = self.query_one(ChatList)
        item = chat_list.children[chat_list.index] if chat_list.index is not None else None
        if isinstance(item, ChatItem):
            sent_msg = await self._message_controller.send_text(item.dialog.entity, text)
            event.input.value = ""
            
            if self._selected_dialog_id is not None:
                self._loaded_messages.append(sent_msg)
                await self._append_message_to_log(sent_msg)
