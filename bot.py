import json
import discord
import logging
import asyncio
from async_timeout import timeout
from discord.ext import commands

logging.basicConfig(level=logging.INFO)

config = json.load(open('config.json'))

_SUCCESS_GREEN = 0x28A745
_ALERT_AMBER = 0xFFBF00
def embed_success(desc, description=''):
    return discord.Embed(title=str(desc), description=description, color=_SUCCESS_GREEN)
def embed_alert(desc, description=''):
    return discord.Embed(title=str(desc), description=description, color=_ALERT_AMBER)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def _verify(channel, users):
    emails = open("emails.txt", "r").read().splitlines()
    verified = open("verified.txt").read().splitlines()

    author = users[0]
    await channel.send(f"**Bienvenid@ {author.mention}!**\n\
    **Ingresa tu e-mail para que pueda darte acceso**")

    def check(msg: discord.Message):
        return msg.author.id == author.id

    msg = await bot.wait_for('message', check=check)
    email = msg.content
    

    if email in verified:
        admin = bot.get_user(config["admin_id"])
        desc = f"**{author.mention}, este e-mail ya fue registrado. Puedes escribirle a **"
        if admin == None: desc += "server admins."
        else: desc += f"{admin.mention}"
        
        await channel.send(embed=embed_alert('', desc))
        return

    if email not in emails:
        await channel.send(embed=embed_alert('', f"**Ups, no te pudimos verificar {author.mention}!**"))
        return

    for user in users:
        role = discord.utils.get(user.guild.roles, name=config["verified_role_name"])
        if role is None:
            role = await user.guild.create_role(name=config["verified_role_name"])
        await user.add_roles(role)

    verified.append(email)
    f = open("verified.txt", "w")
    for email in verified: f.write(email + '\n')
    f.close()
    await channel.send(embed=embed_success('', f"**Genial {author.mention}! Ya tienes acceso a los canales exclusivos :)**"))

@bot.command(brief='verify user with email')
async def verify(ctx):
    users = []
    if isinstance(ctx.channel, discord.channel.DMChannel):
        for guild in bot.guilds:
            user = guild.get_member(ctx.author.id)
            if user == None: continue
            users.append(user)
    
    if ctx.guild != None:
        channel = discord.utils.get(ctx.guild.channels, name='verify')
        await ctx.message.delete()
        if channel == None or channel.id != ctx.channel.id:
            return

        users = [ctx.author]

    await _verify(ctx.channel, users)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    emoji = str(payload.emoji)
    if emoji != '✅': return
    if payload.event_type != 'REACTION_ADD': return
    if payload.message_id != config["verify_message"]: return

    guild = bot.get_guild(payload.guild_id)
    member = payload.member

    admin_role = discord.utils.get(guild.roles, name="Admin")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await guild.create_text_channel(f"verify_{member.name}", overwrites=overwrites)

    try:
        async with timeout(90):
            await _verify(channel, [member])
    except asyncio.TimeoutError:
        await channel.send(f"**La verificacion de tu cuenta no se pudo realizar, por favor intenta más tarde, {member.mention}!**")

    await channel.send("**Closing channel**")
    await asyncio.sleep(5)
    await channel.delete()

bot.run(config["token"])
