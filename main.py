import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
import re

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
COUNTING_CHANNEL_ID = 1478440739095580822
LOG_CHANNEL_ID = 1478437400496705721
VERIFY_CHANNEL_ID = 1478658827682582662
ROLE_UNVERIFIED_ID = 1478658867415089263
ROLE_VERIFIED_ID = 1477170552950231164
GIVEAWAY_FILE = "giveaways.json"
COUNTING_FILE = "counting.json"
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# --- Fonctions de Sauvegarde ---
def save_counting(count, last_user):
    with open(COUNTING_FILE, "w") as f:
        json.dump({"count": count, "last_user_id": last_user}, f)

def load_counting():
    if os.path.exists(COUNTING_FILE):
        try:
            with open(COUNTING_FILE, "r") as f:
                data = json.load(f)
                return data.get("count", 0), data.get("last_user_id", None)
        except: return 0, None
    return 0, None

def save_giveaway(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f)

def load_giveaway():
    if os.path.exists(GIVEAWAY_FILE):
        try:
            with open(GIVEAWAY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

# --- Système de Vérification (Bouton) ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'identifier ✅", style=discord.ButtonStyle.success, custom_id="v_button_persistent")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        verified_role = interaction.guild.get_role(ROLE_VERIFIED_ID)
        unverified_role = interaction.guild.get_role(ROLE_UNVERIFIED_ID)
        
        try:
            await interaction.user.add_roles(verified_role)
            if unverified_role in interaction.user.roles:
                await interaction.user.remove_roles(unverified_role)
            await interaction.response.send_message("Vérification réussie ! Accès accordé.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erreur de permissions (Rôle du bot trop bas).", ephemeral=True)

# --- Système de Giveaway (Boutons) ---
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="gw_join_persistent")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id not in data or data[gw_id]['ended']:
            return await interaction.response.send_message("Ce concours est terminé.", ephemeral=True)
        if interaction.user.id in data[gw_id]['participants']:
            return await interaction.response.send_message("Tu es déjà inscrit !", ephemeral=True)
        
        data[gw_id]['participants'].append(interaction.user.id)
        save_giveaway(data)
        await interaction.response.send_message("Participation validée ! Bonne chance.", ephemeral=True)

# --- Boucle de gestion des Giveaways ---
@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_giveaway()
    now = time.time()
    for msg_id, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            channel = bot.get_channel(gw['channel_id'])
            if channel:
                try:
                    message = await channel.fetch_message(int(msg_id))
                    participants = gw['participants']
                    if len(participants) < gw['winners_count']:
                        await channel.send(f"⚠️ Pas assez de participants pour **{gw['prize']}**.")
                    else:
                        winners = random.sample(participants, gw['winners_count'])
                        mentions = ", ".join([f"<@{w}>" for w in winners])
                        await channel.send(f"🎊 Félicitations {mentions} ! Vous gagnez : **{gw['prize']}** !")
                except: pass
            gw['ended'] = True
            save_giveaway(data)

# --- Événements ---
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    global current_count, last_user_id
    bot.add_view(VerifyView())
    bot.add_view(GiveawayView())
    current_count, last_user_id = load_counting()
    if not check_giveaways.is_running():
        check_giveaways.start()
    print(f"✅ Botixirya en ligne | Score actuel : {current_count}")

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(ROLE_UNVERIFIED_ID)
    if role:
        try: await member.add_roles(role)
        except: pass

@bot.event
async def on_message(message):
    global current_count, last_user_id
    if message.author.bot: return

    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            val = int(message.content.strip())
            if val == current_count + 1 and message.author.id != last_user_id:
                current_count, last_user_id = val, message.author.id
                save_counting(current_count, last_user_id)
                await message.add_reaction("✅")
            elif val == current_count:
                pass
            else:
                current_count, last_user_id = 0, None
                save_counting(0, None)
                await message.add_reaction("❌")
                await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Le score retombe à **1**.")
        except ValueError: pass

    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """Installe le message de vérification avec bouton"""
    chan = bot.get_channel(VERIFY_CHANNEL_ID)
    if chan:
        embed = discord.Embed(title="🛡️ Vérification", description="Clique ci-dessous pour accéder au serveur.", color=discord.Color.blue())
        await chan.send(embed=embed, view=VerifyView())
        await ctx.send("✅ Système de vérification déployé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, *, args):
    """Lance un giveaway : [min] [gagnants] [prix] [condition]"""
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 4: return await ctx.send(f"Usage: `{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [condition]`")
    mins, wins, prize, cond = int(m[0]), int(m[1]), m[2], m[3]
    end = time.time() + (mins * 60)
    embed = discord.Embed(title="🎉 NOUVEAU GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Prix", value=prize, inline=False)
    embed.add_field(name="Fin", value=f"<t:{int(end)}:R>", inline=True)
    msg = await ctx.send(embed=embed, view=GiveawayView())
    data = load_giveaway()
    data[str(msg.id)] = {"channel_id": ctx.channel.id, "prize": prize, "winners_count": wins, "end_time": end, "participants": [], "ended": False}
    save_giveaway(data)

@bot.command()
async def score(ctx):
    """Affiche le score actuel de la suite de nombres"""
    await ctx.send(f"🔢 Le score actuel est de **{current_count}**.")

@bot.command()
async def help(ctx):
    """Affiche toutes les commandes et leur utilité"""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛠️ Admin", value=f"`{COMMAND_PREFIX}setup_verify`, `{COMMAND_PREFIX}giveaway`", inline=False)
    embed.add_field(name="🎮 Général", value=f"`{COMMAND_PREFIX}score`, `{COMMAND_PREFIX}ping`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Mesure la latence du bot"""
    await ctx.send(f"🏓 Pong ! `{round(bot.latency * 1000)}ms` ")

token = os.getenv('DISCORD_TOKEN')
if token: bot.run(token)
