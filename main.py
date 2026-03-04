import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
import re
from flask import Flask
from threading import Thread

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

# --- Serveur Web pour Koyeb/Cron-job ---
app = Flask('')
@app.route('/')
def home(): return "Botixirya Online"
def run_f(): app.run(host='0.0.0.0', port=8000)
def keep_alive():
    t = Thread(target=run_f)
    t.daemon = True
    t.start()

# --- Configuration Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# --- Gestion des Données ---
def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f)

def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return json.load(f)
        except: return default
    return default

# --- Vues Persistantes ---
class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="S'identifier ✅", style=discord.ButtonStyle.success, custom_id="v_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        v_role = interaction.guild.get_role(ROLE_VERIFIED_ID)
        un_role = interaction.guild.get_role(ROLE_UNVERIFIED_ID)
        try:
            await interaction.user.add_roles(v_role)
            if un_role in interaction.user.roles: await interaction.user.remove_roles(un_role)
            await interaction.response.send_message("Vérifié !", ephemeral=True)
        except: await interaction.response.send_message("Erreur permissions.", ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="gw_btn")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data(GIVEAWAY_FILE, {})
        gid = str(interaction.message.id)
        if gid not in data or data[gid]['ended']: return await interaction.response.send_message("Fini.", ephemeral=True)
        if interaction.user.id in data[gid]['participants']: return await interaction.response.send_message("Déjà inscrit.", ephemeral=True)
        data[gid]['participants'].append(interaction.user.id)
        save_data(GIVEAWAY_FILE, data)
        await interaction.response.send_message("Inscrit !", ephemeral=True)

# --- Boucles et Events ---
current_count = 0
last_user_id = None

@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_data(GIVEAWAY_FILE, {})
    now = time.time()
    for mid, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            chan = bot.get_channel(gw['channel_id'])
            if chan:
                pts = gw['participants']
                if len(pts) >= gw['winners_count']:
                    winners = random.sample(pts, gw['winners_count'])
                    mentions = ", ".join([f"<@{w}>" for w in winners])
                    await chan.send(f"🎊 Bravo {mentions} ! Cadeau : **{gw['prize']}** !")
            gw['ended'] = True
            save_data(GIVEAWAY_FILE, data)

@bot.event
async def on_ready():
    global current_count, last_user_id
    bot.add_view(VerifyView()); bot.add_view(GiveawayView())
    c_data = load_data(COUNTING_FILE, {"count": 0, "last_user_id": None})
    current_count = c_data["count"]; last_user_id = c_data["last_user_id"]
    if not check_giveaways.is_running(): check_giveaways.start()
    print(f"✅ Prêt ! Score : {current_count}")

@bot.event
async def on_message(message):
    global current_count, last_user_id
    if message.author.bot: return

    # LOGIQUE DE COMPTAGE
    if message.channel.id == COUNTING_CHANNEL_ID:
        content = message.content.strip()
        if content.isdigit():
            val = int(content)
            if val == current_count + 1 and message.author.id != last_user_id:
                current_count = val
                last_user_id = message.author.id
                save_data(COUNTING_FILE, {"count": current_count, "last_user_id": last_user_id})
                await message.add_reaction("✅")
            else:
                if val != current_count: # On ignore si c'est une répétition du même chiffre
                    current_count = 0
                    last_user_id = None
                    save_data(COUNTING_FILE, {"count": 0, "last_user_id": None})
                    await message.add_reaction("❌")
                    await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Retour à 1.")

    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
async def help(ctx):
    """Affiche l'aide complète et pertinente"""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    
    embed.add_field(name="🛡️ Modération (Admin)", value=(
        f"`{COMMAND_PREFIX}lock` : Verrouille le salon actuel.\n"
        f"`{COMMAND_PREFIX}unlock` : Déverrouille le salon.\n"
        f"`{COMMAND_PREFIX}restore` : Supprime les messages récents (Nettoyage).\n"
        f"`{COMMAND_PREFIX}setup_verify` : Installe le bouton de vérification."
    ), inline=False)
    
    embed.add_field(name="🎁 Giveaways (Admin)", value=(
        f"`{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [cond]`\n"
        "Lance un concours avec boutons **Participer**."
    ), inline=False)
    
    embed.add_field(name="🕹️ Divers", value=(
        f"`{COMMAND_PREFIX}ping` : Affiche la latence du bot.\n"
        f"`{COMMAND_PREFIX}score` : Affiche le score actuel du comptage."
    ), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Verrouille le salon"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Déverrouille le salon"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def restore(ctx, amount: int = 10):
    """Nettoie le salon"""
    await ctx.channel.purge(limit=amount + 1)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """Envoie le message de vérification"""
    chan = bot.get_channel(VERIFY_CHANNEL_ID)
    if chan:
        embed = discord.Embed(title="🛡️ Vérification", description="Clique ci-dessous pour accéder au serveur.", color=discord.Color.green())
        await chan.send(embed=embed, view=VerifyView())
        await ctx.send("✅ Système de vérification installé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, *, args):
    """Format : [min] [gagnants] [prix] [condition]"""
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 4: return await ctx.send("Format: [min] [gagnants] [prix] [cond]")
    mins, wins, prize, cond = int(m[0]), int(m[1]), m[2], m[3]
    end = time.time() + (mins * 60)
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Récompense", value=prize, inline=False)
    embed.add_field(name="Fin", value=f"<t:{int(end)}:R>", inline=True)
    msg = await ctx.send(embed=embed, view=GiveawayView())
    data = load_data(GIVEAWAY_FILE, {})
    data[str(msg.id)] = {"channel_id": ctx.channel.id, "prize": prize, "winners_count": wins, "end_time": end, "participants": [], "ended": False}
    save_data(GIVEAWAY_FILE, data)

@bot.command()
async def score(ctx): await ctx.send(f"🔢 Score actuel : **{current_count}**")

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 `{round(bot.latency * 1000)}ms` ")

# --- Démarrage ---
if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token: bot.run(token)
