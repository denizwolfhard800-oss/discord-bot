import discord
import os
from keep_alive import keep_alive

LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.presences = True
intents.members = True

client = discord.Client(intents=intents)

STATUS_LABELS = {
    discord.Status.online: ("🟢", "Online"),
    discord.Status.idle: ("🟡", "Idle"),
    discord.Status.dnd: ("🔴", "Do Not Disturb"),
    discord.Status.offline: ("⚫", "Offline"),
}


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Logging presence changes to channel ID: {LOG_CHANNEL_ID}")


@client.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if before.status == after.status:
        return

    if LOG_CHANNEL_ID == 0:
        print("WARNING: LOG_CHANNEL_ID is not set. Set it as an environment variable.")
        return

    channel = client.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        print(f"WARNING: Could not find channel with ID {LOG_CHANNEL_ID}")
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
