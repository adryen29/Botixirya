import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
from flask import Flask
from threading import Thread

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
COUNTING_CHANNEL_ID = 1478440739095580822
LOG_CHANNEL_ID = 1478437400496705721
GIVEAWAY_FILE = "giveaways.json"
# ==========================================

# --- Serveur Web pour éviter la mise en veille ---
app = Flask('')

@app.route('/')
def home():
    # Cette page est celle que Cron-job.org doit visiter
    return "Botixirya Status: OK - Système Anti-Mise en Veille Actif"

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Configuration du Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# --- Système de Persistence (Lecture/Écriture) ---
def save_giveaway(data):
    try:
        with open(GIVEAWAY_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Erreur sauvegarde : {e}")

def load_giveaway():
    if os.path.exists(GIVEAWAY_FILE):
        try:
            with open(GIVEAWAY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

# --- Vues et Gestion des Boutons ---
class GiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="join_gw")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id not in data or data[gw_id]['ended']:
            return await interaction.response.send_message("Ce concours est terminé.", ephemeral=True)
        if interaction.user.id in data[gw_id]['participants']:
            return await interaction.response.send_message("Tu participes déjà !", ephemeral=True)
        data[gw_id]['participants'].append(interaction.user.id)
        save_giveaway(data)
        await interaction.response.send_message("Ta participation a été enregistrée !", ephemeral=True)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.gray, custom_id="reroll_gw")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Admin uniquement.", ephemeral=True)
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id not in data or not data[gw_id]['participants']:
            return await interaction.response.send_message("Pas assez de participants.", ephemeral=True)
        winner_id = random.choice(data[gw_id]['participants'])
        await interaction.channel.send(f"🎲 **Reroll :** Le nouveau gagnant est <@{winner_id}> !")
        await interaction.response.send_message("Reroll effectué.", ephemeral=True)

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
                        await channel.send(f"Pas assez de participants pour la récompense **{gw['prize']}**.")
                    else:
                        winners = random.sample(participants, gw['winners_count'])
                        mentions = ", ".join([f"<@{w}>" for w in winners])
                        embed = message.embeds[0]
                        embed.description = f"Terminé !\nGagnant(s) : {mentions}"
                        embed.color = discord.Color.black()
                        await message.edit(embed=embed, view=None) # Retire le bouton participer
                        await channel.send(f"🎉 Félicitations {mentions} ! Vous gagnez : **{gw['prize']}** !")
                except: pass
            gw['ended'] = True
            save_giveaway(data)

# --- Événements ---
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    bot.add_view(GiveawayView(bot))
    if not check_giveaways.is_running():
        check_giveaways.start()
    print(f"Connecté en tant que {bot.user}")

@bot.event
async def on_message(message):
    global current_count, last_user_id
    if message.author == bot.user: return
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            number = int(message.content.strip())
            if number == current_count + 1 and message.author.id != last_user_id:
                current_count, last_user_id = number, message.author.id
                await message.add_reaction("✅")
            else:
                current_count, last_user_id = 0, None
                await message.add_reaction("❌")
                await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Retour à **1**.")
        except ValueError: pass
    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
async def help(ctx):
    """Affiche la liste des commandes disponibles"""
    embed = discord.Embed(title="📜 Aide du Bot Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛡️ Modération (Admin)", value=(
        f"**{COMMAND_PREFIX}lock** : Verrouille le salon.\n"
        f"**{COMMAND_PREFIX}unlock** : Déverrouille le salon.\n"
        f"**{COMMAND_PREFIX}restore** : Recrée le salon à neuf pour effacer l'historique."
    ), inline=False)
    embed.add_field(name="🎁 Giveaways (Admin)", value=(
        f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [récompense] [condition]** : Lance un concours (temps en minutes).\n"
        f"Les admins peuvent reroll via le bouton sous le message."
    ), inline=False)
    embed.add_field(name="🕹️ Divers", value=(
        f"**{COMMAND_PREFIX}ping** : Latence du bot.\n"
        f"**{COMMAND_PREFIX}score** : Score actuel du salon de comptage."
    ), inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def restore(ctx):
    new_channel = await ctx.channel.clone()
    await new_channel.edit(position=ctx.channel.position)
    await ctx.channel.delete()
    await new_channel.send("✨ Salon restauré.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, minutes: int, winners: int, prize: str, *, req: str = "Aucune"):
    end_time = time.time() + (minutes * 60)
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Récompense", value=prize, inline=False)
    embed.add_field(name="Fin", value=f"<t:{int(end_time)}:R>", inline=True)
    embed.add_field(name="Condition", value=req, inline=False)
    
    msg = await ctx.send(embed=embed, view=GiveawayView(bot))
    data = load_giveaway()
    data[str(msg.id)] = {"channel_id": ctx.channel.id, "prize": prize, "winners_count": winners, "end_time": end_time, "participants": [], "ended": False}
    save_giveaway(data)

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong ! (**{round(bot.latency * 1000)}ms**)")

@bot.command()
async def score(ctx): await ctx.send(f"Score actuel : **{current_count}**.")

# --- Lancement ---
if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token: bot.run(token)
