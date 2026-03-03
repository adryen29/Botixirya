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
LOG_CHANNEL_ID = 1478437400496705721  # Ton salon de logs précédent
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

# Variable globale pour stocker le nombre actuel et le dernier utilisateur
current_count = 0
last_user_id = None

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"✅ **{bot.user.name}** est en ligne. Préfixe actuel : `{COMMAND_PREFIX}`")

@bot.event
async def on_message(message):
    global current_count, last_user_id

    # Ne pas répondre à soi-même
    if message.author == bot.user:
        return

    # Logique du jeu de comptage
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            content = message.content.strip()
            # On vérifie si le message est un nombre
            number = int(content)

            # Vérification : n+1 et pas le même utilisateur deux fois
            if number == current_count + 1 and message.author.id != last_user_id:
                current_count = number
                last_user_id = message.author.id
                await message.add_reaction("✅")
            else:
                # Erreur : on recommence à 0
                current_count = 0
                last_user_id = None
                await message.add_reaction("❌")
                
                reason = "Mauvais nombre !" if number != current_count + 1 else "Tu ne peux pas compter deux fois de suite !"
                await message.channel.send(f"⚠️ {message.author.mention} a cassé la suite ! **{reason}** Le prochain nombre est **1**.")

        except ValueError:
            # Si ce n'est pas un nombre, on ignore ou on peut aussi casser la suite
            pass

    # Important pour que les commandes fonctionnent encore
    await bot.process_commands(message)

# 3. Gestionnaire d'erreurs (envoie dans #bot-logs)
@bot.event
async def on_command_error(ctx, error):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="❌ Erreur de Commande", color=discord.Color.red())
        embed.add_field(name="Commande", value=ctx.message.content)
        embed.add_field(name="Erreur", value=f"```py\n{error}\n```")
        await channel.send(embed=embed)

# 4. Commandes
@bot.command()
async def ping(ctx):
    await ctx.send('Pong ! 🏓')

@bot.command()
async def score(ctx):
    """Affiche le score actuel du comptage"""
    await ctx.send(f"Le score actuel est de **{current_count}**. Le prochain est **{current_count + 1}** !")

# 5. Lancement
if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Erreur : DISCORD_TOKEN manquant.")
