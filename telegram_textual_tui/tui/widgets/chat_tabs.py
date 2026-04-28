"""
Component for chat category tabs.
"""

from textual.widgets import Tab, Tabs


class ChatTabs(Tabs):
    """
    Tabs widget for filtering Telegram chats by category (All, Private, Groups, Bots).
    """

    can_focus = False

    def __init__(self, **kwargs) -> None:
        """
        Initialize the category tabs with predefined Telegram filters.
        """
        super().__init__(
            Tab("All", id="all"),
            Tab("Private", id="private"),
            Tab("Groups", id="groups"),
            Tab("Bots", id="bots"),
            **kwargs
        )

    def action_next_tab(self) -> None:
        """
        Cycle to the next available tab category.
        """
        tab_ids = ["all", "private", "groups", "bots"]
        try:
            current_index = tab_ids.index(self.active)
        except (ValueError, TypeError):
            current_index = 0
            
        self.active = tab_ids[(current_index + 1) % len(tab_ids)]

    def action_prev_tab(self) -> None:
        """
        Cycle to the previous available tab category.
        """
        tab_ids = ["all", "private", "groups", "bots"]
        try:
            current_index = tab_ids.index(self.active)
        except (ValueError, TypeError):
            current_index = 0
            
        self.active = tab_ids[(current_index - 1) % len(tab_ids)]
