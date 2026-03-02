import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# Mets ton token entre les guillemets ci-dessous
TOKEN_BOT = "TON_TOKEN_ICI"
# ---------------------

# 1. Configuration du mini serveur Web pour le "Keep-Alive"
app = Flask('')

@app.route('/')
def home():
    return "Bot en ligne !"

def run():
    # On utilise le port 8000 pour correspondre à ta config Koyeb
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Configuration du Bot Discord
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong ! 🏓')

# 3. Lancement
if __name__ == "__main__":
    keep_alive() # Lance le serveur web en arrière-plan
    
    # On vérifie d'abord la variable manuelle, sinon on cherche dans les variables d'environnement
    token = TOKEN_BOT if TOKEN_BOT != "TON_TOKEN_ICI" else os.getenv('DISCORD_TOKEN')
    
    if token:
        bot.run(token)
    else:
        print("Erreur : Aucun TOKEN trouvé. Remplace 'TON_TOKEN_ICI' en haut du script.")