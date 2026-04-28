"""
Avatar management and rendering system.

This module handles the lifecycle of user avatars, including:
1. Downloading profile photos from Telegram using Telethon.
2. Rendering photos into ANSI truecolor art using a native Rust extension.
3. Generating unique, symmetric geometric patterns (identicons) for users without photos.
4. Persistent disk caching of rendered art to ensure UI performance.
5. Concurrency control and throttling to minimize CPU impact.
"""

import asyncio
import hashlib
import logging
import random
from pathlib import Path
from typing import Optional, Union, Tuple

from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

from telegram_textual_tui.core.config import APPLICATION_DIRECTORY, AVATAR_CACHE_DIRECTORY

try:
    import ansi_render_native
except ImportError:
    ansi_render_native = None

logger = logging.getLogger("AvatarManager")


class AvatarManager:
    """
    Orchestrates the retrieval, processing, and fallback generation of Telegram avatars.
    
    This class ensures that every user has a visual representation in the TUI, 
    either by rendering their real photo or generating a deterministic identicon.
    It uses disk caching and a semaphore-controlled rendering queue to maintain 
    smooth UI performance even during heavy background tasks.
    
    Attributes:
        client: The active Telethon TelegramClient instance.
        cache_dir: Path to the directory where rendered avatars are stored.
    """

    def __init__(self, client: TelegramClient):
        """
        Initialize the AvatarManager.

        Args:
            client: An authenticated Telethon client used for downloading photos.
        """
        self.client = client
        self.cache_dir = AVATAR_CACHE_DIRECTORY
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache to avoid redundant disk I/O
        self._memory_cache: Dict[str, str] = {}
        # Strictly serialize rendering tasks to minimize CPU impact
        self._render_semaphore = asyncio.Semaphore(1)
        # Limit concurrent network downloads to prevent network storm
        self._download_semaphore = asyncio.Semaphore(3)
        
        self._setup_logging()

    def _setup_logging(self) -> None:
        """
        Configure the logging system to record application events to a file.
        """
        log_file = APPLICATION_DIRECTORY / "app.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _get_cache_path(self, peer_id: int, size_key: str) -> Path:
        """
        Generate a unique file path for a cached avatar based on peer ID and size.

        Args:
            peer_id: The unique Telegram ID of the peer.
            size_key: A string indicating the size variant (e.g., 'large', 'small').

        Returns:
            A Path object pointing to the cached .txt file.
        """
        name_hash = hashlib.md5(f"{peer_id}_{size_key}".encode()).hexdigest()
        return self.cache_dir / f"{name_hash}.txt"

    async def get_avatar(self, peer: Union[User, Chat, Channel], size: str = "large") -> str:
        """
        Retrieve an ANSI-rendered avatar for the specified Telegram peer.
        
        If a cached version exists, it is returned immediately. If the peer has no 
        photo, a deterministic geometric identicon is generated and cached. 
        Real photos are rendered using the native Rust extension.
        
        This method is guaranteed to return a valid ANSI string.

        Args:
            peer: The Telethon peer entity to get the avatar for.
            size: The size variant to retrieve ('large' for profiles, 'small' for lists).

        Returns:
            A string containing ANSI escape sequences for truecolor art.
        """
        if not peer:
            return self._generate_identicon(0, size == "large")

        try:
            peer_id = peer.id
            cache_key = f"{peer_id}_{size}"
            
            if cache_key in self._memory_cache:
                return self._memory_cache[cache_key]

            cache_path = self._get_cache_path(peer_id, size)
            loop = asyncio.get_running_loop()

            if await loop.run_in_executor(None, cache_path.exists):
                ansi_data = await loop.run_in_executor(None, cache_path.read_text, "utf-8")
                self._memory_cache[cache_key] = ansi_data
                return ansi_data

            temp_photo = self.cache_dir / f"temp_{peer_id}.jpg"
            
            async with self._download_semaphore:
                path = await self.client.download_profile_photo(peer, file=str(temp_photo))
            
            if path and ansi_render_native:
                original_bytes = await loop.run_in_executor(None, temp_photo.read_bytes)
                cols = 50 if size == "large" else 16
                
                async with self._render_semaphore:
                    rendered_text = await loop.run_in_executor(
                        None,
                        self._render_to_ansi_sync, 
                        original_bytes, 
                        cols
                    )
                
                if rendered_text:
                    await loop.run_in_executor(None, lambda: cache_path.write_text(rendered_text, encoding="utf-8"))
                    self._memory_cache[cache_key] = rendered_text
                    return rendered_text
            
            identicon = self._generate_identicon(peer_id, size == "large")
            await loop.run_in_executor(None, lambda: cache_path.write_text(identicon, encoding="utf-8"))
            self._memory_cache[cache_key] = identicon
            return identicon

        except Exception as e:
            logger.error(f"Failed to process avatar: {e}")
            fallback_id = getattr(peer, "id", 0) if peer else 0
            return self._generate_identicon(fallback_id, size == "large")
        finally:
            try:
                temp_photo_path = self.cache_dir / f"temp_{getattr(peer, 'id', '0')}.jpg"
                if temp_photo_path.exists():
                    temp_photo_path.unlink()
            except Exception:
                pass

    def _generate_identicon(self, peer_id: int, is_large: bool) -> str:
        """
        Generate a symmetric geometric pattern (identicon) based on peer ID.
        
        The generated pattern is deterministic and uses ANSI half-blocks 
        to match the visual style of rendered real avatars. It serves as a 
        stylized fallback for users without a profile picture.

        Args:
            peer_id: Unique ID used as a seed for the pattern and color.
            is_large: Whether to generate a high-resolution (profile-sized) version.

        Returns:
            An ANSI truecolor string representing the geometric pattern.
        """
        width = 50 if is_large else 16
        height_chars = 25 if is_large else 8
        height_pixels = height_chars * 2
        
        # Use abs(peer_id) to ensure valid random seed
        rng = random.Random(abs(peer_id))
        
        # Pick a base color (Truecolor range)
        r = rng.randint(60, 220)
        g = rng.randint(60, 220)
        b = rng.randint(60, 220)
        
        # Create a bit-grid for the pattern (will be mirrored horizontally)
        grid_size = 5
        grid = [[rng.choice([True, False, False]) for _ in range(grid_size)] for _ in range(grid_size * 2)]
        
        output = []

        def get_pixel(px: int, py: int) -> Tuple[int, int, int]:
            nx = px / width
            ny = py / height_pixels
            
            gx = int(nx * grid_size * 2)
            gy = int(ny * grid_size * 2)
            
            gx = min(gx, grid_size * 2 - 1)
            gy = min(gy, grid_size * 2 - 1)
            
            if gx >= grid_size:
                gx = (grid_size * 2 - 1) - gx
            
            if grid[gy][gx]:
                return (r, g, b)
            return (30, 30, 30)

        for y in range(0, height_pixels, 2):
            line = []
            for x in range(width):
                tr, tg, tb = get_pixel(x, y)
                br, bg, bb = get_pixel(x, y + 1)
                line.append(f"\x1b[38;2;{tr};{tg};{tb};48;2;{br};{bg};{bb}m▀")
            output.append("".join(line) + "\x1b[0m")
            
        return "\n".join(output)

    def _render_to_ansi_sync(self, data: bytes, cols: int) -> str:
        """
        Synchronously invoke the native Rust renderer.
        
        This method is designed to be called within a thread pool to avoid 
        blocking the main event loop.

        Args:
            data: Raw image bytes (JPEG/PNG).
            cols: The target width in terminal columns.

        Returns:
            An ANSI truecolor string representing the rendered art.
        """
        if not ansi_render_native:
            return ""
        
        try:
            return ansi_render_native.render_to_ansi(
                data=data,
                cols=cols,
                bright=1.1,
                sat=1.1,
                contrast=1.2
            )
        except Exception as e:
            logger.error(f"Native renderer error: {e}")
            return ""
