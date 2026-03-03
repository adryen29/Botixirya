import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
COUNTING_CHANNEL_ID = 1478440739095580822
LOG_CHANNEL_ID = 1478437400496705721
GIVEAWAY_FILE = "giveaways.json"
# ==========================================

app = Flask('')
@app.route('/')
def home(): return "Botixirya est en vie !"

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Nécessaire pour tirer au sort parmi les membres
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- Gestion de la persistence des Giveaways ---

def save_giveaway(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f)

def load_giveaway():
    if os.path.exists(GIVEAWAY_FILE):
        with open(GIVEAWAY_FILE, "r") as f:
            return json.load(f)
    return {}

# --- Vue pour les boutons (Participation et Reroll) ---

class GiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Participer ! 🎉", style=discord.ui.ButtonStyle.blurple, custom_id="join_gw")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.button):
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        
        if gw_id not in data or data[gw_id]['ended']:
            return await interaction.response.send_message("Ce concours est terminé.", ephemeral=True)
        
        if interaction.user.id in data[gw_id]['participants']:
            return await interaction.response.send_message("Tu participes déjà !", ephemeral=True)
        
        data[gw_id]['participants'].append(interaction.user.id)
        save_giveaway(data)
        await interaction.response.send_message("Ta participation a été enregistrée !", ephemeral=True)

    @discord.ui.button(label="Reroll (Admin)", style=discord.ui.ButtonStyle.gray, custom_id="reroll_gw")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Seuls les admins peuvent reroll.", ephemeral=True)
        
        data = load_giveaway()
        gw_id = str(interaction.message.id)
        
        if gw_id not in data or not data[gw_id]['participants']:
            return await interaction.response.send_message("Impossible de reroll (pas assez de participants).", ephemeral=True)
        
        winner_id = random.choice(data[gw_id]['participants'])
        winner = interaction.guild.get_member(winner_id)
        
        await interaction.channel.send(f"🎲 **Reroll :** Le nouveau gagnant est {winner.mention} ! Félicitations !")
        await interaction.response.send_message("Reroll effectué.", ephemeral=True)

# --- Tâche de vérification en arrière-plan ---

@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_giveaway()
    now = time.time()
    
    for msg_id, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            channel = bot.get_channel(gw['channel_id'])
            if not channel: continue
            
            try:
                message = await channel.fetch_message(int(msg_id))
                participants = gw['participants']
                
                if len(participants) < gw['winners_count']:
                    await channel.send(f"Le concours pour **{gw['prize']}** est terminé, mais il n'y a pas assez de participants.")
                else:
                    winners = random.sample(participants, gw['winners_count'])
                    mentions = ", ".join([f"<@{w}>" for w in winners])
                    
                    embed = message.embeds[0]
                    embed.color = discord.Color.gray()
                    embed.description = f"Terminé !\nGagnant(s) : {mentions}"
                    await message.edit(embed=embed)
                    await channel.send(f"🎉 Félicitations {mentions} ! Tu as gagné **{gw['prize']}** !")
                
                gw['ended'] = True
                save_giveaway(data)
            except:
                continue

# --- Événements et Commandes ---

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    bot.add_view(GiveawayView(bot)) # Pour que les boutons marchent après reboot
    check_giveaways.start()
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"✅ **Botixirya** prêt. Système de Giveaway sécurisé activé.")

@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, hours: int, winners: int, prize: str, *, requirement: str = "Aucune"):
    end_time = time.time() + (hours * 3600)
    
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Prix", value=prize, inline=False)
    embed.add_field(name="Gagnants", value=str(winners), inline=True)
    embed.add_field(name="Fin", value=f"<t:{int(end_time)}:R>", inline=True)
    embed.add_field(name="Condition", value=requirement, inline=False)
    embed.set_footer(text="Cliquez sur le bouton pour participer")
    
    msg = await ctx.send(embed=embed, view=GiveawayView(bot))
    
    data = load_giveaway()
    data[str(msg.id)] = {
        "channel_id": ctx.channel.id,
        "prize": prize,
        "winners_count": winners,
        "end_time": end_time,
        "participants": [],
        "ended": False
    }
    save_giveaway(data)

# ... (Ici tu gardes tes commandes lock, unlock, restore et le jeu de comptage précédentes) ...

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    bot.run(token)
