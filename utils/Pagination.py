import discord
from typing import Callable, Optional, Awaitable
import math

GetPage = Callable[[int], Awaitable[tuple[discord.Embed, int]]]

class Pagination(discord.ui.View):
    def __init__(self, source, get_page: GetPage):
        super().__init__(timeout=100)
        self.source = source  # ctx or interaction
        self.get_page = get_page
        self.total_pages: int = 1
        self.index: int = 1
        self.message: Optional[discord.Message] = None

    async def send_message(self, embed):
        self.update_buttons()
        if isinstance(self.source, discord.Interaction):
            await self.source.response.send_message(embed=embed, view=self)
        else:  # assume ctx
            self.message = await self.source.send(embed=embed, view=self)

    async def navigate(self):
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await self.send_message(emb)

    async def edit_page(self, interaction: discord.Interaction):
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await interaction.response.edit_message(embed=emb, view=self)

    def update_buttons(self):
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue
            # Disable all if only 1 page
            if self.total_pages == 1:
                child.disabled = True
                continue
            # Disable previous/next appropriately
            if child.emoji == "◀️":
                child.disabled = self.index <= 1
            elif child.emoji == "▶️":
                child.disabled = self.index >= self.total_pages
            elif child.emoji in ("⏮️", "⏭️"):
                # Flip jump emoji depending on current index
                child.emoji = "⏮️" if self.index > self.total_pages // 2 else "⏭️"

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button):
        if self.index > 1:
            self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button):
        if self.index < self.total_pages:
            self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def jump(self, interaction: discord.Interaction, button):
        if self.index <= self.total_pages // 2:
            self.index = self.total_pages
        else:
            self.index = 1
        await self.edit_page(interaction)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return math.ceil(total_results / results_per_page)
