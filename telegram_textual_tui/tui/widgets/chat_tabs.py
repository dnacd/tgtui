"""
Component for chat category tabs.
"""

from textual.widgets import Tab, Tabs


class ChatTabs(Tabs):
    """
    Tabs widget for filtering Telegram chats by category.
    """

    can_focus = False

    def __init__(self, **kwargs) -> None:
        """Initialize tabs with predefined categories."""
        super().__init__(
            Tab("All", id="all"),
            Tab("Private", id="private"),
            Tab("Groups", id="groups"),
            Tab("Bots", id="bots"),
            **kwargs
        )

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tab_ids = ["all", "private", "groups", "bots"]
        try:
            current_index = tab_ids.index(self.active)
        except (ValueError, TypeError):
            current_index = 0
        next_index = (current_index + 1) % len(tab_ids)
        self.active = tab_ids[next_index]

    def action_prev_tab(self) -> None:
        """Switch to the previous tab."""
        tab_ids = ["all", "private", "groups", "bots"]
        try:
            current_index = tab_ids.index(self.active)
        except (ValueError, TypeError):
            current_index = 0
        prev_index = (current_index - 1) % len(tab_ids)
        self.active = tab_ids[prev_index]
