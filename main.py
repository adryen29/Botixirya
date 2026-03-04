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
COUNTING_CHANNEL_ID = 1478829146799997240
LOG_CHANNEL_ID = 1478437400496705721
VERIFY_CHANNEL_ID = 1478658827682582662
ROLE_UNVERIFIED_ID = 1478658867415089263
ROLE_VERIFIED_ID = 1477170552950231164
GIVEAWAY_FILE = "giveaways.json"
COUNTING_FILE = "counting.json"
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Botixirya Status: OK - Système Anti-Mise en Veille Actif"

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

# --- Gestion des données ---
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

async def send_log(content):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(content)

# --- Système de Vérification (Bouton) ---
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
            
            await interaction.response.send_message("Vérification réussie ! Bienvenue.", ephemeral=True)
            await send_log(f"✅ **Vérification** : {interaction.user.mention} a passé la vérification.")
        except:
            await interaction.response.send_message("Erreur : Vérifiez la hiérarchie de mes rôles.", ephemeral=True)

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
            return await interaction.response.send_message("Ce concours est terminé.", ephemeral=True)
        if interaction.user.id in data[gw_id]['participants']:
            return await interaction.response.send_message("Tu participes déjà !", ephemeral=True)
        
        data[gw_id]['participants'].append(interaction.user.id)
        save_giveaway(data)
        await interaction.response.send_message("Ta participation a été enregistrée !", ephemeral=True)

    @discord.ui.button(label="Reroll 🎲", style=discord.ButtonStyle.gray, custom_id="reroll_gw")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Admin uniquement.", ephemeral=True)
        
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id not in data or not data[gw_id]['participants']:
            return await interaction.response.send_message("Pas assez de participants.", ephemeral=True)
        
        winner_id = random.choice(data[gw_id]['participants'])
        await interaction.channel.send(f"🎲 **Reroll :** Le nouveau gagnant est <@{winner_id}> !")
        await send_log(f"🎲 **Reroll** : {interaction.user.mention} a relancé le tirage du giveaway `{gw_id}`.")
        await interaction.response.send_message("Reroll effectué.", ephemeral=True)

    @discord.ui.button(label="Annuler ❌", style=discord.ButtonStyle.danger, custom_id="delete_gw")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Admin uniquement.", ephemeral=True)
        
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        if gw_id in data:
            del data[gw_id]
            save_giveaway(data)
        
        await interaction.message.delete()
        await send_log(f"🗑️ **Suppression** : {interaction.user.mention} a annulé le giveaway `{gw_id}`.")

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
                        await channel.send(f"Fin : Pas assez de participants pour **{gw['prize']}**.")
                        await send_log(f"📉 **Giveaway Terminé** : `{msg_id}` fini sans assez de participants.")
                    else:
                        winners = random.sample(participants, gw['winners_count'])
                        mentions = ", ".join([f"<@{w}>" for w in winners])
                        embed = message.embeds[0]
                        embed.description = f"Terminé !\nGagnant(s) : {mentions}"
                        embed.color = discord.Color.black()
                        await message.edit(embed=embed, view=None)
                        await channel.send(f"🎉 Félicitations {mentions} ! Vous gagnez : **{gw['prize']}** !")
                        await send_log(f"🏆 **Giveaway Terminé** : Gagnant(s) {mentions} pour **{gw['prize']}**.")
                except: pass
            gw['ended'] = True
            save_giveaway(data)

# --- Événements ---
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    global current_count, last_user_id
    bot.add_view(GiveawayView(bot))
    bot.add_view(VerifyView())
    
    current_count, last_user_id = load_counting()
    
    if not check_giveaways.is_running():
        check_giveaways.start()
    await send_log(f"✅ **Botixirya** en ligne. Score de comptage restauré : `{current_count}`.")
    print(f"Connecté : {bot.user} | Score : {current_count}")

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(ROLE_UNVERIFIED_ID)
    if role:
        try:
            await member.add_roles(role)
            await send_log(f"👤 **Auto-role** : {member.mention} a reçu le rôle `{role.name}`.")
        except: pass

