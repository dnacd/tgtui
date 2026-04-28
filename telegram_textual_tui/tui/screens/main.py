"""
Main application screen of the Telegram Textual TUI.
Provides a multi-column layout for chat selection and message history.
"""

from typing import TYPE_CHECKING, Any, Optional

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
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, ListView, RichLog, Tabs

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

    def __init__(self, *args, **kwargs):
        """
        Initialize the main screen state variables.
        """
        super().__init__(*args, **kwargs)
        self._selected_dialog_id = None
        self._selected_dialog_entity = None
        self._read_outbox_maximum_id = 0
        self._reaction_target_message_id = None
        self._last_received_message_id = None

    BINDINGS = [
        Binding("/", "focus_search", "Search"),
        Binding("ctrl+s", "focus_search", "Search", show=False),
        Binding("ctrl+l", "focus_chat_list", "Chats"),
        Binding("ctrl+i", "focus_message_input", "Input"),
        Binding("tab", "focus_message_input", "Input", show=False),
        Binding("escape", "focus_message_input", "Input", show=False),
        Binding("p", "show_my_profile", "My Profile"),
        Binding("u", "show_partner_profile", "User Profile"),
        Binding("r", "react_to_last_message", "React Last"),
        Binding("l", "reload_all_dialogs", "Reload"),
        Binding("pageup", "scroll_messages_up", "Scroll Up", show=False),
        Binding("pagedown", "scroll_messages_down", "Scroll Down", show=False),
        Binding("[", "prev_tab", "Previous Tab", show=False),
        Binding("]", "next_tab", "Next Tab", show=False),
    ]

    async def action_next_tab(self) -> None:
        """Switch to the next chat category tab."""
        self.query_one(ChatTabs).action_next_tab()

    async def action_prev_tab(self) -> None:
        """Switch to the previous chat category tab."""
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
        """Scroll the message history log upwards."""
        self.query_one("#messages", RichLog).scroll_up()

    async def action_scroll_messages_down(self) -> None:
        """Scroll the message history log downwards."""
        self.query_one("#messages", RichLog).scroll_down()

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
            if chat_list.highlighted_child:
                await self._load_message_history(self._selected_dialog_entity, chat_list.highlighted_child)
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
        """Update the sidebar with the latest 50 dialogs."""
        application_instance: TGTApp = self.app
        chat_list = self.query_one(ChatList)
        chat_list.clear()
        dialogs = await application_instance.telegram_manager.client.get_dialogs(limit=50)
        for dialog in dialogs:
            await chat_list.append(ChatItem(dialog))

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
            sender = await event.get_sender()
            name = get_telegram_entity_title(sender)
            sid = getattr(sender, "id", 0)

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

    @on(Tabs.TabActivated)
    def on_tab_activated(self) -> None:
        """Handle chat category tab switching."""
        self._sync_chat_filter()

    @on(Input.Changed, "#chat-search")
    def on_search_filter_changed(self) -> None:
        """Filter the chat list sidebar based on search term."""
        self._sync_chat_filter()

    @on(Input.Submitted, "#chat-search")
    def on_search_submitted(self) -> None:
        """
        Handle search submission by focusing the chat list.
        Allows for immediate keyboard navigation after search.
        """
        chat_list = self.query_one(ChatList)
        if chat_list.index is not None:
            chat_list.focus()

    def _sync_chat_filter(self) -> None:
        """
        Coordinate filtering between category tabs and search input.
        """
        try:
            search_term = self.query_one("#chat-search", Input).value
            active_tab = self.query_one(ChatTabs).active_tab
            category = active_tab.id if active_tab else "all"
            self.query_one(ChatList).apply_filter(category, search_term)
        except Exception:
            # Handle cases where widgets might not be mounted yet
            pass

    async def _load_message_history(self, entity: Any, item: Optional[ChatItem] = None) -> None:
        """Fetch and render message history for the selected peer."""
        application_instance: TGTApp = self.app
        self._selected_dialog_id = entity.id
        self._selected_dialog_entity = entity

        dialog_data = getattr(item, "dialog", None)
        self._read_outbox_maximum_id = getattr(dialog_data, "read_outbox_max_id", 0)
        if self._read_outbox_maximum_id == 0 and hasattr(dialog_data, "dialog"):
            self._read_outbox_maximum_id = getattr(dialog_data.dialog, "read_outbox_max_id", 0)

        log = self.query_one("#messages", RichLog)
        log.clear()

        try:
            await application_instance.telegram_manager.client.send_read_acknowledge(entity)
            if item:
                try:
                    item.query_one(".chat-unread").remove()
                except Exception:
                    pass
        except Exception:
            pass

        messages_list = []
        async for msg in application_instance.telegram_manager.client.iter_messages(entity, limit=20):
            messages_list.append(msg)

        if messages_list:
            self._last_received_message_id = messages_list[0].id

        is_dm = isinstance(entity, User)
        for msg in reversed(messages_list):
            sender = await msg.get_sender()
            sid = getattr(sender, "id", 0)
            name = get_telegram_entity_title(sender)
            
            status = ""
            if msg.out and is_dm:
                status = " [blue]vv[/blue]" if msg.id <= self._read_outbox_maximum_id else " [dim]v[/dim]"
            
            reacts = self._format_message_reactions(msg.id, getattr(msg, "reactions", None))
            link = f"[@click=screen.show_user_profile({sid})][bold cyan]{name}[/bold cyan][/@click]"
            log.write(f"{link}: {msg.text or '[Media]'}{status}{reacts}")

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
                await self._load_message_history(self._selected_dialog_entity, self.query_one(ChatList).highlighted_child)
            except Exception as error:
                self.query_one("#messages", RichLog).write(f"[red]Error: {error}[/red]")
            return

        item = self.query_one(ChatList).highlighted_child
        if isinstance(item, ChatItem):
            await application_instance.telegram_manager.client.send_message(entity=item.dialog.entity, message=text)
            event.input.value = ""
            await self._load_message_history(item.dialog.entity, item)
