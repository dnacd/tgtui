"""
Custom Textual widget for rendering ANSI ASCII art.
"""

from typing import Optional, Union
from rich.text import Text
from textual.widgets import Static


class AsciiImage(Static):
    """
    A high-performance widget for displaying ANSI-encoded art strings.
    
    This widget optimizes the rendering of complex ANSI escape sequences by 
    caching the parsed Rich Text object. This prevents the TUI from freezing 
    when large or detailed ASCII art is displayed or updated, as it avoids 
    re-parsing the ANSI string on every UI tick.
    
    Attributes:
        fallback_text: Text to display if no image data is available.
        is_loading: Boolean state indicating if a render task is in progress.
    """

    def __init__(self, image_data: Optional[str] = None, fallback_text: str = "?", **kwargs):
        """
        Initialize the AsciiImage widget.

        Args:
            image_data: Optional initial ANSI string to display.
            fallback_text: Placeholder characters (e.g., initials) to show 
                           if image_data is missing or failing.
            **kwargs: Additional arguments passed to the Static widget.
        """
        super().__init__(**kwargs)
        self.fallback_text = fallback_text
        self.is_loading = image_data is None
        self._cached_renderable: Optional[Text] = None
        
        if image_data:
            self._cached_renderable = Text.from_ansi(image_data)

    def update_image(self, ansi_text: str) -> None:
        """
        Update the displayed image with a new ANSI string.
        
        Parses the ANSI sequences into a Rich Text object once and caches it.
        Resets the loading state and triggers a widget refresh.

        Args:
            ansi_text: The new ANSI-encoded string to display.
        """
        if ansi_text:
            self._cached_renderable = Text.from_ansi(ansi_text)
        self.is_loading = False
        self.refresh()

    def set_loading(self, loading: bool = True) -> None:
        """
        Manually toggle the visual loading state.

        Args:
            loading: Whether to show the 'Rendering...' indicator.
        """
        self.is_loading = loading
        self.refresh()

    def render(self) -> Union[Text, str]:
        """
        Produce the renderable content for Textual's compositor.
        
        Priority order:
        1. 'Rendering...' if is_loading is True.
        2. The cached ANSI Text object if it exists.
        3. The fallback_text as a final resort.

        Returns:
            A Rich Text object, a loading string, or the fallback text.
        """
        if self.is_loading:
            return "[bold cyan]Rendering...[/bold cyan]"
        
        if self._cached_renderable:
            return self._cached_renderable
            
        return self.fallback_text
