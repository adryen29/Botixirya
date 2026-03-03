import discord
from discord.ext import commands
import os
import traceback
from flask import Flask
from threading import Thread

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

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Connecté avec succès en tant que {bot.user}')
    # Notification au démarrage dans le salon de logs
    channel_id = os.getenv('LOG_CHANNEL_ID')
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            await channel.send(f"✅ **{bot.user.name}** est maintenant en ligne et surveille les erreurs.")

# 3. Gestionnaire d'erreurs automatique
@bot.event
async def on_command_error(ctx, error):
    # On récupère l'ID du salon de logs
    channel_id = os.getenv('LOG_CHANNEL_ID')
    
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            # Création d'un message d'erreur détaillé (Embed)
            embed = discord.Embed(
                title="❌ Erreur détectée",
                description=f"Une erreur est survenue lors de l'exécution d'une commande.",
                color=discord.Color.red()
            )
            embed.add_field(name="Commande", value=ctx.command.name if ctx.command else "Inconnue", inline=True)
            embed.add_field(name="Utilisateur", value=ctx.author.mention, inline=True)
            embed.add_field(name="Erreur", value=f"```py\n{error}\n```", inline=False)
            
            await channel.send(embed=embed)
    
    # On affiche aussi l'erreur dans la console Koyeb pour être sûr
    print(f"Erreur commande: {error}")

@bot.command()
async def ping(ctx):
    await ctx.send('Pong ! 🏓')

# 4. Lancement
if __name__ == "__main__":
    keep_alive() 
    
    token = os.getenv('DISCORD_TOKEN')
    
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"Erreur fatale au lancement : {e}")
    else:
        print("Erreur : La variable 'DISCORD_TOKEN' est introuvable.")
