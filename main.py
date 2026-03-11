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
DB_CHANNEL_ID = 1479105188454338611         # Salon Discord servant de base de données
VERIFY_CHANNEL_ID = 1478658827682582662
ROLE_UNVERIFIED_ID = 1478658867415089263
ROLE_VERIFIED_ID = 1477170552950231164
GIVEAWAY_FILE = "giveaways.json"

BAN_LOG_CHANNEL_ID = 1481201790375563498    # Logs bans
KICK_LOG_CHANNEL_ID = 1481202403574284310   # Logs kicks
MUTE_LOG_CHANNEL_ID = 1481202820500684841   # Logs mutes
MUTED_ROLE_ID = 1481203639107325983         # Rôle Muted
BANS_FILE = "bans.json"

OWNER_ID = 1339332485930160189              # ID du propriétaire
MAIN_SERVER_ID = 1472951773026062482        # Serveur principal
BACKUP_SERVER_ID = 1481205788566618115      # Serveur de backup

RAID_THRESHOLD = 3    # Nombre de suppressions déclenchant l'anti-raid
RAID_WINDOW = 30      # Fenêtre de temps en secondes

ROLE_BACKUP_CHANNEL_ID = 1481211118843203647  # Sauvegarde des rôles avant quarantaine
RAID_LOG_CHANNEL_ID = 1481211696109326466     # Logs des tentatives de raid
# ==========================================

# --- État global ---
current_count = 0
last_user_id = None
active_counting_channel = 0
commands_on_backup = False
deletion_tracker = {}   # {guild_id: {user_id: {"channels": [...], "roles": [...]}}}
quarantined_users = {}  # {user_id: [role_ids]}

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

# --- Vérification globale : serveur backup ---
@bot.check
async def global_backup_check(ctx):
    """Bloque toutes les commandes sur le serveur backup sauf backup et COMMANDSON."""
    if ctx.guild and ctx.guild.id == BACKUP_SERVER_ID:
        if ctx.command and ctx.command.name in ('backup', 'COMMANDSON'):
            return True
        return commands_on_backup
    return True

# ==========================================
# GESTION DES DONNÉES
# ==========================================

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

