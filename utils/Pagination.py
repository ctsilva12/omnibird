import discord
from typing import Callable, Optional, Awaitable
import math
from discord.ext.commands import Context
from languages import l

GetPage = Callable[[int], Awaitable[tuple[discord.Embed, int]]]


class Pagination(discord.ui.View):
    def __init__(
        self,
        source: discord.Interaction | Context,
        get_page: GetPage,
        *,
        only_author_can_interact: bool = True,
        timeout: float = 100,
    ):
        super().__init__(timeout=timeout)

        self.source = source
        self.get_page = get_page
        self.only_author_can_interact = only_author_can_interact

        self.index: int = 1
        self.total_pages: int = 1
        self.message: Optional[discord.Message] = None

        if isinstance(source, discord.Interaction):
            self.author_id = source.user.id
        else:
            self.author_id = source.author.id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.only_author_can_interact and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                l.text("only_author_can_interact_with_pagination"),
                ephemeral=True,
            )
            return False
        return True

    async def send(self):
        embed, self.total_pages = await self.get_page(self.index)
        self._update_buttons()

        if isinstance(self.source, discord.Interaction):
            await self.source.response.send_message(embed=embed, view=self)
            self.message = await self.source.original_response()
        else:
            self.message = await self.source.send(embed=embed, view=self)

    async def _edit(self, interaction: discord.Interaction):
        embed, self.total_pages = await self.get_page(self.index)
        self._update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def _update_buttons(self):
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue

            if self.total_pages <= 1:
                child.disabled = True
                continue

            match child.custom_id:
                case "prev":
                    child.disabled = self.index <= 1
                case "next":
                    child.disabled = self.index >= self.total_pages
                case "jump":
                    child.disabled = False

    @discord.ui.button(
        emoji="◀️",
        style=discord.ButtonStyle.blurple,
        custom_id="prev",
    )
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.index > 1:
            self.index -= 1
        await self._edit(interaction)

    @discord.ui.button(
        emoji="▶️",
        style=discord.ButtonStyle.blurple,
        custom_id="next",
    )
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.index < self.total_pages:
            self.index += 1
        await self._edit(interaction)

    @discord.ui.button(
        emoji="⏭️",
        style=discord.ButtonStyle.blurple,
        custom_id="jump",
    )
    async def jump(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.index = (
            self.total_pages if self.index <= self.total_pages // 2 else 1
        )
        await self._edit(interaction)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return math.ceil(total_results / results_per_page)
    
    async def navigate(self):
        if self.message is None:
            await self.send()
