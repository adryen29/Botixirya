import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
COUNTING_CHANNEL_ID = 1478440739095580822
LOG_CHANNEL_ID = 1478437400496705721
# ==========================================

# 1. Configuration du mini serveur Web pour Koyeb
app = Flask('')

@app.route('/')
def home():
    return "Botixirya est en vie !"

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Configuration du Bot Discord
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Variables globales pour le comptage
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"✅ **{bot.user.name}** est en ligne. Préfixe : `{COMMAND_PREFIX}`")

@bot.event
async def on_message(message):
    global current_count, last_user_id
    if message.author == bot.user:
        return

    # Logique du jeu de comptage
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            number = int(message.content.strip())
            if number == current_count + 1 and message.author.id != last_user_id:
                current_count = number
                last_user_id = message.author.id
                await message.add_reaction("✅")
            else:
                current_count = 0
                last_user_id = None
                await message.add_reaction("❌")
                await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! Le prochain nombre est **1**.")
        except ValueError:
            pass

    await bot.process_commands(message)

# 3. Gestionnaire d'erreurs (Logs Discord)
@bot.event
async def on_command_error(ctx, error):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="❌ Erreur de Commande", color=discord.Color.red())
        embed.add_field(name="Commande", value=ctx.message.content)
        embed.add_field(name="Erreur", value=f"```py\n{error}\n```")
        await channel.send(embed=embed)
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Tu n'as pas la permission d'utiliser cette commande.")

# 4. Commandes de Modération (Lock/Unlock/Restore)

@bot.command()
@commands.has_permissions(administrator=True)
async def lock(ctx):
    """Verrouille le salon pour tout le monde sauf les admins"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Ce salon a été verrouillé par {ctx.author.mention}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    """Déverrouille le salon"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Ce salon est de nouveau ouvert.")

@bot.command()
@commands.has_permissions(administrator=True)
async def restore(ctx):
    """Clone le salon actuel et supprime l'ancien pour nettoyer le chat"""
    await ctx.send("🔄 Restauration du salon en cours...")
    
    # Cloner le salon (garde les permissions, la catégorie, etc.)
    new_channel = await ctx.channel.clone(reason="Commande restore utilisée")
    
    # Placer le nouveau salon au même endroit que l'ancien
    await new_channel.edit(position=ctx.channel.position)
    
    # Supprimer l'ancien salon
    await ctx.channel.delete(reason="Restauration du salon")
    
    # Envoyer un message dans le nouveau salon
    await new_channel.send(f"✨ Salon restauré avec succès par {ctx.author.mention}. Le chat est propre.")

# 5. Autres Commandes
@bot.command()
async def ping(ctx):
    await ctx.send('Pong ! 🏓')

# 6. Lancement
if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Erreur : DISCORD_TOKEN manquant.")
