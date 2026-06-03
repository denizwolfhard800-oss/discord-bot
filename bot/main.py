import discord
from discord import app_commands
import os
from datetime import datetime, timezone
from keep_alive import keep_alive
from config import get_log_channel_id, set_log_channel_id
from history import append_entry, get_entries, get_stats

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


@tree.command(name="presencelog", description="Show recent presence changes for a member.")
@app_commands.describe(member="The member to look up", entries="Number of entries to show (default 10, max 25)")
@app_commands.default_permissions(administrator=True)
async def presencelog(interaction: discord.Interaction, member: discord.Member, entries: int = 10):
    entries = max(1, min(entries, 25))
    history = get_entries(member.id, limit=entries)

    embed = discord.Embed(
        title=f"Presence History — {member.display_name}",
        color=_status_color(member.status),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    if not history:
        embed.description = "No presence changes recorded yet for this member."
    else:
        lines = []
        for entry in history:
            before_emoji = STATUS_LABELS.get(discord.Status(entry["before"]), ("❓", entry["before"]))[0]
            after_emoji = STATUS_LABELS.get(discord.Status(entry["after"]), ("❓", entry["after"]))[0]
            ts = datetime.fromisoformat(entry["timestamp"])
            discord_ts = f"<t:{int(ts.timestamp())}:R>"
            lines.append(f"{before_emoji} → {after_emoji} {discord_ts}")
        embed.description = "\n".join(lines)

    embed.set_footer(text=f"Showing up to {entries} most recent • User ID: {member.id}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="presencestats", description="Show a breakdown of time spent in each status for a member.")
@app_commands.describe(member="The member to analyse")
@app_commands.default_permissions(administrator=True)
async def presencestats(interaction: discord.Interaction, member: discord.Member):
    stats = get_stats(member.id)

    if stats.get("total_entries", 0) == 0:
        await interaction.response.send_message(
            f"No presence history recorded for **{member.display_name}** yet.",
            ephemeral=True,
        )
        return

    total_seconds = sum(stats[s] for s in ("online", "idle", "dnd", "offline"))

    def fmt(seconds: float) -> str:
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def pct(seconds: float) -> str:
        if total_seconds == 0:
            return "0%"
        return f"{seconds / total_seconds * 100:.1f}%"

    def bar(seconds: float, width: int = 12) -> str:
        filled = round((seconds / total_seconds) * width) if total_seconds else 0
        return "█" * filled + "░" * (width - filled)

    embed = discord.Embed(
        title=f"Presence Stats — {member.display_name}",
        color=_status_color(member.status),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    for status_key, (emoji, label) in [
        ("online",  STATUS_LABELS[discord.Status.online]),
        ("idle",    STATUS_LABELS[discord.Status.idle]),
        ("dnd",     STATUS_LABELS[discord.Status.dnd]),
        ("offline", STATUS_LABELS[discord.Status.offline]),
    ]:
        secs = stats[status_key]
        embed.add_field(
            name=f"{emoji} {label}",
            value=f"`{bar(secs)}` {pct(secs)}\n{fmt(secs)}",
            inline=True,
        )

    first_seen = datetime.fromisoformat(stats["first_seen"])
    embed.add_field(name="Total tracked", value=fmt(total_seconds), inline=True)
    embed.add_field(name="Changes logged", value=str(stats["total_entries"]), inline=True)
    embed.set_footer(text=f"Tracking since {first_seen.strftime('%Y-%m-%d %H:%M UTC')} • User ID: {member.id}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="statuslist", description="Show the current status of every member in the server.")
@app_commands.default_permissions(administrator=True)
async def statuslist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    buckets: dict[discord.Status, list[str]] = {
        discord.Status.online: [],
        discord.Status.idle: [],
        discord.Status.dnd: [],
        discord.Status.offline: [],
    }

    for member in interaction.guild.members:
        if member.bot:
            continue
        bucket = buckets.get(member.status)
        if bucket is not None:
            bucket.append(member.display_name)
        else:
            buckets.setdefault(member.status, []).append(member.display_name)

    total = sum(len(v) for v in buckets.values())

    embed = discord.Embed(
        title="Member Status Overview",
        description=f"{total} members total",
        color=0x5865F2,
    )

    order = [discord.Status.online, discord.Status.idle, discord.Status.dnd, discord.Status.offline]
    for status in order:
        emoji, label = STATUS_LABELS[status]
        members = buckets.get(status, [])
        if members:
            names = "\n".join(members[:30])
            if len(members) > 30:
                names += f"\n… and {len(members) - 30} more"
            embed.add_field(name=f"{emoji} {label} ({len(members)})", value=names, inline=True)
        else:
            embed.add_field(name=f"{emoji} {label} (0)", value="—", inline=True)

    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="statuscheck", description="Check the current presence status of a member.")
@app_commands.describe(member="The member to check")
@app_commands.default_permissions(administrator=True)
async def statuscheck(interaction: discord.Interaction, member: discord.Member):
    emoji, label = STATUS_LABELS.get(member.status, ("❓", str(member.status)))

    embed = discord.Embed(
        description=f"Current status for **{member.display_name}**",
        color=_status_color(member.status),
    )
    embed.add_field(name="Status", value=f"{emoji} {label}", inline=True)

    activities = [a for a in member.activities if not isinstance(a, discord.CustomActivity)]
    custom = next((a for a in member.activities if isinstance(a, discord.CustomActivity)), None)

    if custom and custom.name:
        embed.add_field(name="Custom Status", value=str(custom.name), inline=True)

    if activities:
        activity_lines = []
        for a in activities:
            if isinstance(a, discord.Spotify):
                activity_lines.append(f"🎵 Listening to **{a.title}** by {a.artist}")
            elif isinstance(a, discord.Game):
                activity_lines.append(f"🎮 Playing **{a.name}**")
            elif isinstance(a, discord.Streaming):
                activity_lines.append(f"📡 Streaming **{a.name}**")
            elif isinstance(a, discord.Activity):
                activity_lines.append(f"▶️ {a.type.name.capitalize()} **{a.name}**")
        if activity_lines:
            embed.add_field(name="Activity", value="\n".join(activity_lines), inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"User ID: {member.id}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


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

    append_entry(
        member_id=after.id,
        member_name=after.display_name,
        before=str(before.status),
        after=str(after.status),
    )

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
