import asyncio
import logging
import re
from typing import Any

import discord
from lib import BELL, LOADING

from quotient.models import (
    Scrim,
    ScrimAssignedSlot,
    ScrimsBannedUser,
    ScrimSlotReminder,
    ScrimsSlotManager,
)

from ..utility.selectors import (
    ScrimsSlotSelector,
    prompt_scrims_selector,
    prompt_scrims_slot_selector,
)


class TeamNameInput(discord.ui.Modal, title="Slot Claim Form"):
    team_name = discord.ui.TextInput(label="Enter your team name:", min_length=3, max_length=20)

    async def on_submit(self, inter: discord.Interaction):
        await inter.response.defer()


SLOT_CLAIM_LOCK = asyncio.Lock()


class ScrimSlotmPublicPanel(discord.ui.View):
    def __init__(self, record: ScrimsSlotManager):
        super().__init__(timeout=None)
        self.record = record

        self.bot = record.bot

    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception, item: discord.ui.Item[Any]) -> None:
        if isinstance(error, discord.NotFound):
            return
        logging.error(f"Error in {self.__class__.__name__}: {error}")

    @discord.ui.button(label="Cancel Slot", style=discord.ButtonStyle.red, custom_id="cancel_scrims_slot")
    async def cancel_scrims_slot(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer(thinking=True, ephemeral=True)

        if not (user_slots := await self.record.get_user_slots(inter.user.id)):
            return await inter.followup.send(
                embed=self.record.bot.error_embed("You don't have any slots that can be cancelled."), ephemeral=True
            )

        selected_slots = await prompt_scrims_slot_selector(
            inter, user_slots, "Please select the slots you want to cancel from dropdown.", multiple=True, force_dropdown=True
        )
        if not selected_slots:
            return

        prompt = await self.record.bot.prompt(
            inter,
            inter.user,
            "Are you sure you want to cancel the selected slots?",
            msg_title="This action can't be undone!",
            confirm_btn_label="Yes, Cancel",
            cancel_btn_label="No, Abort",
            ephemeral=True,
        )
        if not prompt:
            return

        m = await inter.followup.send(f"Please wait, cancelling selected slots {LOADING}", ephemeral=True)

        for slot in selected_slots:
            slot.scrim.available_slots.append(slot.num)
            slot.scrim.available_slots = sorted(slot.scrim.available_slots)
            await slot.scrim.save(update_fields=["available_slots"])
            await slot.delete()

            slot.bot.loop.create_task(slot.scrim.refresh_slotlist_message())

            await self.record.dispatch_reminders(slot.scrim.id)

        await m.edit(content="Selected slots have been cancelled successfully.", embed=None, view=None)
        await self.record.refresh_public_message()

        cancelled_slots = ""
        for slot in selected_slots:
            cancelled_slots += f"- Slot {slot.num} - {slot.scrim}\n"

        await slot.scrim.send_log(
            msg=f"Scrims Slots Cancelled by {inter.user.mention} through Cancel-Claim Panel:\n{cancelled_slots}",
            title="Scrims Slot Cancelled",
            color=discord.Color.red(),
            add_contact_btn=False,
        )

    @discord.ui.button(label="Claim Slot", style=discord.ButtonStyle.green, custom_id="claim_scrims_slot")
    async def claim_scrims_slot(self, inter: discord.Interaction, btn: discord.ui.Button):
        m = TeamNameInput()
        await inter.response.send_modal(m)
        await m.wait()
        team_name = "Team " + re.sub(r"team|name|[^\w\s]", "", m.team_name.value.lower()).strip().title()

        if await ScrimsBannedUser.filter(user_id=inter.user.id, guild_id=inter.guild_id).exists():
            return await inter.followup.send(
                embed=self.record.bot.error_embed("You are banned from claiming slots in this server."), ephemeral=True
            )

        available_scrims = await self.record.claimable_scrims()
        if not available_scrims:
            return await inter.followup.send(embed=self.record.bot.error_embed("No slots available to claim."), ephemeral=True)

        v = discord.ui.View(timeout=60)
        v.add_item(ClaimSlotSelector(available_scrims))
        m = await inter.followup.send("Please select the slot you want to claim:", view=v, ephemeral=True)
        await v.wait()

        if not v.selected_slot:
            return

        scrim_id, slot_num = v.selected_slot.split(":")

        scrim = await Scrim.get_or_none(pk=scrim_id)
        if not scrim:
            return await inter.followup.send(embed=self.record.bot.error_embed("Scrim not found."), ephemeral=True)

        if not self.record.allow_multiple_slots:
            if await ScrimAssignedSlot.filter(leader_id=inter.user.id, scrim=scrim).exists():
                return await inter.followup.send(
                    embed=self.record.bot.error_embed("You already have a slot in this scrim, can't claim another."), ephemeral=True
                )

        async with SLOT_CLAIM_LOCK:
            m = await inter.followup.send(f"Please wait, claiming `slot {slot_num}` for you ...{LOADING}", ephemeral=True)
            slot_num = int(slot_num)

            if not slot_num in scrim.available_slots:
                return await m.edit(
                    content="", embed=self.record.bot.error_embed("Someone else claimed this slot before you. Please try again.")
                )

            scrim.available_slots.remove(slot_num)
            await scrim.save(update_fields=["available_slots"])

            await ScrimAssignedSlot.create(
                scrim=scrim, leader_id=inter.user.id, team_name=team_name, num=slot_num, members=[inter.user.id]
            )

            scrim.bot.loop.create_task(scrim.refresh_slotlist_message())
            scrim.bot.loop.create_task(self.record.refresh_public_message())
            scrim.bot.loop.create_task(
                scrim.send_log(
                    f"`Slot {slot_num}` in {scrim} was claimed by {inter.user.mention}",
                    title="Slot Claimed",
                    color=discord.Color.green(),
                    add_contact_btn=False,
                )
            )

            await m.edit(content="", embed=self.record.bot.success_embed(f"`Slot {slot_num}` in {scrim} claimed successfully."))

    @discord.ui.button(label="Remind Me", emoji=BELL, custom_id="scrims_slot_reminder")
    async def scrims_remind_me(self, inter: discord.Interaction, btn: discord.ui.Button):
        await inter.response.defer()
        self.bot.logger.debug(f"User {inter.user} requested slot reminder in {inter.guild_id}")

        if not await self.record.bot.is_pro_guild(inter.guild_id):
            return await inter.followup.send(
                embed=self.bot.error_embed(
                    "`Slot Available Reminder` feature is only available for Quotient Premium servers.", title="Premium Only Feature"
                ),
            )

        self.bot.logger.debug(f"User {inter.user} is in a premium guild {inter.guild_id}")

        if await ScrimsBannedUser.filter(user_id=inter.user.id, guild_id=inter.guild_id).exists():
            return await inter.followup.send(
                embed=self.record.bot.error_embed("You are banned from claiming slots in this server."), ephemeral=True
            )

        self.bot.logger.debug(f"User {inter.user} is not banned from claiming slots in {inter.guild_id}")

        scrims = (
            await Scrim.filter(
                slotm=self.record,
                reg_ended_at__gt=self.bot.current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                match_start_time__gt=self.bot.current_time,
                reg_started_at__isnull=True,
            )
            .order_by("reg_start_time")
            .limit(25)
        )

        scrims = [s for s in scrims if not s.available_slots]

        self.bot.logger.debug(f"Found {len(scrims)} scrims for slot reminder in {inter.guild_id}")

        selected_scrims = await prompt_scrims_selector(
            inter,
            inter.user,
            scrims,
            "Please select the scrim you want to be reminded for (In DM).",
            single_scrim_only=True,
            force_dropdown=True,
        )

        if not selected_scrims:
            return

        selected_scrim = selected_scrims[0]

        if await ScrimSlotReminder.filter(user_id=inter.user.id, scrim_id=selected_scrim.id).exists():
            return await inter.followup.send(
                embed=self.record.bot.error_embed(
                    "You already have a reminder set for this scrim, we will remind you as soon as we have a slot available.",
                    title="Don't be Impatient!",
                ),
                ephemeral=True,
            )

        if not self.record.allow_multiple_slots:
            if await ScrimAssignedSlot.filter(leader_id=inter.user.id, scrim=selected_scrim).exists():
                return await inter.followup.send(
                    embed=self.record.bot.error_embed(
                        "You already have a slot in this scrim, this server doesn't allow multiple slots per scrim.",
                    ),
                    ephemeral=True,
                )

        await ScrimSlotReminder.create(user_id=inter.user.id, scrim_id=selected_scrim.id)
        await inter.followup.send(
            embed=self.bot.success_embed(
                f"You will be reminded as soon as we have a slot available for {selected_scrim}.", title="Reminder Set!"
            ),
            ephemeral=True,
        )


class ClaimSlotSelector(discord.ui.Select):
    def __init__(self, scrims: list[Scrim]):

        options = []
        for scrim in scrims:
            slots = sorted(scrim.available_slots)

            options.append(
                discord.SelectOption(
                    label=f"Slot {slots[0]} ─ #{getattr(scrim.registration_channel,'name','deleted-channel')}",
                    value=f"{scrim.id}:{slots[0]}",
                    emoji="📇",
                )
            )

        super().__init__(options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.selected_slot = self.values[0]

        self.view.stop()
