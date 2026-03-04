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

# --- Systèmes de Sauvegarde JSON ---
def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return default
    return default

# --- Vues Interactives (Boutons Persistants) ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'identifier ✅", style=discord.ButtonStyle.success, custom_id="v_btn_p")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        v_role = interaction.guild.get_role(ROLE_VERIFIED_ID)
        un_role = interaction.guild.get_role(ROLE_UNVERIFIED_ID)
        
        try:
            if v_role in interaction.user.roles:
                return await interaction.response.send_message("Tu es déjà vérifié !", ephemeral=True)
            
            await interaction.user.add_roles(v_role)
            if un_role in interaction.user.roles:
                await interaction.user.remove_roles(un_role)
            
            await interaction.response.send_message("Vérification réussie ! Bienvenue.", ephemeral=True)
            
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                await log_chan.send(f"✅ **Vérification** : {interaction.user.mention} a réussi la vérification.")
        except:
            await interaction.response.send_message("❌ Erreur : Mes permissions sont insuffisantes.", ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="gw_btn_p")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data(GIVEAWAY_FILE, {})
        gid = str(interaction.message.id)
        
        if gid not in data or data[gid]['ended']:
            return await interaction.response.send_message("Concours terminé.", ephemeral=True)
        if interaction.user.id in data[gid]['participants']:
            return await interaction.response.send_message("Déjà inscrit !", ephemeral=True)
        
        data[gid]['participants'].append(interaction.user.id)
        save_data(GIVEAWAY_FILE, data)
        await interaction.response.send_message("Inscription validée !", ephemeral=True)

# --- Boucle Automatique Giveaways ---
@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_data(GIVEAWAY_FILE, {})
    now = time.time()
    for mid, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            chan = bot.get_channel(gw['channel_id'])
            if chan:
                try:
                    msg = await chan.fetch_message(int(mid))
                    pts = gw['participants']
                    if len(pts) < gw['winners_count']:
                        await chan.send(f"⚠️ Pas assez de monde pour **{gw['prize']}**.")
                    else:
                        winners = random.sample(pts, gw['winners_count'])
                        mentions = ", ".join([f"<@{w}>" for w in winners])
                        await chan.send(f"🎊 Félicitations {mentions} ! Tu gagnes : **{gw['prize']}** !")
                except: pass
            gw['ended'] = True
            save_data(GIVEAWAY_FILE, data)

# --- Événements ---
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    global current_count, last_user_id
    bot.add_view(VerifyView())
    bot.add_view(GiveawayView())
    
    counting_data = load_data(COUNTING_FILE, {"count": 0, "last_user_id": None})
    current_count = counting_data["count"]
    last_user_id = counting_data["last_user_id"]
    
    if not check_giveaways.is_running():
        check_giveaways.start()
    print(f"✅ Connecté : {bot.user} | Score : {current_count}")

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
                save_data(COUNTING_FILE, {"count": current_count, "last_user_id": last_user_id})
                await message.add_reaction("✅")
            elif val == current_count:
                pass
            else:
                current_count, last_user_id = 0, None
                save_data(COUNTING_FILE, {"count": 0, "last_user_id": None})
                await message.add_reaction("❌")
                await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Retour à 1.")
        except ValueError: pass

    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """Installe le système de vérification par bouton"""
    chan = bot.get_channel(VERIFY_CHANNEL_ID)
    if chan:
        embed = discord.Embed(title="🛡️ Vérification", description="Clique ci-dessous pour accéder au serveur.", color=discord.Color.blue())
        await chan.send(embed=embed, view=VerifyView())
        await ctx.send("✅ Système envoyé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, *, args):
    """Lance un concours : [min] [gagnants] [prix] [condition]"""
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 4: return await ctx.send("Usage: [min] [gagnants] [prix] [cond]")
    
    mins, wins, prize, cond = int(m[0]), int(m[1]), m[2], m[3]
    end = time.time() + (mins * 60)
    
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Prix", value=prize, inline=False)
    embed.add_field(name="Fin", value=f"<t:{int(end)}:R>", inline=True)
    
    msg = await ctx.send(embed=embed, view=GiveawayView())
    data = load_data(GIVEAWAY_FILE, {})
    data[str(msg.id)] = {"channel_id": ctx.channel.id, "prize": prize, "winners_count": wins, "end_time": end, "participants": [], "ended": False}
    save_data(GIVEAWAY_FILE, data)

@bot.command()
async def score(ctx):
    """Affiche le score actuel du comptage"""
    await ctx.send(f"🔢 Le score actuel est : **{current_count}**")

@bot.command()
async def help(ctx):
    """Affiche l'aide du bot"""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛡️ Admin", value=f"`{COMMAND_PREFIX}setup_verify`, `{COMMAND_PREFIX}giveaway`", inline=False)
    embed.add_field(name="🕹️ Divers", value=f"`{COMMAND_PREFIX}score`, `{COMMAND_PREFIX}ping`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Affiche la latence du bot"""
    await ctx.send(f"🏓 Pong ! `{round(bot.latency * 1000)}ms` ")

# --- Lancement ---
token = os.getenv('DISCORD_TOKEN')
if token: bot.run(token)
