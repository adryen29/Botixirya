import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
import re
import sys
from flask import Flask
from threading import Thread

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
LOG_CHANNEL_ID = 1478437400496705721
DB_CHANNEL_ID = 1479105188454338611  # Salon Discord servant de base de données
VERIFY_CHANNEL_ID = 1478658827682582662
ROLE_UNVERIFIED_ID = 1478658867415089263
ROLE_VERIFIED_ID = 1477170552950231164
GIVEAWAY_FILE = "giveaways.json"
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Botixirya Status: OK"

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# --- Gestion des données Giveaway ---
def save_giveaway(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_giveaway():
    if os.path.exists(GIVEAWAY_FILE):
        try:
            with open(GIVEAWAY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

# --- Sauvegarde du comptage dans le salon DB ---
async def save_counting_to_db():
    """Envoie une sauvegarde du comptage dans le salon DB Discord."""
    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        await db_chan.send(
            f"BACKUP_COUNT|{current_count}|{last_user_id}|{active_counting_channel}"
        )

async def send_log(content):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(content)

# --- Système de Vérification ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'identifier ✅", style=discord.ButtonStyle.success, custom_id="verify_user")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        verified_role = interaction.guild.get_role(ROLE_VERIFIED_ID)
        unverified_role = interaction.guild.get_role(ROLE_UNVERIFIED_ID)
        if verified_role in interaction.user.roles:
            return await interaction.response.send_message("Tu es déjà vérifié !", ephemeral=True)
        try:
            await interaction.user.add_roles(verified_role)
            if unverified_role in interaction.user.roles:
                await interaction.user.remove_roles(unverified_role)
            await interaction.response.send_message("Vérification réussie !", ephemeral=True)
            await send_log(f"✅ **Vérification** : {interaction.user.mention}")
        except:
            await interaction.response.send_message("Erreur de rôle.", ephemeral=True)

# --- Interface Giveaway ---
class GiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="join_gw")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id not in data or data[gw_id]['ended']:
            return await interaction.response.send_message("Terminé.", ephemeral=True)
        if interaction.user.id in data[gw_id]['participants']:
            return await interaction.response.send_message("Déjà inscrit !", ephemeral=True)
        data[gw_id]['participants'].append(interaction.user.id)
        save_giveaway(data)
        await interaction.response.send_message("Inscrit !", ephemeral=True)

    @discord.ui.button(label="Reroll 🎲", style=discord.ButtonStyle.gray, custom_id="reroll_gw")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id in data and data[gw_id]['participants']:
            winner = random.choice(data[gw_id]['participants'])
            await interaction.channel.send(f"🎲 Nouveau gagnant : <@{winner}>")
            await interaction.response.send_message("Fait.", ephemeral=True)

    @discord.ui.button(label="Annuler ❌", style=discord.ButtonStyle.danger, custom_id="delete_gw")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return
        await interaction.message.delete()

@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_giveaway()
    now = time.time()
    for msg_id, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            gw['ended'] = True
            save_giveaway(data)

# --- Événements ---
current_count = 0
last_user_id = None
active_counting_channel = 0

@bot.event
async def on_ready():
    global current_count, last_user_id, active_counting_channel
    bot.add_view(GiveawayView(bot))
    bot.add_view(VerifyView())

    # Restauration depuis le salon DB Discord (seule source de vérité)
    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        async for message in db_chan.history(limit=50):
            if "BACKUP_COUNT|" in message.content:
                parts = message.content.split("|")
                current_count = int(parts[1])
                last_user_id = int(parts[2]) if parts[2] != "None" else None
                active_counting_channel = int(parts[3])
                break

    if not check_giveaways.is_running():
        check_giveaways.start()

    await send_log(f"✅ **Botixirya** prêt. Score actuel : `{current_count}`")

@bot.event
async def on_message(message):
    global current_count, last_user_id, active_counting_channel
    if message.author == bot.user:
        return

    if message.channel.id == active_counting_channel:
        content = message.content.strip()
        if content.isdigit():
            number = int(content)
            if number == current_count + 1 and message.author.id != last_user_id:
                current_count = number
                last_user_id = message.author.id
                await save_counting_to_db()
                await message.add_reaction("✅")
            elif number <= current_count:
                return
            else:
                current_count = 0
                last_user_id = None
                await save_counting_to_db()
                await message.add_reaction("❌")
                await message.channel.send("⚠️ Suite cassée ! Retour à 1.")

    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
async def help(ctx):
    """Affiche la liste des commandes disponibles."""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛡️ Système", value=(
        f"**{COMMAND_PREFIX}kill** : Sauvegarde les données dans le salon DB et s'éteint.\n"
        f"**{COMMAND_PREFIX}ping** : Affiche la latence du bot.\n"
        f"**{COMMAND_PREFIX}score** : Affiche le score actuel."
    ), inline=False)
    embed.add_field(name="⚙️ Admin", value=(
        f"**{COMMAND_PREFIX}setcountchannel** : Définit le salon de comptage actuel.\n"
        f"**{COMMAND_PREFIX}setscore [nb]** : Modifie manuellement le score.\n"
        f"**{COMMAND_PREFIX}lock / unlock** : Verrouille ou déverrouille le salon.\n"
        f"**{COMMAND_PREFIX}restore** : Recrée le salon actuel."
    ), inline=False)
    embed.add_field(name="🎁 Giveaway", value=f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [condition]**", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def kill(ctx):
    """Envoie une sauvegarde dans le salon DB et ferme le bot."""
    await save_counting_to_db()
    await ctx.send("💀 Données sauvegardées dans le salon DB. Extinction...")
    await asyncio.sleep(2)
    await bot.close()
    sys.exit()

@bot.command()
@commands.has_permissions(administrator=True)
async def setcountchannel(ctx):
    """Définit ce salon pour le comptage."""
    global active_counting_channel
    active_counting_channel = ctx.channel.id
    await save_counting_to_db()
    await ctx.send("✅ Salon de comptage défini.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setscore(ctx, number: int):
    """Définit le score manuellement."""
    global current_count, last_user_id
    current_count = number
    last_user_id = None
    await save_counting_to_db()
    await ctx.send(f"✅ Score fixé à {number}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def lock(ctx):
    """Verrouille l'envoi de messages dans le salon."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    """Déverrouille l'envoi de messages dans le salon."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def restore(ctx):
    """Clone et supprime le salon actuel."""
    new = await ctx.channel.clone()
    await ctx.channel.delete()
    await new.send("✨ Salon restauré.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, *, args):
    """Lance un giveaway. Format : [min] [gagnants] [prix] [condition]"""
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 4:
        return
    end = time.time() + (int(m[0]) * 60)
    embed = discord.Embed(title="🎉 GIVEAWAY", color=discord.Color.gold())
    embed.add_field(name="Prix", value=m[2])
    msg = await ctx.send(embed=embed, view=GiveawayView(bot))
    data = load_giveaway()
    data[str(msg.id)] = {
        "channel_id": ctx.channel.id,
        "prize": m[2],
        "winners_count": int(m[1]),
        "end_time": end,
        "participants": [],
        "ended": False
    }
    save_giveaway(data)

@bot.command()
async def ping(ctx):
    """Affiche la latence."""
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def score(ctx):
    """Affiche le score actuel."""
    await ctx.send(f"Score actuel : **{current_count}**")

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