def load_bans():
    if os.path.exists(BANS_FILE):
        try:
            with open(BANS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_bans(data):
    with open(BANS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def save_counting_to_db():
    """Sauvegarde le score dans le salon DB Discord."""
    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        await db_chan.send(f"BACKUP_COUNT|{current_count}|{last_user_id}|{active_counting_channel}")

async def send_log(content):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(content)

# ==========================================
# ANTI-RAID
# ==========================================

async def quarantine_user(guild, member):
    """Retire tous les rôles et bloque toutes les permissions d'un membre. Seul le propriétaire est immunisé."""
    if member.id == OWNER_ID:
        return

    user_id = str(member.id)
    roles_avant = [r.id for r in member.roles if r != guild.default_role]
    quarantined_users[user_id] = roles_avant

    # --- Sauvegarde des rôles dans le salon dédié ---
    role_backup_chan = bot.get_channel(ROLE_BACKUP_CHANNEL_ID)
    if role_backup_chan and roles_avant:
        roles_str = ",".join(str(r) for r in roles_avant)
        await role_backup_chan.send(
            f"ROLE_BACKUP|{guild.id}|{member.id}|{roles_str}"
        )

    # --- Retrait des rôles ---
    try:
        await member.edit(roles=[], reason="Anti-Raid : suppressions en masse détectées")
    except:
        pass

    # --- Blocage de tous les salons ---
    for channel in guild.channels:
        try:
            await channel.set_permissions(
                member,
                send_messages=False,
                read_messages=False,
                manage_channels=False,
                manage_roles=False,
                reason="Anti-Raid"
            )
        except:
            pass

    # --- Log dans le salon raid ---
    raid_log_chan = bot.get_channel(RAID_LOG_CHANNEL_ID)
    tag = "🤖 **BOT**" if member.bot else "👤 **Utilisateur**"
    if raid_log_chan:
        await raid_log_chan.send(
            f"🚨 **TENTATIVE DE RAID DÉTECTÉE**\n"
            f"{tag} : {member.mention} (`{member.id}`)\n"
            f"Rôles retirés : {len(roles_avant)}\n"
            f"Accès à tous les salons révoqué.\n"
            f"Utilisez `{COMMAND_PREFIX}safe @{member.name}` ou `{COMMAND_PREFIX}Give_Role_Back @{member.name}` pour intervenir."
        )

    # --- Log général ---
    log_chan = bot.get_channel(LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(
            f"🚨 **ANTI-RAID** : {member.mention} (`{member.id}`) mis en quarantaine ({tag})."
        )

async def track_deletion(guild, user, dtype):
    """Suit les suppressions d'un utilisateur. dtype : 'channels' ou 'roles'. Seul le propriétaire est immunisé."""
    if user.id == OWNER_ID:
        return

    now = time.time()
    gid = str(guild.id)
    uid = str(user.id)

    if gid not in deletion_tracker:
        deletion_tracker[gid] = {}
    if uid not in deletion_tracker[gid]:
        deletion_tracker[gid][uid] = {"channels": [], "roles": []}

    tracker = deletion_tracker[gid][uid]
    tracker[dtype] = [t for t in tracker[dtype] if now - t < RAID_WINDOW]
    tracker[dtype].append(now)

    total = len(tracker["channels"]) + len(tracker["roles"])
    if total >= RAID_THRESHOLD:
        deletion_tracker[gid][uid] = {"channels": [], "roles": []}  # Reset
        member = guild.get_member(user.id)
        if member:
            await quarantine_user(guild, member)

# ==========================================
# VIEWS
# ==========================================

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

# ==========================================
# TÂCHES PÉRIODIQUES
# ==========================================

@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_giveaway()
    now = time.time()
    for msg_id, gw in list(data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            gw['ended'] = True
            save_giveaway(data)

@tasks.loop(seconds=60)
async def check_bans():
    """Vérifie les bans temporaires expirés et unban automatiquement."""
    bans = load_bans()
    now = time.time()
    to_remove = []

    for key, ban_data in list(bans.items()):
        if ban_data.get('end_time') and now >= ban_data['end_time']:
            guild = bot.get_guild(ban_data['guild_id'])
            if guild:
                try:
                    user = await bot.fetch_user(ban_data['user_id'])
                    await guild.unban(user, reason="Expiration du ban temporaire")
                    log_chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
                    if log_chan:
                        await log_chan.send(
                            f"⏱️ **Unban automatique** : <@{ban_data['user_id']}> "
                            f"(`{ban_data['user_id']}`) — ban expiré."
                        )
                except:
                    pass
                to_remove.append(key)

    for key in to_remove:
        del bans[key]
    if to_remove:
        save_bans(bans)

# ==========================================
# ÉVÉNEMENTS
# ==========================================

@bot.event
async def on_ready():
    global current_count, last_user_id, active_counting_channel
    bot.add_view(GiveawayView(bot))
    bot.add_view(VerifyView())

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
    if not check_bans.is_running():
        check_bans.start()

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

@bot.event
async def on_guild_channel_delete(channel):
    """Détecte la suppression de salons pour l'anti-raid."""
    guild = channel.guild
    await asyncio.sleep(0.5)
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if time.time() - entry.created_at.timestamp() < 5:
                await track_deletion(guild, entry.user, "channels")
            break
    except:
        pass

@bot.event
async def on_guild_role_delete(role):
    """Détecte la suppression de rôles pour l'anti-raid."""
    guild = role.guild
    await asyncio.sleep(0.5)
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if time.time() - entry.created_at.timestamp() < 5:
                await track_deletion(guild, entry.user, "roles")
            break
    except:
        pass

# ==========================================
# COMMANDES
# ==========================================

@bot.command()
async def help(ctx):
    """Affiche la liste des commandes disponibles."""
    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())
    embed.add_field(name="🛡️ Système", value=(
        f"**{COMMAND_PREFIX}kill** : Éteint le bot.\n"
        f"**{COMMAND_PREFIX}ping** : Affiche la latence.\n"
        f"**{COMMAND_PREFIX}score** : Affiche le score actuel."
    ), inline=False)
    embed.add_field(name="⚙️ Admin", value=(
        f"**{COMMAND_PREFIX}setcountchannel** : Définit le salon de comptage.\n"
        f"**{COMMAND_PREFIX}setscore [nb]** : Modifie manuellement le score.\n"
        f"**{COMMAND_PREFIX}lock / unlock** : Verrouille ou déverrouille le salon.\n"
        f"**{COMMAND_PREFIX}restore** : Recrée le salon actuel."
    ), inline=False)
    embed.add_field(name="🔨 Modération", value=(
        f"**{COMMAND_PREFIX}msgdel [nb] (@user)** : Supprime des messages (optionnel : filtre par user).\n"
        f"**{COMMAND_PREFIX}ban @user [min] [raison]** : Bannit pour X minutes (0 = permanent).\n"
        f"**{COMMAND_PREFIX}pardon @user** : Débannit un utilisateur.\n"
        f"**{COMMAND_PREFIX}kick @user [raison]** : Expulse un utilisateur.\n"
        f"**{COMMAND_PREFIX}mute @user [raison]** : Mute (rôle Muted + retire rôle Membre).\n"
        f"**{COMMAND_PREFIX}unmute @user** : Unmute (retire Muted + redonne Membre).\n"
        f"**{COMMAND_PREFIX}safe @user** : Lève la quarantaine anti-raid **(owner only)**.\n"
        f"**{COMMAND_PREFIX}Give_Role_Back @user** : Restaure les rôles depuis la sauvegarde Discord **(owner only)**."
    ), inline=False)
    embed.add_field(name="🎁 Giveaway", value=f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [condition]**", inline=False)
    embed.add_field(name="💾 Backup", value=(
        f"**{COMMAND_PREFIX}backup** : Copie le serveur principal → backup *(backup server only)*.\n"
        f"**{COMMAND_PREFIX}COMMANDSON** : Active toutes les commandes sur le serveur backup *(owner only)*."
    ), inline=False)
    await ctx.send(embed=embed)

# --- Système ---

@bot.command()
@commands.has_permissions(administrator=True)
async def kill(ctx):
    """Éteint le bot (le score est déjà sauvegardé en temps réel)."""
    await ctx.send("💀 Extinction...")
    await asyncio.sleep(2)
    await bot.close()
    sys.exit()

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def score(ctx):
    await ctx.send(f"Score actuel : **{current_count}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setcountchannel(ctx):
    global active_counting_channel
    active_counting_channel = ctx.channel.id
    await save_counting_to_db()
    await ctx.send("✅ Salon de comptage défini.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setscore(ctx, number: int):
    global current_count, last_user_id
    current_count = number
    last_user_id = None
    await save_counting_to_db()
    await ctx.send(f"✅ Score fixé à {number}.")

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

# --- Modération ---

@bot.command()
@commands.has_permissions(manage_messages=True)
async def msgdel(ctx, number: int, user: discord.Member = None):
    """Supprime [number] messages, optionnellement filtrés par utilisateur."""
    await ctx.message.delete()

    to_delete = []
    async for msg in ctx.channel.history(limit=500):
        if user is None or msg.author == user:
            to_delete.append(msg)
        if len(to_delete) >= number:
            break

    now = discord.utils.utcnow()
    recent = [m for m in to_delete if (now - m.created_at).total_seconds() < 1209600]
    old = [m for m in to_delete if (now - m.created_at).total_seconds() >= 1209600]

    for i in range(0, len(recent), 100):
        try:
            await ctx.channel.delete_messages(recent[i:i+100])
        except:
            pass

    for m in old:
        try:
            await m.delete()
            await asyncio.sleep(0.7)
        except:
            pass

    mention = f" de {user.mention}" if user else ""
    confirm = await ctx.send(f"🗑️ {len(to_delete)} message(s){mention} supprimé(s).")
    await asyncio.sleep(4)
    await confirm.delete()

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, user: discord.Member, duration: int, *, reason: str = "Aucune raison fournie"):
    """Bannit un utilisateur. duration en minutes (0 = permanent)."""
    end_time = time.time() + duration * 60 if duration > 0 else None

    try:
        await user.ban(reason=reason)
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    bans = load_bans()
    key = f"{ctx.guild.id}:{user.id}"
    bans[key] = {
        "user_id": user.id,
        "guild_id": ctx.guild.id,
        "reason": reason,
        "end_time": end_time,
        "moderator": ctx.author.id
    }
    save_bans(bans)

    duration_str = f"{duration} minute(s)" if duration > 0 else "permanent"
    log_chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(
            f"🔨 **Ban** : {user} (`{user.id}`)\n"
            f"👮 Par : {ctx.author.mention}\n"
            f"⏱️ Durée : {duration_str}\n"
            f"📝 Raison : {reason}"
        )

    await ctx.send(f"🔨 {user.mention} banni ({duration_str}). Raison : {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def pardon(ctx, user: discord.User):
    """Débannit un utilisateur."""
    try:
        await ctx.guild.unban(user, reason=f"Pardonné par {ctx.author}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    bans = load_bans()
    key = f"{ctx.guild.id}:{user.id}"
    if key in bans:
        del bans[key]
        save_bans(bans)

    log_chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(f"✅ **Unban** : {user} (`{user.id}`) pardonné par {ctx.author.mention}")

    await ctx.send(f"✅ {user} a été débanni.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, user: discord.Member, *, reason: str = "Aucune raison fournie"):
    """Expulse un utilisateur."""
    try:
        await user.kick(reason=reason)
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    log_chan = bot.get_channel(KICK_LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(
            f"👢 **Kick** : {user} (`{user.id}`)\n"
            f"👮 Par : {ctx.author.mention}\n"
            f"📝 Raison : {reason}"
        )

    await ctx.send(f"👢 {user.mention} expulsé. Raison : {reason}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, user: discord.Member, *, reason: str = "Aucune raison fournie"):
    """Mute : donne le rôle Muted et retire le rôle Membre."""
    muted_role = ctx.guild.get_role(MUTED_ROLE_ID)
    membre_role = ctx.guild.get_role(ROLE_VERIFIED_ID)

    if not muted_role:
        return await ctx.send("❌ Rôle Muted introuvable.")

    try:
        await user.add_roles(muted_role, reason=reason)
        if membre_role and membre_role in user.roles:
            await user.remove_roles(membre_role, reason=reason)
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    log_chan = bot.get_channel(MUTE_LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(
            f"🔇 **Mute** : {user} (`{user.id}`)\n"
            f"👮 Par : {ctx.author.mention}\n"
            f"📝 Raison : {reason}"
        )

    await ctx.send(f"🔇 {user.mention} mute. Raison : {reason}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, user: discord.Member):
    """Unmute : retire le rôle Muted et redonne le rôle Membre."""
    muted_role = ctx.guild.get_role(MUTED_ROLE_ID)
    membre_role = ctx.guild.get_role(ROLE_VERIFIED_ID)

    if not muted_role:
        return await ctx.send("❌ Rôle Muted introuvable.")

    try:
        if muted_role in user.roles:
            await user.remove_roles(muted_role, reason=f"Unmute par {ctx.author}")
        if membre_role and membre_role not in user.roles:
            await user.add_roles(membre_role, reason=f"Unmute par {ctx.author}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    await ctx.send(f"🔊 {user.mention} unmute.")

@bot.command()
async def safe(ctx, user: discord.Member):
    """Lève la quarantaine anti-raid d'un utilisateur et restaure ses rôles. (Owner uniquement)"""
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    user_id = str(user.id)

    for channel in ctx.guild.channels:
        try:
            overwrite = channel.overwrites_for(user)
            if overwrite.send_messages is False or overwrite.read_messages is False:
                await channel.set_permissions(user, overwrite=None)
        except:
            pass

    if user_id in quarantined_users:
        roles_to_restore = []
        for role_id in quarantined_users[user_id]:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_to_restore.append(role)
        try:
            await user.edit(roles=roles_to_restore, reason=f"Safe par {ctx.author}")
        except Exception as e:
            await ctx.send(f"⚠️ Erreur restauration des rôles : {e}")
        del quarantined_users[user_id]
        await ctx.send(f"✅ {user.mention} sorti de quarantaine, rôles restaurés.")
    else:
        await ctx.send(f"✅ Restrictions levées pour {user.mention} (pas en quarantaine formelle).")

    await send_log(f"🛡️ **Safe** : {user.mention} libéré par {ctx.author.mention}")

@bot.command()
async def Give_Role_Back(ctx, user: discord.Member):
    """Restaure les rôles d'un utilisateur depuis le salon de sauvegarde. (Owner uniquement)"""
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    role_backup_chan = bot.get_channel(ROLE_BACKUP_CHANNEL_ID)
    if not role_backup_chan:
        return await ctx.send("❌ Salon de sauvegarde des rôles introuvable.")

    # Recherche de la dernière sauvegarde pour cet utilisateur
    found_roles = None
    async for message in role_backup_chan.history(limit=200):
        if f"ROLE_BACKUP|{ctx.guild.id}|{user.id}|" in message.content:
            parts = message.content.strip().split("|")
            if len(parts) >= 4 and parts[3]:
                found_roles = [int(r) for r in parts[3].split(",") if r.strip().isdigit()]
            break

    if not found_roles:
        return await ctx.send(f"❌ Aucune sauvegarde de rôles trouvée pour {user.mention}.")

    roles_to_restore = []
    for role_id in found_roles:
        role = ctx.guild.get_role(role_id)
        if role:
            roles_to_restore.append(role)

    try:
        await user.edit(roles=roles_to_restore, reason=f"Give_Role_Back par {ctx.author}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur lors de la restauration : {e}")

    # Nettoyage des overrides de permissions
    for channel in ctx.guild.channels:
        try:
            overwrite = channel.overwrites_for(user)
            if overwrite.send_messages is False or overwrite.read_messages is False:
                await channel.set_permissions(user, overwrite=None)
        except:
            pass

    # Nettoyage en mémoire si présent
    user_id = str(user.id)
    if user_id in quarantined_users:
        del quarantined_users[user_id]

    raid_log_chan = bot.get_channel(RAID_LOG_CHANNEL_ID)
    if raid_log_chan:
        roles_names = ", ".join(r.name for r in roles_to_restore) or "aucun"
        await raid_log_chan.send(
            f"✅ **Give_Role_Back** : {user.mention} (`{user.id}`)\n"
            f"Rôles restaurés par {ctx.author.mention} : {roles_names}"
        )

    await ctx.send(f"✅ Rôles restaurés pour {user.mention} ({len(roles_to_restore)} rôle(s)).")

# ==========================================
# COMMANDES BACKUP SERVER
# ==========================================

@bot.command()
async def COMMANDSON(ctx):
    """Active toutes les commandes sur le serveur backup. (Owner uniquement)"""
    global commands_on_backup
    if ctx.guild.id != BACKUP_SERVER_ID:
        return
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Réservé au propriétaire.")
    commands_on_backup = True
    await ctx.send("✅ Toutes les commandes sont maintenant actives sur ce serveur.")

@bot.command()
async def backup(ctx):
    """Copie la structure (rôles, catégories, salons) du serveur principal vers ce serveur. (backup server only)"""
    if ctx.guild.id != BACKUP_SERVER_ID:
        return await ctx.send("❌ Cette commande ne fonctionne que sur le serveur de backup.")
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Réservé au propriétaire.")

    main_guild = bot.get_guild(MAIN_SERVER_ID)
    if not main_guild:
        return await ctx.send(
            "❌ Impossible d'accéder au serveur principal. "
            "Le bot est-il présent sur les deux serveurs ?"
        )

    backup_guild = ctx.guild
    status_msg = await ctx.send("🔄 Démarrage de la backup...")

    # --- Copie des rôles ---
    await status_msg.edit(content="🔄 Copie des rôles en cours...")
    role_map = {}
    existing_roles = {r.name: r for r in backup_guild.roles}

    for role in sorted(main_guild.roles, key=lambda r: r.position):
        if role.is_default():
            continue
        if role.name in existing_roles:
            role_map[role.id] = existing_roles[role.name]
        else:
            try:
                new_role = await backup_guild.create_role(
                    name=role.name,
                    color=role.color,
                    permissions=role.permissions,
                    hoist=role.hoist,
                    mentionable=role.mentionable,
                    reason="Botixirya Backup"
                )
                role_map[role.id] = new_role
                existing_roles[role.name] = new_role
                await asyncio.sleep(0.4)
            except Exception as e:
                await ctx.send(f"⚠️ Rôle `{role.name}` ignoré : {e}")

    # --- Copie des catégories ---
    await status_msg.edit(content="🔄 Copie des catégories en cours...")
    category_map = {}
    existing_channels = {c.name: c for c in backup_guild.channels}

    for category in main_guild.categories:
        if category.name in existing_channels:
            category_map[category.id] = existing_channels[category.name]
        else:
            try:
                new_cat = await backup_guild.create_category(
                    name=category.name,
                    reason="Botixirya Backup"
                )
                category_map[category.id] = new_cat
                existing_channels[category.name] = new_cat
                await asyncio.sleep(0.4)
            except Exception as e:
                await ctx.send(f"⚠️ Catégorie `{category.name}` ignorée : {e}")

    # --- Copie des salons ---
    await status_msg.edit(content="🔄 Copie des salons en cours...")
    for channel in main_guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue
        if channel.name in existing_channels:
            continue
        cat = category_map.get(channel.category_id) if channel.category_id else None
        try:
            if isinstance(channel, discord.TextChannel):
                await backup_guild.create_text_channel(
                    name=channel.name,
                    category=cat,
                    topic=channel.topic or "",
                    reason="Botixirya Backup"
                )
            elif isinstance(channel, discord.VoiceChannel):
                await backup_guild.create_voice_channel(
                    name=channel.name,
                    category=cat,
                    reason="Botixirya Backup"
                )
            await asyncio.sleep(0.4)
        except Exception as e:
            await ctx.send(f"⚠️ Salon `{channel.name}` ignoré : {e}")

    await status_msg.edit(
        content="✅ **Backup terminée !**\nRôles, catégories et salons copiés depuis le serveur principal."
    )

# ==========================================

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
