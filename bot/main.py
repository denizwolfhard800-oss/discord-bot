import discord
from discord import app_commands
import os
from keep_alive import keep_alive
from config import get_log_channel_id, set_log_channel_id

intents = discord.Intents.default()
intents.presences = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

STATUS_LABELS = {
    discord.Status.online: ("🟢", "Online"),
    discord.Status.idle: ("🟡", "Idle"),
    discord.Status.dnd: ("🔴", "Do Not Disturb"),
    discord.Status.offline: ("⚫", "Offline"),
}


@client.event
async def on_ready():
    await tree.sync()
    log_channel_id = get_log_channel_id()
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Slash commands synced globally.")
    if log_channel_id:
        print(f"Logging presence changes to channel ID: {log_channel_id}")
    else:
        print("WARNING: No log channel set. Use /setstatus in your server to configure one.")


@tree.command(name="setstatus", description="Set the channel where presence changes are logged.")
@app_commands.describe(channel="The channel to send presence logs to")
@app_commands.default_permissions(administrator=True)
async def setstatus(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel_id(channel.id)
    await interaction.response.send_message(
        f"✅ Presence logs will now be sent to {channel.mention}.",
        ephemeral=True,
    )
    print(f"Log channel updated to #{channel.name} (ID: {channel.id}) by {interaction.user}")


@client.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if before.status == after.status:
        return

    log_channel_id = get_log_channel_id()
    if not log_channel_id:
        return

    channel = client.get_channel(log_channel_id)
    if channel is None:
        print(f"WARNING: Could not find channel with ID {log_channel_id}")
        return

    before_emoji, before_label = STATUS_LABELS.get(before.status, ("❓", str(before.status)))
    after_emoji, after_label = STATUS_LABELS.get(after.status, ("❓", str(after.status)))

    embed = discord.Embed(
        description=f"**{after.display_name}** changed status",
        color=_status_color(after.status),
    )
    embed.add_field(name="Before", value=f"{before_emoji} {before_label}", inline=True)
    embed.add_field(name="After", value=f"{after_emoji} {after_label}", inline=True)
    embed.set_thumbnail(url=after.display_avatar.url)
    embed.set_footer(text=f"User ID: {after.id}")

    await channel.send(embed=embed)


def _status_color(status: discord.Status) -> int:
    return {
        discord.Status.online: 0x57F287,
        discord.Status.idle: 0xFEE75C,
        discord.Status.dnd: 0xED4245,
        discord.Status.offline: 0x747F8D,
    }.get(status, 0x99AAB5)


keep_alive()
client.run(os.environ["DISCORD_BOT_TOKEN"])