@bot.event
async def on_message(message):
    global current_count, last_user_id
    if message.author == bot.user: return
    
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            content = message.content.strip()
            if content.isdigit():
                number = int(content)
                # On vérifie si c'est le bon nombre ET que ce n'est pas le même utilisateur
                if number == current_count + 1 and message.author.id != last_user_id:
                    current_count, last_user_id = number, message.author.id
                    save_counting(current_count, last_user_id) 
                    await message.add_reaction("✅")
                elif number == current_count:
                    # On ignore si l'utilisateur répète le même chiffre par erreur
                    return
                else:
                    # Mauvais chiffre : Réinitialisation
                    current_count, last_user_id = 0, None
                    save_counting(0, None) 
                    await message.add_reaction("❌")
                    await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Retour à **1**.")
        except ValueError: pass
        
    await bot.process_commands(message)

# --- Commandes ---

@bot.command()
async def help(ctx):
    """Affiche les commandes avec leur description pertinente"""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛡️ Modération (Admin)", value=(
        f"**{COMMAND_PREFIX}lock** : Verrouille le salon.\n"
        f"**{COMMAND_PREFIX}unlock** : Déverrouille le salon.\n"
        f"**{COMMAND_PREFIX}restore** : Nettoie le salon actuel (Clone et Supprime).\n"
        f"**{COMMAND_PREFIX}setup_verify** : Installe le bouton de vérification."
    ), inline=False)
    embed.add_field(name="🎁 Giveaways (Admin)", value=(
        f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [récompense] [condition]**\n"
        f"Lance un concours avec boutons **Participer**, **Reroll** et **Annuler**."
    ), inline=False)
    embed.add_field(name="🕹️ Divers", value=(
        f"**{COMMAND_PREFIX}ping** : Latence du bot.\n"
        f"**{COMMAND_PREFIX}score** : Score actuel du comptage (sauvegardé)."
    ), inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if not channel: return await ctx.send("Salon de vérification introuvable.")
    embed = discord.Embed(
        title="🛡️ Vérification Sécurisée",
        description="Clique sur le bouton ci-dessous pour accéder au serveur.",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=VerifyView())
    await ctx.send("✅ Système de vérification installé.")

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
async def giveaway(ctx, *, args):
    matches = re.findall(r'\[(.*?)\]', args)
    if len(matches) < 4:
        return await ctx.send(f"❌ Format : `{COMMAND_PREFIX}giveaway [minutes] [gagnants] [récompense] [condition]`")
    try:
        minutes, winners = int(matches[0]), int(matches[1])
        prize, req = matches[2], matches[3]
    except ValueError:
        return await ctx.send("❌ Erreur : Minutes et gagnants doivent être des chiffres.")

    end_time = time.time() + (minutes * 60)
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Récompense", value=prize, inline=False)
    embed.add_field(name="Fin", value=f"<t:{int(end_time)}:R>", inline=True)
    embed.add_field(name="Gagnants", value=str(winners), inline=True)
    embed.add_field(name="Condition", value=req, inline=False)
    embed.set_footer(text=f"Lancé par {ctx.author.display_name}")
    
    msg = await ctx.send(embed=embed, view=GiveawayView(bot))
    data = load_giveaway()
    data[str(msg.id)] = {"channel_id": ctx.channel.id, "prize": prize, "winners_count": winners, "end_time": end_time, "participants": [], "ended": False}
    save_giveaway(data)
    await send_log(f"🎁 **Nouveau Giveaway** lancé par {ctx.author.mention}")

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Pong ! (**{round(bot.latency * 1000)}ms**)")

@bot.command()
async def score(ctx): await ctx.send(f"Le score actuel sauvegardé est **{current_count}**.")

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token: bot.run(token)
