import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
import random
import re
import sys
import io
import uuid
import math
import aiohttp
from flask import Flask, request
import requests as req_lib
from threading import Thread

# ==========================================
# VARIABLES MODIFIABLES (VISIBLES)
# ==========================================
COMMAND_PREFIX = "<aav>"
LOG_CHANNEL_ID = 1478437400496705721
DB_CHANNEL_ID = 1479105188454338611             # Salon Discord servant de base de données
VERIFY_CHANNEL_ID = 1478658827682582662
ROLE_UNVERIFIED_ID = 1478658867415089263
ROLE_VERIFIED_ID = 1477170552950231164
MANUAL_LOG_CHANNEL_ID = 1510623278379565288   # Logs actions manuelles Discord


BAN_LOG_CHANNEL_ID = 1481201790375563498         # Logs bans + mémoire persistance des bans
KICK_LOG_CHANNEL_ID = 1481202403574284310        # Logs kicks
MUTE_LOG_CHANNEL_ID = 1481202820500684841        # Logs mutes
MUTED_ROLE_ID = 1481203639107325983              # Rôle Muted

GIVEAWAY_MEMORY_CHANNEL_ID = 1543983392733790329 # Mémoire des giveaways (persistance Discord)

TEMPBAN_LOG_CHANNEL_ID  = 1510401125616980169    # Logs + mémoire tempbans
TEMPMUTE_LOG_CHANNEL_ID = 1510400362526543934    # Logs + mémoire tempmutes

MEMBER_LOG_CHANNEL_ID        = 1510621031960805396   # Arrivées & départs
MESSAGES_LOG_CHANNEL_ID      = 1510620947621613599   # Messages supprimés & modifiés
ADMIN_ACTIONS_LOG_CHANNEL_ID = 1510620898363707533   # Commandes admin/modo utilisées
VERIF_HISTORY_LOG_CHANNEL_ID = 1510620834547367936   # Historique vérifications Roblox

ONLINE_COUNTER_CHANNEL_ID = 1477628409826906183  # Salon vocal affichant le nombre de membres en ligne

# --- Système d'invitations ---
INVITE_ARRIVAL_CHANNEL_ID = 1477457433184960719   # Annonce "X a invité Y" à chaque arrivée
INVITE_DEPART_CHANNEL_ID = 1505846628546773143     # Annonce des départs (avec rappel de l'inviteur si connu)
INVITE_CASHOUT_CHANNEL_ID = 1544422573914198046    # Demandes de cashout + confirmation de paiement (logs permanents)
INVITE_DATA_CHANNEL_ID = 1544421684201652314       # Mémoire principale (soldes, compteurs, historique cashouts)
ALREADY_INVITED_CHANNEL_ID = 1544426137164455967   # Liste permanente des ID déjà invités une fois (anti-farming)
INVITE_REWARD_PER_INVITE = 10   # Robux crédités par invitation valide
INVITE_CASHOUT_MINIMUM = 50     # Solde minimum requis pour pouvoir cash out
INVITE_MIN_ACCOUNT_AGE_DAYS = 30  # Âge minimum du compte invité pour être crédité (anti-fraude)

# --- Système de warns / big warns ---
WARN_LOG_CHANNEL_ID = 1545832162748792972   # Logs + mémoire des warns/big warns
WARN_SIMPLE_EXPIRY_DAYS = 30    # Un warn simple expire après ce délai s'il n'a jamais atteint 3
BIGWARN_EXPIRY_DAYS = 90        # Un big warn expire après ce délai sans nouveau big warn
WARNS_PER_BIGWARN = 3           # Nombre de warns simples consommés pour déclencher un big warn automatique

# --- Messages de bienvenue du système d'invitations (un choisi au hasard à chaque arrivée) ---
INVITE_WELCOME_CREDITED = [
    "🎉 Bienvenue {invited} ! Tu as été invité(e) par {inviter}, merci à lui/elle de faire grandir la communauté !",
    "👋 Bienvenue parmi nous, {invited} ! → invité(e) par {inviter} 🎉",
    "🎉 **{invited}** vient de nous rejoindre !\nInvité(e) par **{inviter}**",
    "🥳 Un nouveau visage ! Bienvenue {invited}, ravi de t'avoir avec nous grâce à {inviter} !",
    "📥 {invited} a rejoint le serveur, invité(e) par {inviter}. Bienvenue à toi !",
]
INVITE_WELCOME_ALREADY_SEEN = [
    "👋 {invited} nous rejoint à nouveau, ravis de te revoir !",
    "🔄 Rebonjour {invited}, content de te retrouver parmi nous !",
    "👋 {invited} est de retour, bienvenue à nouveau !",
]
INVITE_WELCOME_UNKNOWN = [
    "👋 Bienvenue {invited}, on est content de t'avoir parmi nous !",
    "🎉 {invited} vient de rejoindre le serveur, bienvenue à toi !",
]

OWNER_ID = 1339332485930160189                   # ID du propriétaire
MAIN_SERVER_ID = 1472951773026062482             # Serveur principal
BACKUP_SERVER_ID = 1481205788566618115           # Serveur de backup

RAID_THRESHOLD = 3                               # Nb suppressions déclenchant l'anti-raid
RAID_WINDOW = 600                                # Fenêtre de temps en secondes (10 minutes)

ROLE_BACKUP_CHANNEL_ID = 1481211118843203647     # Sauvegarde des rôles avant quarantaine
RAID_LOG_CHANNEL_ID = 1481211696109326466        # Logs des tentatives de raid
RAIDER_ROLE_ID = 1482735894745186435             # Rôle donné aux raiders

TICKET_MEMORY_CHANNEL_ID = 1482417571549544690   # Mémoire des configs de tickets
TABLE_LOG_CHANNEL_ID = 1483437540299243670       # Logs/sauvegarde du tableau de rémunération

# --- Roblox Group Funds ---
ROBLOX_GROUP_UGC = 35515170                      # Groupe Aavixyria UGC
ROBLOX_GROUP_CLOTHING = 16522178                 # Groupe Aavixyria Clothing
FUNDS_UGC_CHANNEL_ID = 1483505991994835057       # Salon funds UGC
FUNDS_CLOTHING_CHANNEL_ID = 1483508939504091187  # Salon funds Clothing

# --- Rôles et zones à vérifier toutes les 20 minutes ---
PERM_UNVERIFIED_EXCEPTION_CATEGORY = 1478663941168037898
PERM_UNVERIFIED_EXCEPTION_CHANNEL = 1478669348989177997

# --- Système de niveaux ---
LEVEL_UP_CHANNEL_ID = 1483746384610857092        # Salon de ping lors d'un niveau à rôle
XP_MEMORY_CHANNEL_ID = 1483747180853596190       # Sauvegarde de l'XP
LEVEL_ROLES = {
    5:   1483745785966366750,
    10:  1483745824906416138,
    15:  1483746241379827804,
    30:  1483745868648546414,
    50:  1483745915004129280,
    100: 1483745942468296704,
}
XP_COOLDOWN = 60        # Secondes entre deux gains d'XP par utilisateur
XP_MIN = 15             # XP minimum par message
XP_MAX = 25             # XP maximum par message

# --- Donations Roblox ---
DONATION_SCOREBOARD_CHANNEL_ID = 1484302892059066538  # Salon affichage scoreboard
DONATION_MEMORY_CHANNEL_ID = 1484303351649665116      # Salon logs/sauvegarde donations
DONATION_SECRET = os.getenv("DONATION_SECRET", "change_moi")  # Token secret Roblox → bot

# --- Vérification OAuth Roblox ---
ROBLOX_CLIENT_ID     = "4841751639344220253"
ROBLOX_CLIENT_SECRET = os.getenv("ROBLOX_CLIENT_SECRET", "")
ROBLOX_REDIRECT_URI  = "https://vulnerable-angelfish-aavixyria-79722b21.koyeb.app/roblox/callback"
ROLE_ROBLOX_LINKED_ID    = 1484610496861700247   # Rôle attribué après liaison Roblox
ROBLOX_VERIFY_CHANNEL_ID = 1484611746101596351   # Seul salon visible par ce rôle
ROBLOX_LINKS_CHANNEL_ID  = 1484617094531387424   # Mémoire des liaisons Discord ↔ Roblox
# ==========================================

# --- État global ---
current_count = 0
last_user_id = None
active_counting_channel = 0
commands_on_backup = False
deletion_tracker = {}
quarantined_users = {}
safe_users = set()
ticket_configs = {}
table_data = {}
table_channel_id = None
table_message_id = None
funds_ugc_message_id = None
funds_clothing_message_id = None
xp_data = {}            # {user_id: {"xp": int, "level": int, "streak": int, "last_daily": str, "xp_today": int}}
xp_cooldowns = {}       # {user_id: last_xp_timestamp}
slots_cooldowns = {}    # {user_id: last_slots_timestamp}

# --- Anti-raid @everyone ---
everyone_tracker = {}   # {guild_id: {user_id: [timestamps]}}

# --- Donations ---
donations_data = {}     # {user_id: {"username": str, "total": int}}
scoreboard_message_id = None

# --- OAuth Roblox ---
oauth_states  = {}       # {state: discord_user_id} — temporaire pendant le flux OAuth
roblox_links  = {}       # {discord_user_id: {"roblox_id": str, "roblox_username": str}}

# --- TempBan / TempMute ---
tempban_data  = {}       # {"guild_id:user_id": {user_id, guild_id, end_time, reason, moderator_id, username}}
tempmute_data = {}       # même structure

# --- Bans classiques (remplace bans.json — persistance Discord dans BAN_LOG_CHANNEL_ID) ---
bans_data = {}            # {"guild_id:user_id": {user_id, guild_id, reason, end_time, moderator}}

# --- Giveaways (remplace giveaways.json — persistance Discord dans GIVEAWAY_MEMORY_CHANNEL_ID) ---
giveaway_data = {}        # {message_id: {channel_id, prize, condition, winners_count, end_time, participants, ended}}

# --- Système d'invitations ---
invite_cache = {}             # {guild_id: {code: {"uses": int, "inviter_id": int|None}, "__vanity__": {...}}} — en mémoire, reconstruit à chaque démarrage
recently_deleted_invites = {} # {guild_id: {code: {"inviter_id": int, "deleted_at": float}}} — filet de sécurité anti-course (10-15s)
invite_data = {}              # {"balances": {inviter_id: {"count","balance","total_earned"}}, "cashouts": {request_id: {...}}, "invited_by": {invited_id: inviter_id}}
already_invited_ids = set()   # IDs (str) déjà comptés comme invités une fois — jamais retirés (anti leave/rejoin farming)

# --- Système de warns / big warns ---
warn_data = {}   # {"guild_id:user_id": {"warns": int, "last_warn_at": float, "big_warns": int, "last_bigwarn_at": float, "history": [...]}}

# --- Commandes admin/modo à tracer automatiquement ---
LOGGED_ADMIN_COMMANDS = {
    'kill', 'setcountchannel', 'setscore', 'lock', 'unlock', 'restore',
    'giveaway', 'msgdel', 'ban', 'tempban', 'pardon', 'kick', 'mute',
    'tempmute', 'unmute', 'safe', 'removesafe', 'TicketCreatingChannel',
    'SetTableChannel', 'AddTableLine', 'SetTableValue', 'RemoveTableValue',
    'GetTableUserValue', 'RemoveTopBoardRobux', 'backup', 'COMMANDSON',
    'setuprobloxverify', 'cashout', 'AdjustInviteBalance', 'ResetInviteFlag',
    'warn', 'bigwarn', 'unwarn', 'unbigwarn'
}

# --- Salons "mémoire" du bot : jamais loggés dans messages-log (ni suppression, ni édition) ---
MEMORY_CHANNELS = {
    DB_CHANNEL_ID, XP_MEMORY_CHANNEL_ID, DONATION_MEMORY_CHANNEL_ID,
    TICKET_MEMORY_CHANNEL_ID, TABLE_LOG_CHANNEL_ID, ROBLOX_LINKS_CHANNEL_ID,
    ROLE_BACKUP_CHANNEL_ID, TEMPBAN_LOG_CHANNEL_ID, TEMPMUTE_LOG_CHANNEL_ID,
    BAN_LOG_CHANNEL_ID, GIVEAWAY_MEMORY_CHANNEL_ID,
    MESSAGES_LOG_CHANNEL_ID, MEMBER_LOG_CHANNEL_ID,
    ADMIN_ACTIONS_LOG_CHANNEL_ID, VERIF_HISTORY_LOG_CHANNEL_ID,
    INVITE_ARRIVAL_CHANNEL_ID, INVITE_DEPART_CHANNEL_ID, INVITE_CASHOUT_CHANNEL_ID,
    INVITE_DATA_CHANNEL_ID, ALREADY_INVITED_CHANNEL_ID, WARN_LOG_CHANNEL_ID,
}
# ==========================================

# ==========================================
# HELPERS — DURÉE
# ==========================================

def parse_duration(duration_str: str):
    """
    Parse une durée comme 10m, 2h, 3d.
    Retourne le nombre de secondes ou None si invalide.
    """
    match = re.fullmatch(r'(\d+)([mhd])', duration_str.lower().strip())
    if not match:
        return None
    value = int(match.group(1))
    unit  = match.group(2)
    if value <= 0:
        return None
    if unit == 'm':
        return value * 60
    if unit == 'h':
        return value * 3600
    if unit == 'd':
        return value * 86400
    return None


def format_duration(seconds: int) -> str:
    """Formate un nombre de secondes en chaîne lisible (ex: 2h30m, 1d12h)."""
    seconds = int(seconds)
    days    = seconds // 86400
    hours   = (seconds % 86400) // 3600
    minutes = (seconds % 3600)  // 60

    parts = []
    if days:
        parts.append(f"{days}j")
    if hours:
        parts.append(f"{hours}h")
    if minutes and not days:          # on n'affiche pas les minutes si > 1 jour
        parts.append(f"{minutes}m")
    return "".join(parts) if parts else "< 1m"

# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Botixirya Status: OK"

@app.route('/donation', methods=['POST'])
def receive_donation():
    token = request.headers.get("X-Secret-Token", "")
    if token != DONATION_SECRET:
        return {"error": "Unauthorized"}, 401

    data = request.get_json()
    if not data:
        return {"error": "Invalid JSON"}, 400

    user_id = str(data.get("userId", ""))
    username = data.get("username", "Inconnu")
    amount = int(data.get("amount", 0))

    if not user_id or amount <= 0:
        return {"error": "Invalid data"}, 400

    if user_id not in donations_data:
        donations_data[user_id] = {"username": username, "total": 0}

    donations_data[user_id]["username"] = username
    donations_data[user_id]["total"] += amount

    asyncio.run_coroutine_threadsafe(save_donations_to_discord(), bot.loop)
    asyncio.run_coroutine_threadsafe(refresh_scoreboard(), bot.loop)

    return {"success": True, "total": donations_data[user_id]["total"]}, 200


async def notify_oauth_expired(user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await user.send(
            "⏱️ **Vérification Roblox expirée**\n"
            "Ta session a expiré (10 minutes dépassées).\n"
            "Retourne sur le serveur et clique à nouveau sur le bouton pour recommencer."
        )
    except:
        pass
@app.route('/roblox/callback')
def roblox_callback():
    import requests as req_lib
    code  = request.args.get("code", "")
    state = request.args.get("state", "")

    if not code or not state:
        return "<h2>❌ Paramètres manquants.</h2>", 400

    state_data = oauth_states.pop(state, None)
    if not state_data:
        return "<h2>❌ Session expirée ou invalide. Recommence depuis Discord.</h2>", 400
    if time.time() > state_data.get("expires_at", 0):
        asyncio.run_coroutine_threadsafe(notify_oauth_expired(state_data["user_id"]), bot.loop)
        return """<html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:white;">
        <h1>⏱️ Session expirée</h1>
        <p>Tu as mis plus de 10 minutes. Retourne sur Discord et recommence.</p>
        </body></html>""", 400
    discord_user_id = state_data["user_id"]

    try:
        token_resp = req_lib.post(
            "https://apis.roblox.com/oauth/v1/token",
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  ROBLOX_REDIRECT_URI,
                "client_id":     ROBLOX_CLIENT_ID,
                "client_secret": ROBLOX_CLIENT_SECRET,
            },
            timeout=10
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return "<h2>❌ Impossible d'obtenir le token Roblox.</h2>", 400
    except Exception as e:
        return f"<h2>❌ Erreur token : {e}</h2>", 500

    try:
        user_resp = req_lib.get(
            "https://apis.roblox.com/oauth/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        roblox_info = user_resp.json()
        roblox_id       = roblox_info.get("sub", "?")
        roblox_username = roblox_info.get("preferred_username", "Inconnu")
    except Exception as e:
        return f"<h2>❌ Erreur profil Roblox : {e}</h2>", 500

    asyncio.run_coroutine_threadsafe(
        assign_roblox_role(discord_user_id, roblox_id, roblox_username),
        bot.loop
    )

    return f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:white;">
    <h1>✅ Compte Roblox lié !</h1>
    <p>Bienvenue <strong>{roblox_username}</strong> !</p>
    <p>Retourne sur Discord pour continuer la vérification.</p>
    </body></html>
    """


async def save_roblox_links():
    chan = bot.get_channel(ROBLOX_LINKS_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(roblox_links, ensure_ascii=False)
    async for msg in chan.history(limit=20):
        if msg.content.startswith("ROBLOX_LINKS|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"ROBLOX_LINKS|{payload}")

async def load_roblox_links():
    global roblox_links
    chan = bot.get_channel(ROBLOX_LINKS_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=20):
        if msg.content.startswith("ROBLOX_LINKS|"):
            try:
                roblox_links = json.loads(msg.content[len("ROBLOX_LINKS|"):])
            except:
                roblox_links = {}
            break


async def assign_roblox_role(discord_user_id: int, roblox_id: str, roblox_username: str):
    global roblox_links

    for uid, data in roblox_links.items():
        if data.get("roblox_id") == roblox_id and int(uid) != discord_user_id:
            return

    for guild in bot.guilds:
        member = guild.get_member(discord_user_id)
        if not member:
            try:
                member = await guild.fetch_member(discord_user_id)
            except:
                continue

        linked_role     = guild.get_role(ROLE_ROBLOX_LINKED_ID)
        verified_role   = guild.get_role(ROLE_VERIFIED_ID)
        unverified_role = guild.get_role(ROLE_UNVERIFIED_ID)

        try:
            if verified_role:
                await member.add_roles(verified_role, reason="Vérification Roblox complète")
            if linked_role and linked_role in member.roles:
                await member.remove_roles(linked_role, reason="Vérification Roblox complète")
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason="Vérification Roblox complète")
        except Exception as e:
            await send_log(f"⚠️ Erreur attribution rôle Membre OAuth : {e}")
            return

        roblox_links[str(discord_user_id)] = {
            "roblox_id":       roblox_id,
            "roblox_username": roblox_username,
            "linked_at":       discord.utils.utcnow().strftime("%d/%m/%Y à %H:%M")
        }
        await save_roblox_links()

        # Log dans verif-history
        verif_chan = bot.get_channel(VERIF_HISTORY_LOG_CHANNEL_ID)
        if verif_chan:
            embed = discord.Embed(
                title="🎮 Compte Roblox lié — Vérification complète",
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Discord",        value=f"{member.mention} (`{discord_user_id}`)", inline=True)
            embed.add_field(name="Pseudo Discord", value=str(member),                               inline=True)
            embed.add_field(name="Roblox",         value=f"**{roblox_username}**",                  inline=True)
            embed.add_field(name="Roblox ID",      value=f"`{roblox_id}`",                          inline=True)
            embed.add_field(
                name="Profil Roblox",
                value=f"[Voir sur Roblox](https://www.roblox.com/users/{roblox_id}/profile)",
                inline=True
            )
            await verif_chan.send(embed=embed)

        try:
            await member.send(
                f"✅ **Compte Roblox lié avec succès !**\n"
                f"Roblox : **{roblox_username}**\n"
                f"Bienvenue dans notre communauté !"
            )
        except:
            pass
        break


def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True   # Nécessaire pour le compteur "membres en ligne" — doit AUSSI être activé
                            # dans le Discord Developer Portal (onglet Bot > Privileged Gateway Intents > Presence Intent)
intents.invites = True     # Nécessaire pour on_invite_create/on_invite_delete (système d'invitations). Non privilégié,
                            # rien à activer dans le portail — mais le bot doit avoir la permission "Gérer le serveur"
                            # pour pouvoir lire guild.invites().
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
bot.remove_command('help')

# --- Vérification globale : serveur backup ---
@bot.check
async def global_backup_check(ctx):
    if ctx.guild and ctx.guild.id == BACKUP_SERVER_ID:
        if ctx.command and ctx.command.name in ('backup', 'COMMANDSON'):
            return True
        return commands_on_backup
    return True

# ==========================================
# GESTION DES DONNÉES
# ==========================================

async def save_counting_to_db():
    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        await db_chan.send(f"BACKUP_COUNT|{current_count}|{last_user_id}|{active_counting_channel}")

async def send_log(content):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(content)

# ==========================================
# BANS — PERSISTANCE DISCORD
# ==========================================

async def save_bans_to_discord():
    chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(bans_data, ensure_ascii=False)
    async for msg in chan.history(limit=200):
        if msg.content.startswith("BANS_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"BANS_SAVE|{payload}")

async def load_bans_from_discord():
    global bans_data
    chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=200):
        if msg.content.startswith("BANS_SAVE|"):
            try:
                bans_data = json.loads(msg.content[len("BANS_SAVE|"):])
            except:
                bans_data = {}
            break

# ==========================================
# GIVEAWAY — PERSISTANCE DISCORD
# ==========================================

async def save_giveaways_to_discord():
    chan = bot.get_channel(GIVEAWAY_MEMORY_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(giveaway_data, ensure_ascii=False)
    async for msg in chan.history(limit=100):
        if msg.content.startswith("GIVEAWAY_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"GIVEAWAY_SAVE|{payload}")

async def load_giveaways_from_discord():
    global giveaway_data
    chan = bot.get_channel(GIVEAWAY_MEMORY_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=100):
        if msg.content.startswith("GIVEAWAY_SAVE|"):
            try:
                giveaway_data = json.loads(msg.content[len("GIVEAWAY_SAVE|"):])
            except:
                giveaway_data = {}
            break

# ==========================================
# HELPERS GÉNÉRIQUES — PERSISTANCE DISCORD (payload potentiellement volumineux)
# ==========================================
# Contrairement aux autres systèmes du bot (limités par les 2000 caractères d'un message Discord),
# ces helpers basculent automatiquement sur un fichier .json en pièce jointe si le payload est trop
# gros. Utilisé pour le système d'invitations, dont les données grandissent avec le temps.

async def save_json_to_channel(channel_id: int, marker: str, data, search_limit: int = 100):
    chan = bot.get_channel(channel_id)
    if not chan:
        return
    payload = json.dumps(data, ensure_ascii=False)

    async for msg in chan.history(limit=search_limit):
        if msg.content == marker or msg.content.startswith(marker):
            try:
                await msg.delete()
            except:
                pass
            break

    if len(payload) <= 1900:
        await chan.send(f"{marker}{payload}")
    else:
        file = discord.File(fp=io.BytesIO(payload.encode("utf-8")), filename="data.json")
        await chan.send(content=marker, file=file)

async def load_json_from_channel(channel_id: int, marker: str, default, search_limit: int = 100):
    chan = bot.get_channel(channel_id)
    if not chan:
        return default
    async for msg in chan.history(limit=search_limit):
        if msg.content == marker and msg.attachments:
            try:
                raw = await msg.attachments[0].read()
                return json.loads(raw.decode("utf-8"))
            except:
                return default
        if msg.content.startswith(marker):
            try:
                return json.loads(msg.content[len(marker):])
            except:
                return default
    return default

# ==========================================
# SYSTÈME D'INVITATIONS — PERSISTANCE DISCORD
# ==========================================

async def save_invite_data():
    await save_json_to_channel(INVITE_DATA_CHANNEL_ID, "INVITE_DATA|", invite_data, search_limit=200)

async def load_invite_data():
    global invite_data
    invite_data = await load_json_from_channel(
        INVITE_DATA_CHANNEL_ID, "INVITE_DATA|",
        {"balances": {}, "cashouts": {}, "invited_by": {}}, search_limit=200
    )
    invite_data.setdefault("balances", {})
    invite_data.setdefault("cashouts", {})
    invite_data.setdefault("invited_by", {})

async def save_already_invited():
    await save_json_to_channel(ALREADY_INVITED_CHANNEL_ID, "ALREADY_INVITED|", list(already_invited_ids), search_limit=200)

async def load_already_invited():
    global already_invited_ids
    ids = await load_json_from_channel(ALREADY_INVITED_CHANNEL_ID, "ALREADY_INVITED|", [], search_limit=200)
    already_invited_ids = set(str(i) for i in ids)

# ==========================================
# SYSTÈME D'INVITATIONS — SUIVI DES INVITATIONS
# ==========================================

async def refresh_invite_cache(guild):
    """À appeler au démarrage (on_ready) : construit l'instantané initial des invitations du serveur."""
    cache_entry = {}
    try:
        invites = await guild.invites()
        for inv in invites:
            cache_entry[inv.code] = {"uses": inv.uses, "inviter_id": inv.inviter.id if inv.inviter else None}
    except discord.Forbidden:
        await send_log(
            f"⚠️ **Invitations** : permission `Gérer le serveur` manquante sur **{guild.name}** — "
            f"le suivi des invitations ne fonctionnera pas sur ce serveur."
        )
    except Exception:
        pass

    try:
        vanity = await guild.vanity_invite()
        if vanity:
            cache_entry["__vanity__"] = {"uses": vanity.uses, "inviter_id": None}
    except Exception:
        pass

    invite_cache[guild.id] = cache_entry

async def find_inviter(guild):
    """
    Détermine l'ID de l'utilisateur qui vient d'inviter un nouveau membre, en comparant
    l'état des invitations juste avant/après son arrivée. Retourne None si indéterminable
    (ex : lien "Découverte" de Discord, invitation supprimée sans qu'on ait pu la relier).
    Limite connue : si deux invitations différentes sont utilisées à la même seconde,
    seule la première trouvée est retenue (cas très rare en pratique).
    """
    gid = guild.id
    old_snapshot = dict(invite_cache.get(gid, {}))
    try:
        new_invites = await guild.invites()
    except Exception:
        new_invites = []
    new_map = {inv.code: inv for inv in new_invites}

    inviter_id = None

    # Cas 1 : une invitation existante a un compteur d'utilisation plus élevé qu'avant
    for code, new_inv in new_map.items():
        old = old_snapshot.get(code)
        if old and new_inv.uses > old.get("uses", 0):
            inviter_id = new_inv.inviter.id if new_inv.inviter else None
            break

    # Cas 2 : une invitation à usage unique a disparu entre les deux instantanés
    if inviter_id is None:
        for code, old in old_snapshot.items():
            if code == "__vanity__":
                continue
            if code not in new_map:
                inviter_id = old.get("inviter_id")
                break

    # Cas 3 : filet de sécurité — suppression de l'invitation détectée par on_invite_delete
    # juste avant qu'on ait pu comparer nous-mêmes (course entre les deux événements)
    if inviter_id is None:
        recent = recently_deleted_invites.get(gid, {})
        now = time.time()
        for code, info in list(recent.items()):
            if now - info["deleted_at"] <= 15:
                inviter_id = info["inviter_id"]
                recent.pop(code, None)
                break

    # Mise à jour de l'instantané pour la prochaine arrivée
    new_cache = {inv.code: {"uses": inv.uses, "inviter_id": inv.inviter.id if inv.inviter else None} for inv in new_invites}
    try:
        vanity = await guild.vanity_invite()
        if vanity:
            new_cache["__vanity__"] = {"uses": vanity.uses, "inviter_id": None}
    except Exception:
        pass
    invite_cache[gid] = new_cache

    return inviter_id

# ==========================================
# SYSTÈME DE WARNS / BIG WARNS — PERSISTANCE DISCORD
# ==========================================

async def save_warn_data():
    await save_json_to_channel(WARN_LOG_CHANNEL_ID, "WARN_DATA|", warn_data, search_limit=200)

async def load_warn_data():
    global warn_data
    warn_data = await load_json_from_channel(WARN_LOG_CHANNEL_ID, "WARN_DATA|", {}, search_limit=200)

async def apply_bigwarn_sanction(member: discord.Member, big_warn_level: int, reason: str, moderator: discord.Member):
    """
    Applique la sanction correspondant au palier de big warn atteint (1, 2 ou 3),
    en s'appuyant sur les systèmes de tempmute/tempban déjà existants du bot.
    Retourne un texte descriptif de la sanction appliquée.
    """
    guild = member.guild
    key = f"{guild.id}:{member.id}"

    if big_warn_level == 1:
        seconds = 1 * 86400
        muted_role = guild.get_role(MUTED_ROLE_ID)
        verified_role = guild.get_role(ROLE_VERIFIED_ID)
        if muted_role:
            try:
                await member.add_roles(muted_role, reason=f"[Big Warn 1/3] {reason}")
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role, reason=f"[Big Warn 1/3] {reason}")
            except Exception:
                pass
        tempmute_data[key] = {
            "user_id": member.id, "guild_id": guild.id, "end_time": time.time() + seconds,
            "reason": f"Big Warn 1/3 : {reason}", "moderator_id": moderator.id, "username": str(member)
        }
        await save_tempmutes_to_discord()
        return "🔇 Mute temporaire de **1 jour** appliqué (Big Warn 1/3)."

    elif big_warn_level == 2:
        seconds = 3 * 86400
        muted_role = guild.get_role(MUTED_ROLE_ID)
        verified_role = guild.get_role(ROLE_VERIFIED_ID)
        if muted_role:
            try:
                await member.add_roles(muted_role, reason=f"[Big Warn 2/3] {reason}")
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role, reason=f"[Big Warn 2/3] {reason}")
            except Exception:
                pass
        tempmute_data[key] = {
            "user_id": member.id, "guild_id": guild.id, "end_time": time.time() + seconds,
            "reason": f"Big Warn 2/3 : {reason}", "moderator_id": moderator.id, "username": str(member)
        }
        await save_tempmutes_to_discord()
        return "🔇 Mute temporaire de **3 jours** appliqué (Big Warn 2/3)."

    elif big_warn_level >= 3:
        seconds = 31 * 86400
        try:
            await member.ban(reason=f"[Big Warn 3/3] {reason}")
        except Exception as e:
            return f"⚠️ Big Warn 3/3 atteint mais le ban a échoué : {e}"

        tempban_data[key] = {
            "user_id": member.id, "guild_id": guild.id, "end_time": time.time() + seconds,
            "reason": f"Big Warn 3/3 : {reason}", "moderator_id": moderator.id, "username": str(member)
        }
        await save_tempbans_to_discord()

        # Reset complet du cycle pour cet utilisateur — le cycle repart de zéro une fois qu'il revient
        entry = warn_data.get(key)
        if entry:
            entry["warns"] = 0
            entry["big_warns"] = 0
            await save_warn_data()

        return "🔨 **Ban temporaire de 31 jours** appliqué (Big Warn 3/3). Le cycle de warns a été réinitialisé."

    return None

@tasks.loop(hours=1)
async def check_warn_expiry():
    """Fait expirer les warns simples (30j sans avoir atteint 3) et les big warns (90j sans nouveau big warn)."""
    now = time.time()
    changed = False
    for key, entry in list(warn_data.items()):
        if entry.get("warns", 0) > 0 and now - entry.get("last_warn_at", 0) > WARN_SIMPLE_EXPIRY_DAYS * 86400:
            entry["warns"] = 0
            changed = True
        if 0 < entry.get("big_warns", 0) < 3 and now - entry.get("last_bigwarn_at", 0) > BIGWARN_EXPIRY_DAYS * 86400:
            entry["big_warns"] = 0
            changed = True
    if changed:
        await save_warn_data()

# ==========================================
# TEMPBAN — PERSISTANCE DISCORD
# ==========================================

async def save_tempbans_to_discord():
    chan = bot.get_channel(TEMPBAN_LOG_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(tempban_data, ensure_ascii=False)
    async for msg in chan.history(limit=100):
        if msg.content.startswith("TEMPBAN_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"TEMPBAN_SAVE|{payload}")

async def load_tempbans_from_discord():
    global tempban_data
    chan = bot.get_channel(TEMPBAN_LOG_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=100):
        if msg.content.startswith("TEMPBAN_SAVE|"):
            try:
                tempban_data = json.loads(msg.content[len("TEMPBAN_SAVE|"):])
            except:
                tempban_data = {}
            break

# ==========================================
# TEMPMUTE — PERSISTANCE DISCORD
# ==========================================

async def save_tempmutes_to_discord():
    chan = bot.get_channel(TEMPMUTE_LOG_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(tempmute_data, ensure_ascii=False)
    async for msg in chan.history(limit=100):
        if msg.content.startswith("TEMPMUTE_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"TEMPMUTE_SAVE|{payload}")

async def load_tempmutes_from_discord():
    global tempmute_data
    chan = bot.get_channel(TEMPMUTE_LOG_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=100):
        if msg.content.startswith("TEMPMUTE_SAVE|"):
            try:
                tempmute_data = json.loads(msg.content[len("TEMPMUTE_SAVE|"):])
            except:
                tempmute_data = {}
            break

# ==========================================
# SYSTÈME DE TICKETS — MÉMOIRE
# ==========================================

async def save_ticket_config(config: dict):
    mem_chan = bot.get_channel(TICKET_MEMORY_CHANNEL_ID)
    if not mem_chan:
        return
    async for msg in mem_chan.history(limit=200):
        if msg.content.startswith("TICKET_CONFIG|"):
            try:
                old = json.loads(msg.content[len("TICKET_CONFIG|"):])
                if old.get("ticket_id") == config["ticket_id"]:
                    await msg.delete()
                    break
            except:
                pass
    await mem_chan.send(f"TICKET_CONFIG|{json.dumps(config, ensure_ascii=False)}")

async def load_ticket_configs():
    global ticket_configs
    mem_chan = bot.get_channel(TICKET_MEMORY_CHANNEL_ID)
    if not mem_chan:
        return
    async for msg in mem_chan.history(limit=200):
        if msg.content.startswith("TICKET_CONFIG|"):
            try:
                config = json.loads(msg.content[len("TICKET_CONFIG|"):])
                tid = config["ticket_id"]
                ticket_configs[tid] = config
            except:
                pass

# ==========================================
# SYSTÈME DE TABLEAU DE RÉMUNÉRATION
# ==========================================

async def save_table_to_log():
    log_chan = bot.get_channel(TABLE_LOG_CHANNEL_ID)
    if not log_chan:
        return
    payload = {
        "table_channel_id": table_channel_id,
        "table_message_id": table_message_id,
        "data": table_data
    }
    async for msg in log_chan.history(limit=50):
        if msg.content.startswith("TABLE_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await log_chan.send(f"TABLE_SAVE|{json.dumps(payload, ensure_ascii=False)}")

async def load_table_from_log():
    global table_data, table_channel_id, table_message_id
    log_chan = bot.get_channel(TABLE_LOG_CHANNEL_ID)
    if not log_chan:
        return
    async for msg in log_chan.history(limit=50):
        if msg.content.startswith("TABLE_SAVE|"):
            try:
                payload = json.loads(msg.content[len("TABLE_SAVE|"):])
                table_channel_id = payload.get("table_channel_id")
                table_message_id = payload.get("table_message_id")
                table_data = payload.get("data", {})
            except:
                pass
            break

def render_table(guild) -> str:
    if not table_data:
        return "```\nAucune entrée dans le tableau.\n```"

    rows = []
    for uid, entry in table_data.items():
        member = guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"
        rows.append([
            name,
            entry.get("profession", "—"),
            str(entry.get("value", 0)),
            str(entry.get("total_value", 0)),
            entry.get("last_modified", "—")
        ])

    headers = ["Utilisateur", "Profession", "Valeur", "Total", "Dernière màj"]
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def make_row(cells):
        return "│ " + " │ ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells)) + " │"

    def make_sep(left, mid, right, fill="─"):
        return left + (fill * (col_widths[0] + 2)) + "".join(
            mid + (fill * (w + 2)) for w in col_widths[1:]
        ) + right

    lines = []
    lines.append(make_sep("┌", "┬", "┐"))
    lines.append(make_row(headers))
    lines.append(make_sep("├", "┼", "┤"))
    for row in rows:
        lines.append(make_row(row))
    lines.append(make_sep("└", "┴", "┘"))

    return "```\n" + "\n".join(lines) + "\n```"

# ==========================================
# SYSTÈME D'XP / NIVEAUX
# ==========================================

def save_xp():
    pass

async def save_xp_to_discord():
    chan = bot.get_channel(XP_MEMORY_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(xp_data, ensure_ascii=False)
    async for msg in chan.history(limit=20):
        if msg.content.startswith("XP_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"XP_SAVE|{payload}")

def load_xp():
    global xp_data
    xp_data = {}

async def load_xp_from_discord():
    global xp_data
    chan = bot.get_channel(XP_MEMORY_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=20):
        if msg.content.startswith("XP_SAVE|"):
            try:
                xp_data = json.loads(msg.content[len("XP_SAVE|"):])
            except:
                xp_data = {}
            break

def get_level(xp: int) -> int:
    return int(math.sqrt(xp / 100))

def xp_for_level(level: int) -> int:
    return level * level * 100

def xp_progress(xp: int):
    level = get_level(xp)
    current_floor = xp_for_level(level)
    next_floor = xp_for_level(level + 1)
    return level, xp - current_floor, next_floor - current_floor

async def check_level_up(guild, member, old_level: int, new_level: int):
    if new_level <= old_level:
        return

    awarded = []
    for lvl_threshold, role_id in LEVEL_ROLES.items():
        if old_level < lvl_threshold <= new_level:
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Niveau {lvl_threshold} atteint")
                    awarded.append((lvl_threshold, role))
                except:
                    pass

    if awarded:
        chan = bot.get_channel(LEVEL_UP_CHANNEL_ID)
        if chan:
            for lvl_threshold, role in awarded:
                await chan.send(
                    f"🎉 {member.mention} a atteint le **niveau {lvl_threshold}** "
                    f"et obtient le rôle {role.mention} !"
                )

async def refresh_table_message(guild):
    global table_message_id
    if not table_channel_id:
        return
    chan = bot.get_channel(table_channel_id)
    if not chan:
        return

    embed = discord.Embed(
        title="💰 Tableau de rémunération",
        description=render_table(guild),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Mis à jour le {discord.utils.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC")

    if table_message_id:
        try:
            msg = await chan.fetch_message(table_message_id)
            await msg.edit(embed=embed)
            return
        except:
            pass

    msg = await chan.send(embed=embed)
    table_message_id = msg.id
    await save_table_to_log()

# ==========================================
# SYSTÈME DE DONATIONS ROBLOX
# ==========================================

async def save_donations_to_discord():
    chan = bot.get_channel(DONATION_MEMORY_CHANNEL_ID)
    if not chan:
        return
    payload = json.dumps(donations_data, ensure_ascii=False)
    async for msg in chan.history(limit=20):
        if msg.content.startswith("DONATION_SAVE|"):
            try:
                await msg.delete()
            except:
                pass
            break
    await chan.send(f"DONATION_SAVE|{payload}")

async def load_donations_from_discord():
    global donations_data
    chan = bot.get_channel(DONATION_MEMORY_CHANNEL_ID)
    if not chan:
        return
    async for msg in chan.history(limit=20):
        if msg.content.startswith("DONATION_SAVE|"):
            try:
                donations_data = json.loads(msg.content[len("DONATION_SAVE|"):])
            except:
                donations_data = {}
            break

def build_scoreboard_embed():
    sorted_donors = sorted(
        donations_data.items(),
        key=lambda x: x[1].get("total", 0),
        reverse=True
    )

    p1 = sorted_donors[0] if len(sorted_donors) > 0 else None
    p2 = sorted_donors[1] if len(sorted_donors) > 1 else None
    p3 = sorted_donors[2] if len(sorted_donors) > 2 else None

    def fmt_podium(entry):
        if not entry:
            return "*Personne*\n—"
        total = f"{entry.get('total', 0):,}".replace(",", " ")
        return f"**{entry.get('username', '???')}**\n💰 {total} Robux"

    embed = discord.Embed(color=discord.Color.gold())
    embed.description = (
        "```\n"
        "╔══════════════════════════════════════╗\n"
        "║     🏆  TOPBOARD DES DONATIONS  🏆    ║\n"
        "║           Aavixyria Donations          ║\n"
        "╚══════════════════════════════════════╝\n"
        "```"
    )

    embed.add_field(name="🥈 2ème Place", value=fmt_podium(p2[1] if p2 else None), inline=True)
    embed.add_field(name="🥇 1ère Place", value=fmt_podium(p1[1] if p1 else None), inline=True)
    embed.add_field(name="🥉 3ème Place", value=fmt_podium(p3[1] if p3 else None), inline=True)
    embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

    if len(sorted_donors) > 3:
        lines = []
        for i, (uid, entry) in enumerate(sorted_donors[3:15], start=4):
            total = f"{entry.get('total', 0):,}".replace(",", " ")
            lines.append(f"> `#{i}` ┊ **{entry.get('username', uid)}** — 💰 {total} Robux")
        embed.add_field(name="🎖️ Autres donateurs", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="🎖️ Autres donateurs", value="> *Aucun autre donateur pour le moment.*", inline=False)

    embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    embed.set_footer(text="💝  Merci énormément pour vos donations  💝")
    return embed


async def refresh_scoreboard():
    global scoreboard_message_id
    chan = bot.get_channel(DONATION_SCOREBOARD_CHANNEL_ID)
    if not chan:
        return

    embed = build_scoreboard_embed()

    if scoreboard_message_id:
        try:
            msg = await chan.fetch_message(scoreboard_message_id)
            await msg.edit(embed=embed)
            return
        except:
            pass

    msg = await chan.send(embed=embed)
    scoreboard_message_id = msg.id

# ==========================================
# ANTI-RAID
# ==========================================

async def quarantine_user(guild, member, silent: bool = False):
    if member.id == OWNER_ID:
        return

    user_id = str(member.id)
    roles_avant = [r.id for r in member.roles if r != guild.default_role]
    quarantined_users[user_id] = roles_avant

    role_backup_chan = bot.get_channel(ROLE_BACKUP_CHANNEL_ID)
    if role_backup_chan:
        roles_str = ",".join(str(r) for r in roles_avant) if roles_avant else "aucun"
        embed = discord.Embed(
            title="💾 Sauvegarde de rôles",
            color=discord.Color.orange() if not silent else discord.Color.red(),
            description=(
                f"**Utilisateur** : {member.mention} (`{member.id}`)\n"
                f"**Rôles sauvegardés** : {len(roles_avant)}\n"
                f"**Raison** : {'Mise en quarantaine manuelle' if silent else 'Anti-raid automatique'}"
            )
        )
        await role_backup_chan.send(
            content=f"ROLE_BACKUP|{guild.id}|{member.id}|{roles_str}",
            embed=embed,
            view=RestoreRolesView(guild.id, member.id)
        )

    raider_role = guild.get_role(RAIDER_ROLE_ID)
    try:
        new_roles = [raider_role] if raider_role else []
        await member.edit(roles=new_roles, reason="Quarantaine" if silent else "Anti-Raid : suppressions en masse détectées")
    except:
        pass

    for channel in guild.channels:
        try:
            await channel.set_permissions(
                member,
                send_messages=False,
                read_messages=False,
                manage_channels=False,
                manage_roles=False,
                reason="Quarantaine manuelle" if silent else "Anti-Raid"
            )
        except:
            pass

    if not silent:
        tag = "🤖 **BOT**" if member.bot else "👤 **Utilisateur**"
        raid_log_chan = bot.get_channel(RAID_LOG_CHANNEL_ID)
        if raid_log_chan:
            await raid_log_chan.send(
                f"🚨 **TENTATIVE DE RAID DÉTECTÉE**\n"
                f"{tag} : {member.mention} (`{member.id}`)\n"
                f"Rôles retirés : {len(roles_avant)}\n"
                f"Accès à tous les salons révoqué.\n"
                f"Utilisez le bouton dans <#{ROLE_BACKUP_CHANNEL_ID}> pour restaurer les rôles."
            )
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(
                f"🚨 **ANTI-RAID** : {member.mention} (`{member.id}`) mis en quarantaine ({tag})."
            )
    else:
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(
                f"🔒 **Quarantaine manuelle** : {member.mention} (`{member.id}`) — rôles retirés, accès révoqué."
            )

async def track_deletion(guild, user, dtype):
    if user.id == OWNER_ID or user.id in safe_users:
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
        deletion_tracker[gid][uid] = {"channels": [], "roles": []}
        member = guild.get_member(user.id)
        if member:
            await quarantine_user(guild, member)

# ==========================================
# VIEWS — RESTAURATION DE RÔLES (anti-raid)
# ==========================================

class RestoreRolesView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=None)
        btn = discord.ui.Button(
            label="🔓 Restaurer les rôles",
            style=discord.ButtonStyle.success,
            custom_id=f"restore_roles:{guild_id}:{user_id}"
        )
        btn.callback = self.restore_callback
        self.add_item(btn)

    async def restore_callback(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Réservé au propriétaire.", ephemeral=True)

        custom_id = interaction.data["custom_id"]
        parts = custom_id.split(":")
        if len(parts) < 3:
            return await interaction.response.send_message("❌ Données invalides.", ephemeral=True)

        guild_id = int(parts[1])
        user_id = int(parts[2])
        guild = bot.get_guild(guild_id)
        if not guild:
            return await interaction.response.send_message("❌ Serveur introuvable.", ephemeral=True)

        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except:
                return await interaction.response.send_message(
                    "❌ Membre introuvable (il a peut-être quitté le serveur).", ephemeral=True
                )

        found_roles = []
        msg_content = interaction.message.content or ""
        if msg_content.startswith("ROLE_BACKUP|"):
            p = msg_content.strip().split("|")
            if len(p) >= 4 and p[3] and p[3] != "aucun":
                for rid in p[3].split(","):
                    rid = rid.strip()
                    if rid.isdigit():
                        role = guild.get_role(int(rid))
                        if role:
                            found_roles.append(role)

        if not found_roles:
            for rid in quarantined_users.get(str(user_id), []):
                role = guild.get_role(rid)
                if role:
                    found_roles.append(role)

        try:
            await member.edit(roles=found_roles, reason=f"Restauration par {interaction.user}")
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erreur restauration rôles : {e}", ephemeral=True)

        for channel in guild.channels:
            try:
                overwrite = channel.overwrites_for(member)
                if overwrite.send_messages is False or overwrite.read_messages is False:
                    await channel.set_permissions(member, overwrite=None)
            except:
                pass

        quarantined_users.pop(str(user_id), None)

        raid_log_chan = bot.get_channel(RAID_LOG_CHANNEL_ID)
        if raid_log_chan:
            roles_names = ", ".join(r.name for r in found_roles) or "aucun"
            await raid_log_chan.send(
                f"✅ **Rôles restaurés** : {member.mention} (`{member.id}`)\n"
                f"Par : {interaction.user.mention}\n"
                f"Rôles : {roles_names}"
            )

        try:
            await interaction.message.edit(view=None)
        except:
            pass

        await interaction.response.send_message(
            f"✅ Rôles restaurés pour {member.mention} ({len(found_roles)} rôle(s)).",
            ephemeral=True
        )

# ==========================================
# VIEWS — VÉRIFICATION & GIVEAWAY
# ==========================================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="J'ai lu le règlement ✅", style=discord.ButtonStyle.success, custom_id="verify_user")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        linked_role     = interaction.guild.get_role(ROLE_ROBLOX_LINKED_ID)
        verified_role   = interaction.guild.get_role(ROLE_VERIFIED_ID)
        unverified_role = interaction.guild.get_role(ROLE_UNVERIFIED_ID)

        if verified_role and verified_role in interaction.user.roles:
            return await interaction.response.send_message(
                "✅ Tu es déjà membre du serveur !", ephemeral=True
            )
        if linked_role and linked_role in interaction.user.roles:
            return await interaction.response.send_message(
                "🎮 Tu es déjà en cours de vérification Roblox !\nRends-toi dans le salon de vérification.", ephemeral=True
            )

        try:
            if linked_role:
                await interaction.user.add_roles(linked_role, reason="Règlement accepté")
            if unverified_role and unverified_role in interaction.user.roles:
                await interaction.user.remove_roles(unverified_role, reason="Règlement accepté")
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

        # Log dans verif-history
        verif_chan = bot.get_channel(VERIF_HISTORY_LOG_CHANNEL_ID)
        if verif_chan:
            embed = discord.Embed(
                title="📋 Règlement accepté",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="Utilisateur", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            embed.add_field(name="Pseudo",      value=str(interaction.user),                                   inline=True)
            await verif_chan.send(embed=embed)

        await interaction.response.send_message(
            "✅ Règlement accepté ! Rends-toi maintenant dans le salon de vérification pour lier ton compte Roblox.",
            ephemeral=True
        )


class RobloxVerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lier mon compte Roblox 🎮", style=discord.ButtonStyle.blurple, custom_id="roblox_link_btn")
    async def roblox_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        linked_role   = interaction.guild.get_role(ROLE_ROBLOX_LINKED_ID)
        verified_role = interaction.guild.get_role(ROLE_VERIFIED_ID)

        if verified_role and verified_role in interaction.user.roles:
            return await interaction.response.send_message(
                "✅ Ton compte Roblox est déjà lié, tu es membre !", ephemeral=True
            )
        if linked_role and linked_role not in interaction.user.roles:
            return await interaction.response.send_message(
                "❌ Tu dois d'abord lire et accepter le règlement.", ephemeral=True
            )

        state = str(uuid.uuid4())
        oauth_states[state] = {
            "user_id":    interaction.user.id,
            "expires_at": time.time() + 600
        }

        oauth_url = (
            f"https://apis.roblox.com/oauth/v1/authorize"
            f"?client_id={ROBLOX_CLIENT_ID}"
            f"&redirect_uri={ROBLOX_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=openid+profile"
            f"&state={state}"
        )

        embed = discord.Embed(
            title="🔗 Liaison compte Roblox",
            description=(
                "Clique sur le bouton ci-dessous pour lier ton compte Roblox.\n\n"
                "Tu seras redirigé vers Roblox pour autoriser la connexion.\n"
                "Une fois terminé, reviens sur Discord !"
            ),
            color=discord.Color.blurple()
        )
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(
            label="Connecter avec Roblox",
            url=oauth_url,
            style=discord.ButtonStyle.link,
            emoji="🎮"
        ))
        await interaction.response.send_message(embed=embed, view=link_view, ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Participer ! 🎉", style=discord.ButtonStyle.blurple, custom_id="join_gw")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw_id = str(interaction.message.id)
        if gw_id not in giveaway_data or giveaway_data[gw_id]['ended']:
            return await interaction.response.send_message("Terminé.", ephemeral=True)
        if interaction.user.id in giveaway_data[gw_id]['participants']:
            return await interaction.response.send_message("Déjà inscrit !", ephemeral=True)
        giveaway_data[gw_id]['participants'].append(interaction.user.id)
        await save_giveaways_to_discord()
        await interaction.response.send_message("Inscrit !", ephemeral=True)

    @discord.ui.button(label="Reroll 🎲", style=discord.ButtonStyle.gray, custom_id="reroll_gw")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return
        gw_id = str(interaction.message.id)
        if gw_id in giveaway_data and giveaway_data[gw_id]['participants']:
            winner = random.choice(giveaway_data[gw_id]['participants'])
            await interaction.channel.send(f"🎲 Nouveau gagnant : <@{winner}>")
            await interaction.response.send_message("Fait.", ephemeral=True)

    @discord.ui.button(label="Annuler ❌", style=discord.ButtonStyle.danger, custom_id="delete_gw")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return
        gw_id = str(interaction.message.id)
        giveaway_data.pop(gw_id, None)
        await save_giveaways_to_discord()
        await interaction.message.delete()

class ConfirmPaymentView(discord.ui.View):
    """Bouton de confirmation de paiement pour une demande de cashout d'invitations.
    Le message n'est jamais supprimé : il est simplement modifié pour conserver un log permanent."""

    def __init__(self, request_id: str):
        super().__init__(timeout=None)
        btn = discord.ui.Button(
            label="✅ Confirmer le paiement",
            style=discord.ButtonStyle.success,
            custom_id=f"confirm_payment:{request_id}"
        )
        btn.callback = self.confirm_callback
        self.add_item(btn)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Réservé au propriétaire.", ephemeral=True)

        request_id = interaction.data["custom_id"].split(":", 1)[1]
        cashouts = invite_data.setdefault("cashouts", {})
        record = cashouts.get(request_id)
        if not record:
            return await interaction.response.send_message("❌ Demande de cashout introuvable.", ephemeral=True)
        if record.get("status") == "paid":
            return await interaction.response.send_message("ℹ️ Ce paiement a déjà été confirmé.", ephemeral=True)

        paid_at = discord.utils.utcnow().strftime("%d/%m/%Y à %H:%M UTC")
        record["status"] = "paid"
        record["paid_by"] = interaction.user.id
        record["paid_at"] = paid_at
        await save_invite_data()

        embed = interaction.message.embeds[0]
        status_text = f"✅ Payé le {paid_at} par {interaction.user.mention}"
        field_names = [f.name for f in embed.fields]
        if "Statut" in field_names:
            embed.set_field_at(field_names.index("Statut"), name="Statut", value=status_text, inline=False)
        else:
            embed.add_field(name="Statut", value=status_text, inline=False)
        embed.color = discord.Color.green()

        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Paiement confirmé et journalisé.", ephemeral=True)

# ==========================================
# VIEWS — TICKETS
# ==========================================

class TicketCreateView(discord.ui.View):
    def __init__(self, ticket_id: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        btn = discord.ui.Button(
            label="🎫 Create Ticket",
            style=discord.ButtonStyle.blurple,
            custom_id=f"create_ticket:{ticket_id}"
        )
        btn.callback = self.create_ticket_callback
        self.add_item(btn)

    async def create_ticket_callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        ticket_id = interaction.data["custom_id"].split(":", 1)[1]
        config = ticket_configs.get(ticket_id)
        if not config:
            return await interaction.response.send_message(
                "❌ Configuration du ticket introuvable.", ephemeral=True
            )

        ticket_channel_name = f"ticket-{ticket_id[:8]}-{user.name.lower().replace(' ', '-')}"
        existing = discord.utils.get(guild.text_channels, name=ticket_channel_name)
        if existing:
            return await interaction.response.send_message(
                f"❌ Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True
            )

        category = guild.get_channel(config["category_id"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"TICKET|{user.id}|{config['logs_channel_id']}",
                reason=f"Ticket créé par {user}"
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erreur création ticket : {e}", ephemeral=True)

        embed = discord.Embed(
            description=config["inside_ticket_message"],
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Ticket #{ticket_id[:8]} — {user.display_name}")
        await ticket_channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {ticket_channel.mention}", ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        topic = channel.topic or ""
        ticket_owner_id = None
        logs_channel_id = None

        if topic.startswith("TICKET|"):
            parts = topic.split("|")
            if len(parts) >= 3:
                try:
                    ticket_owner_id = int(parts[1])
                    logs_channel_id = int(parts[2])
                except:
                    pass

        is_admin = user.guild_permissions.administrator
        is_owner = user.id == OWNER_ID
        is_creator = user.id == ticket_owner_id

        if not (is_admin or is_owner or is_creator):
            return await interaction.response.send_message(
                "❌ Tu n'as pas la permission de fermer ce ticket.", ephemeral=True
            )

        await interaction.response.send_message("🔒 Fermeture du ticket en cours...")

        messages = []
        async for msg in channel.history(limit=500, oldest_first=True):
            if msg.author == guild.me and msg.components:
                continue
            if msg.content:
                messages.append(f"{msg.author.display_name}:\n{msg.content}\n")

        log_content = "\n".join(messages) if messages else "(aucun message)"

        if logs_channel_id:
            logs_chan = bot.get_channel(logs_channel_id)
            if logs_chan:
                txt_bytes = log_content.encode("utf-8")
                txt_file = discord.File(
                    fp=io.BytesIO(txt_bytes),
                    filename=f"ticket-{channel.name}-{int(time.time())}.txt"
                )
                ticket_owner_mention = f"<@{ticket_owner_id}>" if ticket_owner_id else channel.name
                await logs_chan.send(
                    content=(
                        f"📁 **Ticket fermé** — ticket de {ticket_owner_mention}\n"
                        f"Fermé par : {user.mention}\n"
                        f"Voici les logs de la conversation :"
                    ),
                    file=txt_file
                )

        await asyncio.sleep(3)
        try:
            await channel.delete(reason=f"Ticket fermé par {user}")
        except:
            pass

# ==========================================
# TÂCHES PÉRIODIQUES
# ==========================================

@tasks.loop(seconds=30)
async def check_giveaways():
    now = time.time()
    changed = False
    for msg_id, gw in list(giveaway_data.items()):
        if not gw['ended'] and now >= gw['end_time']:
            gw['ended'] = True
            changed = True
            channel = bot.get_channel(gw['channel_id'])
            if not channel:
                continue
            participants = gw.get('participants', [])
            winners_count = gw.get('winners_count', 1)
            if not participants:
                try:
                    await channel.send("🎉 Le giveaway est terminé mais **personne n'a participé** !")
                except:
                    pass
                continue
            winners = random.sample(participants, min(winners_count, len(participants)))
            winners_mentions = ", ".join(f"<@{w}>" for w in winners)
            try:
                embed = discord.Embed(title="🎉 Giveaway terminé !", color=discord.Color.gold())
                embed.add_field(name="Prix",       value=gw['prize'],       inline=True)
                embed.add_field(name="Gagnant(s)", value=winners_mentions,  inline=False)
                await channel.send(content=f"🎊 Félicitations {winners_mentions} !", embed=embed)
            except:
                pass
    if changed:
        await save_giveaways_to_discord()

@tasks.loop(seconds=60)
async def check_bans():
    now = time.time()
    to_remove = []

    for key, ban_data in list(bans_data.items()):
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

    if to_remove:
        for key in to_remove:
            bans_data.pop(key, None)
        await save_bans_to_discord()

@tasks.loop(seconds=30)
async def check_tempbans():
    """Vérifie les tempbans expirés et débannit automatiquement."""
    now = time.time()
    to_remove = []

    for key, info in list(tempban_data.items()):
        if now >= info["end_time"]:
            guild = bot.get_guild(info["guild_id"])
            if guild:
                try:
                    user = await bot.fetch_user(info["user_id"])
                    await guild.unban(user, reason="TempBan expiré — unban automatique")

                    log_chan = bot.get_channel(TEMPBAN_LOG_CHANNEL_ID)
                    if log_chan:
                        from datetime import datetime, timezone
                        embed = discord.Embed(
                            title="⏱️ TempBan expiré — Unban automatique",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="Utilisateur",
                            value=f"{info.get('username', str(user))} (`{user.id}`)",
                            inline=True
                        )
                        embed.add_field(
                            name="Raison initiale",
                            value=info.get("reason", "—"),
                            inline=True
                        )
                        embed.add_field(
                            name="Banni par",
                            value=f"<@{info.get('moderator_id', 0)}>",
                            inline=True
                        )
                        embed.set_footer(
                            text=f"Unban automatique — {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC"
                        )
                        await log_chan.send(embed=embed)
                except Exception:
                    pass
            to_remove.append(key)

    if to_remove:
        for key in to_remove:
            tempban_data.pop(key, None)
        await save_tempbans_to_discord()

@tasks.loop(seconds=30)
async def check_tempmutes():
    """Vérifie les tempmutes expirés et unmute automatiquement."""
    now = time.time()
    to_remove = []

    for key, info in list(tempmute_data.items()):
        if now >= info["end_time"]:
            guild = bot.get_guild(info["guild_id"])
            if guild:
                member = guild.get_member(info["user_id"])
                if not member:
                    try:
                        member = await guild.fetch_member(info["user_id"])
                    except Exception:
                        to_remove.append(key)
                        continue

                muted_role   = guild.get_role(MUTED_ROLE_ID)
                verified_role = guild.get_role(ROLE_VERIFIED_ID)

                try:
                    if muted_role and muted_role in member.roles:
                        await member.remove_roles(muted_role, reason="TempMute expiré — unmute automatique")
                    if verified_role and verified_role not in member.roles:
                        await member.add_roles(verified_role, reason="TempMute expiré — unmute automatique")

                    log_chan = bot.get_channel(TEMPMUTE_LOG_CHANNEL_ID)
                    if log_chan:
                        from datetime import datetime, timezone
                        embed = discord.Embed(
                            title="⏱️ TempMute expiré — Unmute automatique",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="Utilisateur",
                            value=f"{member.mention} (`{member.id}`)",
                            inline=True
                        )
                        embed.add_field(
                            name="Raison initiale",
                            value=info.get("reason", "—"),
                            inline=True
                        )
                        embed.add_field(
                            name="Muté par",
                            value=f"<@{info.get('moderator_id', 0)}>",
                            inline=True
                        )
                        embed.set_footer(
                            text=f"Unmute automatique — {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC"
                        )
                        await log_chan.send(embed=embed)
                except Exception:
                    pass
            to_remove.append(key)

    if to_remove:
        for key in to_remove:
            tempmute_data.pop(key, None)
        await save_tempmutes_to_discord()
@tasks.loop(minutes=5)
async def cleanup_oauth_states():
    now = time.time()
    expired = [s for s, d in list(oauth_states.items()) if now > d.get("expires_at", 0)]
    for state in expired:
        data = oauth_states.pop(state, None)
        if data:
            await notify_oauth_expired(data["user_id"])

@tasks.loop(minutes=20)
async def enforce_permissions():
    for guild in bot.guilds:
        unverified_role    = guild.get_role(ROLE_UNVERIFIED_ID)
        raider_role        = guild.get_role(RAIDER_ROLE_ID)
        muted_role         = guild.get_role(MUTED_ROLE_ID)
        roblox_linked_role = guild.get_role(ROLE_ROBLOX_LINKED_ID)

        for channel in guild.channels:
            channel_changed = False

            if unverified_role:
                is_unverified_exception = (
                    channel.id == PERM_UNVERIFIED_EXCEPTION_CHANNEL
                    or channel.id == PERM_UNVERIFIED_EXCEPTION_CATEGORY
                    or getattr(channel, 'category_id', None) == PERM_UNVERIFIED_EXCEPTION_CATEGORY
                )
                if channel.id == ROBLOX_VERIFY_CHANNEL_ID:
                    target_ow = channel.overwrites_for(unverified_role)
                    if target_ow.read_messages is not False:
                        try:
                            await channel.set_permissions(
                                unverified_role,
                                read_messages=False,
                                send_messages=False,
                                reason="enforce_permissions : unverified bloqué dans roblox-verify"
                            )
                            channel_changed = True
                        except:
                            pass
                elif is_unverified_exception:
                    target_ow = channel.overwrites_for(unverified_role)
                    if target_ow.read_messages is not True:
                        try:
                            await channel.set_permissions(
                                unverified_role,
                                read_messages=True,
                                send_messages=True,
                                reason="enforce_permissions : exception non-vérifié"
                            )
                            channel_changed = True
                        except:
                            pass
                else:
                    target_ow = channel.overwrites_for(unverified_role)
                    if target_ow.read_messages is not False:
                        try:
                            await channel.set_permissions(
                                unverified_role,
                                read_messages=False,
                                send_messages=False,
                                reason="enforce_permissions : non-vérifié bloqué"
                            )
                            channel_changed = True
                        except:
                            pass

            if raider_role:
                target_ow = channel.overwrites_for(raider_role)
                if target_ow.read_messages is not False:
                    try:
                        await channel.set_permissions(
                            raider_role,
                            read_messages=False,
                            send_messages=False,
                            reason="enforce_permissions : raider bloqué"
                        )
                        channel_changed = True
                    except:
                        pass

            if muted_role:
                target_ow = channel.overwrites_for(muted_role)
                if target_ow.send_messages is not False:
                    try:
                        await channel.set_permissions(
                            muted_role,
                            send_messages=False,
                            reason="enforce_permissions : muted bloqué"
                        )
                        channel_changed = True
                    except:
                        pass

            if roblox_linked_role:
                is_verify_channel = (channel.id == ROBLOX_VERIFY_CHANNEL_ID)
                if is_verify_channel:
                    target_ow = channel.overwrites_for(roblox_linked_role)
                    if target_ow.read_messages is not True:
                        try:
                            await channel.set_permissions(
                                roblox_linked_role,
                                read_messages=True,
                                send_messages=True,
                                reason="enforce_permissions : roblox-lié autorisé dans vérification"
                            )
                            channel_changed = True
                        except:
                            pass
                else:
                    target_ow = channel.overwrites_for(roblox_linked_role)
                    if target_ow.read_messages is not False:
                        try:
                            await channel.set_permissions(
                                roblox_linked_role,
                                read_messages=False,
                                send_messages=False,
                                reason="enforce_permissions : roblox-lié bloqué hors vérification"
                            )
                            channel_changed = True
                        except:
                            pass

            # Petite pause seulement si on a effectivement modifié ce salon, pour ménager les rate limits Discord
            if channel_changed:
                await asyncio.sleep(0.3)

        await asyncio.sleep(0.5)

@tasks.loop(minutes=10)
async def update_online_counter():
    """
    Renomme le salon vocal ONLINE_COUNTER_CHANNEL_ID avec le nombre de membres en ligne.
    Nécessite l'intent 'presences' activé ici ET dans le Discord Developer Portal.
    Intervalle de 10 minutes pour respecter la limite Discord de renommage des salons.
    """
    chan = bot.get_channel(ONLINE_COUNTER_CHANNEL_ID)
    if not chan:
        return
    guild = chan.guild
    online_count = sum(
        1 for m in guild.members
        if not m.bot and m.status != discord.Status.offline
    )
    new_name = f"🟢・En ligne : {online_count}"
    if chan.name != new_name:
        try:
            await chan.edit(name=new_name, reason="Botixirya : mise à jour du compteur en ligne")
        except Exception as e:
            await send_log(f"⚠️ **Compteur en ligne** : impossible de renommer le salon — `{e}`")

async def send_funds_error(msg: str):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"<@{OWNER_ID}> {msg}")

@tasks.loop(minutes=6)
async def update_roblox_funds():
    global funds_ugc_message_id, funds_clothing_message_id

    cookie = os.getenv("ROBLOX_COOKIE", "")
    if not cookie:
        await send_funds_error("⚠️ **Roblox Funds** : Variable d'environnement `ROBLOX_COOKIE` manquante.")
        return

    headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com"
    }

    groups = [
        (ROBLOX_GROUP_UGC,      FUNDS_UGC_CHANNEL_ID,      "Aavixyria UGC",      "funds_ugc_message_id"),
        (ROBLOX_GROUP_CLOTHING, FUNDS_CLOTHING_CHANNEL_ID, "Aavixyria Clothing", "funds_clothing_message_id"),
    ]

    async with aiohttp.ClientSession() as session:

        try:
            async with session.get(
                "https://users.roblox.com/v1/users/authenticated",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as auth_resp:
                if auth_resp.status == 401:
                    await send_funds_error(
                        "❌ **Roblox Funds** : Cookie invalide ou expiré (HTTP 401).\n"
                        "Renouvelez la variable `ROBLOX_COOKIE` dans Koyeb."
                    )
                    return
        except Exception as e:
            await send_funds_error(f"⚠️ **Roblox Funds** : Impossible de vérifier le cookie — `{e}`")
            return

        csrf_token = None
        try:
            async with session.post(
                "https://auth.roblox.com/v2/logout",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                csrf_token = resp.headers.get("x-csrf-token")
        except:
            pass

        if csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token

        for group_id, channel_id, label, msg_attr in groups:
            url = f"https://economy.roblox.com/v1/groups/{group_id}/currency"
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        robux = data.get("robux", 0)
                        new_name = f"💵·{label}: {robux:,} Robux".replace(",", " ")
                    elif resp.status == 401:
                        await send_funds_error(
                            f"⚠️ **Roblox Funds — {label}** : Cookie invalide ou expiré (HTTP 401)."
                        )
                        continue
                    elif resp.status == 403:
                        try:
                            body = await resp.json()
                            errors = body.get("errors", [])
                            detail = ", ".join(
                                f"code {e.get('code')} : {e.get('message')}" for e in errors
                            ) if errors else str(body)
                        except:
                            detail = await resp.text()
                        await send_funds_error(
                            f"⚠️ **Roblox Funds — {label}** : HTTP 403 — `{detail[:400]}`"
                        )
                        continue
                    else:
                        try:
                            body = await resp.text()
                        except:
                            body = "(corps illisible)"
                        await send_funds_error(
                            f"⚠️ **Roblox Funds — {label}** : HTTP `{resp.status}` — `{body[:200]}`"
                        )
                        continue
            except asyncio.TimeoutError:
                await send_funds_error(f"⚠️ **Roblox Funds — {label}** : Timeout.")
                continue
            except Exception as e:
                await send_funds_error(f"⚠️ **Roblox Funds — {label}** : Erreur — `{e}`")
                continue

            chan = bot.get_channel(channel_id)
            if not chan:
                await send_funds_error(f"⚠️ **Roblox Funds — {label}** : Salon `{channel_id}` introuvable.")
                continue
            try:
                await chan.edit(name=new_name, reason="Botixirya : mise à jour funds Roblox")
            except Exception as e:
                await send_funds_error(f"⚠️ **Roblox Funds — {label}** : Impossible de renommer — `{e}`")

# ==========================================
# ÉVÉNEMENTS
# ==========================================

@bot.event
async def on_ready():
    global current_count, last_user_id, active_counting_channel
    bot.add_view(GiveawayView(bot))
    bot.add_view(VerifyView())
    bot.add_view(RobloxVerifyView())
    bot.add_view(CloseTicketView())

    role_backup_chan = bot.get_channel(ROLE_BACKUP_CHANNEL_ID)
    if role_backup_chan:
        async for msg in role_backup_chan.history(limit=200):
            if msg.content.startswith("ROLE_BACKUP|"):
                parts = msg.content.split("|")
                if len(parts) >= 3:
                    try:
                        g_id = int(parts[1])
                        u_id = int(parts[2])
                        bot.add_view(RestoreRolesView(g_id, u_id), message_id=msg.id)
                    except:
                        pass

    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        async for message in db_chan.history(limit=50):
            if "BACKUP_COUNT|" in message.content:
                parts = message.content.split("|")
                current_count = int(parts[1])
                last_user_id = int(parts[2]) if parts[2] != "None" else None
                active_counting_channel = int(parts[3])
                break

    await load_ticket_configs()
    for ticket_id, config in ticket_configs.items():
        bot.add_view(TicketCreateView(ticket_id))

    await load_table_from_log()
    load_xp()
    await load_xp_from_discord()
    await load_donations_from_discord()
    await refresh_scoreboard()
    await load_roblox_links()
    await load_tempbans_from_discord()
    await load_tempmutes_from_discord()
    await load_bans_from_discord()
    await load_giveaways_from_discord()

    # --- Système d'invitations ---
    await load_invite_data()
    await load_already_invited()
    for guild in bot.guilds:
        await refresh_invite_cache(guild)
    for request_id, record in invite_data.get("cashouts", {}).items():
        if record.get("status") == "pending":
            bot.add_view(ConfirmPaymentView(request_id))

    # --- Système de warns / big warns ---
    await load_warn_data()

    if not check_giveaways.is_running():
        check_giveaways.start()
    if not check_bans.is_running():
        check_bans.start()
    if not enforce_permissions.is_running():
        enforce_permissions.start()
    if not update_roblox_funds.is_running():
        update_roblox_funds.start()
    if not check_tempbans.is_running():
        check_tempbans.start()
    if not check_tempmutes.is_running():
        check_tempmutes.start()
    if not cleanup_oauth_states.is_running():
        cleanup_oauth_states.start()
    if not update_online_counter.is_running():
        update_online_counter.start()
    if not check_warn_expiry.is_running():
        check_warn_expiry.start()

    await send_log(f"✅ **Botixirya** prêt. Score : `{current_count}` | Configs tickets : `{len(ticket_configs)}`")

@bot.event
async def on_message(message):
    global current_count, last_user_id, active_counting_channel
    if message.author == bot.user or not message.guild:
        return

    has_everyone = message.mention_everyone or "@everyone" in message.content or "@here" in message.content
    if has_everyone and message.author.id != OWNER_ID and message.author.id not in safe_users:
        member = message.author
        gid = str(message.guild.id)
        uid = str(member.id)
        now = time.time()

        if gid not in everyone_tracker:
            everyone_tracker[gid] = {}
        if uid not in everyone_tracker[gid]:
            everyone_tracker[gid][uid] = []

        everyone_tracker[gid][uid] = [t for t in everyone_tracker[gid][uid] if now - t < RAID_WINDOW]
        everyone_tracker[gid][uid].append(now)

        try:
            await message.delete()
        except:
            pass

        if len(everyone_tracker[gid][uid]) >= 4:
            everyone_tracker[gid][uid] = []
            await quarantine_user(message.guild, member)
            return

    member = message.author
    verified_role = message.guild.get_role(ROLE_VERIFIED_ID)
    if verified_role and verified_role in member.roles:
        uid = str(member.id)
        now = time.time()
        if now - xp_cooldowns.get(uid, 0) >= XP_COOLDOWN:
            from datetime import datetime, timezone
            xp_cooldowns[uid] = now
            gained = random.randint(XP_MIN, XP_MAX)
            entry = xp_data.get(uid, {"xp": 0, "level": 0, "streak": 0, "last_daily": None, "xp_today": 0, "last_xp_date": None})
            old_level = entry.get("level", 0)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if entry.get("last_xp_date") != today:
                entry["xp_today"] = 0
                entry["last_xp_date"] = today
            entry["xp"] = entry.get("xp", 0) + gained
            entry["xp_today"] = entry.get("xp_today", 0) + gained
            entry["level"] = get_level(entry["xp"])
            xp_data[uid] = entry
            await save_xp_to_discord()
            await check_level_up(message.guild, member, old_level, entry["level"])

    if message.channel.id == active_counting_channel:
        content = message.content.strip()
        if content.isdigit():
            number = int(content)
            if number == current_count + 1 and message.author.id != last_user_id:
                current_count = number
                last_user_id = message.author.id
                await save_counting_to_db()
                await message.add_reaction("✅")
            else:
                current_count = 0
                last_user_id = None
                await save_counting_to_db()
                await message.add_reaction("❌")
                await message.channel.send("⚠️ Suite cassée ! Retour à 1.")

    await bot.process_commands(message)

@bot.event
async def on_invite_create(invite):
    gid = invite.guild.id
    invite_cache.setdefault(gid, {})[invite.code] = {
        "uses": invite.uses,
        "inviter_id": invite.inviter.id if invite.inviter else None
    }

@bot.event
async def on_invite_delete(invite):
    gid = invite.guild.id
    cached = invite_cache.get(gid, {}).pop(invite.code, None)
    inviter_id = cached.get("inviter_id") if cached else (invite.inviter.id if invite.inviter else None)
    if inviter_id:
        recently_deleted_invites.setdefault(gid, {})[invite.code] = {
            "inviter_id": inviter_id,
            "deleted_at": time.time()
        }

@bot.event
async def on_member_join(member):
    if member.bot:
        return

    await asyncio.sleep(0.5)
    unverified_role = member.guild.get_role(ROLE_UNVERIFIED_ID)
    if unverified_role:
        try:
            await member.add_roles(unverified_role, reason="Arrivée sur le serveur")
        except Exception as e:
            await send_log(f"⚠️ Impossible d'attribuer Unverified à {member.mention} : {e}")

    log_chan = bot.get_channel(MEMBER_LOG_CHANNEL_ID)
    if log_chan:
        account_age = (discord.utils.utcnow() - member.created_at).days
        age_flag = " — ⚠️ **COMPTE RÉCENT**" if account_age < 7 else ""
        embed = discord.Embed(
            title="📥 Nouveau membre",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Utilisateur",    value=f"{member.mention} (`{member.id}`)",                inline=False)
        embed.add_field(name="Compte créé le", value=member.created_at.strftime("%d/%m/%Y à %H:%M UTC"), inline=True)
        embed.add_field(name="Âge du compte",  value=f"{account_age} jour(s){age_flag}",                inline=True)
        embed.set_footer(text=f"Membres : {member.guild.member_count}")
        await log_chan.send(embed=embed)

    # --- Système d'invitations ---
    invited_str = str(member.id)
    already_seen = invited_str in already_invited_ids
    inviter_id = await find_inviter(member.guild)
    account_age_days = (discord.utils.utcnow() - member.created_at).days
    account_too_young = account_age_days < INVITE_MIN_ACCOUNT_AGE_DAYS

    if inviter_id:
        invite_data.setdefault("invited_by", {})[invited_str] = inviter_id

    arrival_chan = bot.get_channel(INVITE_ARRIVAL_CHANNEL_ID)

    if inviter_id and not already_seen and not account_too_young:
        balances = invite_data.setdefault("balances", {})
        entry = balances.get(str(inviter_id), {"count": 0, "balance": 0, "total_earned": 0})
        entry["count"] = entry.get("count", 0) + 1
        entry["balance"] = entry.get("balance", 0) + INVITE_REWARD_PER_INVITE
        entry["total_earned"] = entry.get("total_earned", 0) + INVITE_REWARD_PER_INVITE
        balances[str(inviter_id)] = entry
        already_invited_ids.add(invited_str)
        await save_invite_data()
        await save_already_invited()

        if arrival_chan:
            msg = random.choice(INVITE_WELCOME_CREDITED).format(invited=member.mention, inviter=f"<@{inviter_id}>")
            await arrival_chan.send(msg)
    elif inviter_id and not already_seen and account_too_young:
        # Compte trop récent : invitation non créditée cette fois, mais pas bloquée définitivement —
        # si la personne revient plus tard une fois son compte assez ancien, l'invitation pourra compter.
        await save_invite_data()
        await send_log(
            f"🚫 **Invitation non créditée** : {member.mention} (`{member.id}`) a un compte de "
            f"{account_age_days} jour(s) (minimum {INVITE_MIN_ACCOUNT_AGE_DAYS}j requis). "
            f"Inviteur potentiel : <@{inviter_id}>."
        )
        if arrival_chan:
            msg = random.choice(INVITE_WELCOME_UNKNOWN).format(invited=member.mention)
            await arrival_chan.send(msg)
    elif inviter_id and already_seen:
        await save_invite_data()  # on garde le mapping invited_by à jour même sans rémunération
        if arrival_chan:
            msg = random.choice(INVITE_WELCOME_ALREADY_SEEN).format(invited=member.mention)
            await arrival_chan.send(msg)
    else:
        if not already_seen:
            already_invited_ids.add(invited_str)
            await save_already_invited()
        if arrival_chan:
            msg = random.choice(INVITE_WELCOME_UNKNOWN).format(invited=member.mention)
            await arrival_chan.send(msg)
@bot.event
async def on_guild_channel_delete(channel):
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
    guild = role.guild
    await asyncio.sleep(0.5)
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if time.time() - entry.created_at.timestamp() < 5:
                await track_deletion(guild, entry.user, "roles")
            break
    except:
        pass

@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    await asyncio.sleep(0.5)
    try:
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if (time.time() - entry.created_at.timestamp() < 5
                    and entry.target.id == member.id
                    and entry.user.id != bot.user.id):
                manual_log = bot.get_channel(MANUAL_LOG_CHANNEL_ID)
                if manual_log:
                    embed = discord.Embed(title="👢 Kick manuel", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Utilisateur", value=f"{member} (`{member.id}`)", inline=True)
                    embed.add_field(name="Modérateur",  value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    embed.add_field(name="Raison",      value=entry.reason or "—", inline=False)
                    await manual_log.send(embed=embed)
            break
    except Exception:
        pass
    log_chan = bot.get_channel(MEMBER_LOG_CHANNEL_ID)
    if log_chan:
        time_on_server = "Inconnu"
        if member.joined_at:
            delta = discord.utils.utcnow() - member.joined_at
            days  = delta.days
            hours = delta.seconds // 3600
            time_on_server = f"{days}j {hours}h" if days else f"{hours}h"

        roles = [r.name for r in member.roles if r != member.guild.default_role]
        roles_str = ", ".join(roles[:15]) if roles else "Aucun"

        embed = discord.Embed(
            title="📤 Membre parti",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Utilisateur",         value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Temps sur le serveur", value=time_on_server,             inline=True)
        embed.add_field(name="Rôles",               value=roles_str,                   inline=False)
        embed.set_footer(text=f"Membres : {member.guild.member_count}")
        await log_chan.send(embed=embed)

    # --- Système d'invitations ---
    invite_depart_chan = bot.get_channel(INVITE_DEPART_CHANNEL_ID)
    if invite_depart_chan:
        known_inviter_id = invite_data.get("invited_by", {}).get(str(member.id))
        if known_inviter_id:
            await invite_depart_chan.send(
                f"📤 {member} (invité par <@{known_inviter_id}>) vient de quitter le serveur."
            )
        else:
            await invite_depart_chan.send(f"📤 {member} vient de quitter le serveur.")

    # --- Flush des données "identité" désormais obsolètes (garde XP, invitations, donations, etc.) ---
    uid = str(member.id)
    if uid in roblox_links:
        del roblox_links[uid]
        await save_roblox_links()

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    # Ne pas logger les messages dans les salons mémoire du bot
    if message.channel.id in MEMORY_CHANNELS:
        return

    log_chan = bot.get_channel(MESSAGES_LOG_CHANNEL_ID)
    if not log_chan:
        return

    content = message.content or "*(contenu non disponible — embed ou fichier)*"
    if len(content) > 1000:
        content = content[:1000] + "…"

    embed = discord.Embed(
        title="🗑️ Message supprimé",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Auteur",  value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Salon",   value=message.channel.mention,                             inline=True)
    embed.add_field(name="Contenu", value=content,                                             inline=False)
    if message.attachments:
        embed.add_field(
            name="Pièces jointes",
            value="\n".join(a.filename for a in message.attachments),
            inline=False
        )
    await log_chan.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild:
        return
    if before.content == after.content:
        return  # Changement d'embed uniquement, pas de contenu

    if before.channel.id in MEMORY_CHANNELS:
        return

    log_chan = bot.get_channel(MESSAGES_LOG_CHANNEL_ID)
    if not log_chan:
        return

    before_content = before.content or "*(non disponible)*"
    after_content  = after.content  or "*(non disponible)*"
    if len(before_content) > 500:
        before_content = before_content[:500] + "…"
    if len(after_content) > 500:
        after_content = after_content[:500] + "…"

    embed = discord.Embed(
        title="✏️ Message modifié",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Auteur", value=f"{before.author.mention} (`{before.author.id}`)", inline=True)
    embed.add_field(name="Salon",  value=before.channel.mention,                            inline=True)
    embed.add_field(name="Lien",   value=f"[Aller au message]({after.jump_url})",           inline=True)
    embed.add_field(name="Avant",  value=before_content, inline=False)
    embed.add_field(name="Après",  value=after_content,  inline=False)
    await log_chan.send(embed=embed)
@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(0.5)
    log_chan = bot.get_channel(MANUAL_LOG_CHANNEL_ID)
    if not log_chan:
        return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if time.time() - entry.created_at.timestamp() > 5:
            return
        if entry.user.id == bot.user.id:
            return
        embed = discord.Embed(title="🔨 Ban manuel", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Utilisateur", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Modérateur",  value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
        embed.add_field(name="Raison",      value=entry.reason or "—", inline=False)
        await log_chan.send(embed=embed)
        return

@bot.event
async def on_member_unban(guild, user):
    await asyncio.sleep(0.5)
    log_chan = bot.get_channel(MANUAL_LOG_CHANNEL_ID)
    if not log_chan:
        return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
        if time.time() - entry.created_at.timestamp() > 5:
            return
        if entry.user.id == bot.user.id:
            return
        embed = discord.Embed(title="✅ Unban manuel", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Utilisateur", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Modérateur",  value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
        await log_chan.send(embed=embed)
        return

@bot.event
async def on_member_update(before, after):
    muted_role   = after.guild.get_role(MUTED_ROLE_ID)
    was_muted    = muted_role in before.roles if muted_role else False
    is_muted_now = muted_role in after.roles  if muted_role else False
    timeout_changed = before.timed_out_until != after.timed_out_until

    if not (was_muted != is_muted_now or timeout_changed):
        return

    await asyncio.sleep(0.5)
    log_chan = bot.get_channel(MANUAL_LOG_CHANNEL_ID)
    if not log_chan:
        return

    if was_muted != is_muted_now:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if time.time() - entry.created_at.timestamp() > 5:
                break
            if entry.user.id == bot.user.id:
                break
            title = "🔇 Mute manuel" if is_muted_now else "🔊 Unmute manuel"
            color = discord.Color.orange() if is_muted_now else discord.Color.teal()
            embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
            embed.add_field(name="Utilisateur", value=f"{after.mention} (`{after.id}`)", inline=True)
            embed.add_field(name="Modérateur",  value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
            await log_chan.send(embed=embed)
            break

    if timeout_changed and after.timed_out_until:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            if time.time() - entry.created_at.timestamp() > 5:
                break
            if entry.user.id == bot.user.id:
                break
            embed = discord.Embed(title="⏱️ Timeout manuel", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Utilisateur", value=f"{after.mention} (`{after.id}`)", inline=True)
            embed.add_field(name="Modérateur",  value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
            embed.add_field(name="Expire le",   value=after.timed_out_until.strftime("%d/%m/%Y à %H:%M UTC"), inline=True)
            await log_chan.send(embed=embed)
            break
@bot.after_invoke
async def log_admin_action(ctx):
    """Trace automatiquement toutes les commandes admin/modo dans admin-actions-logs."""
    if not ctx.command or ctx.command.name not in LOGGED_ADMIN_COMMANDS:
        return
    if not ctx.guild:
        return

    log_chan = bot.get_channel(ADMIN_ACTIONS_LOG_CHANNEL_ID)
    if not log_chan:
        return

    full_msg = ctx.message.content
    if len(full_msg) > 800:
        full_msg = full_msg[:800] + "…"

    embed = discord.Embed(
        title="🛠️ Commande admin utilisée",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Commande",   value=f"`{ctx.prefix}{ctx.command.name}`",              inline=True)
    embed.add_field(name="Utilisateur", value=f"{ctx.author.mention} (`{ctx.author.id}`)",    inline=True)
    embed.add_field(name="Salon",       value=ctx.channel.mention,                            inline=True)
    embed.add_field(name="Message complet", value=f"```{full_msg}```",                        inline=False)
    embed.set_footer(text=f"Serveur : {ctx.guild.name}")
    await log_chan.send(embed=embed)

# ==========================================
# COMMANDES
# ==========================================

@bot.command()
async def help(ctx):
    user = ctx.author

    blocked_role_ids = {MUTED_ROLE_ID, RAIDER_ROLE_ID, ROLE_UNVERIFIED_ID}
    user_role_ids = {r.id for r in user.roles}
    if user_role_ids & blocked_role_ids:
        return

    is_owner = (user.id == OWNER_ID)
    is_membre = (ROLE_VERIFIED_ID in user_role_ids)

    embed = discord.Embed(title="📜 Aide Botixirya", color=discord.Color.blue())

    embed.add_field(name="🛡️ Système", value=(
        f"**{COMMAND_PREFIX}ping** : Affiche la latence.\n"
        f"**{COMMAND_PREFIX}score** : Affiche le score actuel."
    ), inline=False)
    embed.add_field(name="🎮 Fun", value=(
        f"**{COMMAND_PREFIX}rps @user** : Pierre/Feuille/Ciseaux.\n"
        f"**{COMMAND_PREFIX}tictactoe @user** : Morpion interactif.\n"
        f"**{COMMAND_PREFIX}pendu** : Jeu du pendu.\n"
        f"**{COMMAND_PREFIX}slots** : Machine à sous (1 fois/10 min).\n"
        f"**{COMMAND_PREFIX}roll [faces]** : Lance un dé à N faces.\n"
        f"**{COMMAND_PREFIX}coinflip** : Pile ou face.\n"
        f"**{COMMAND_PREFIX}8ball [question]** : La boule magique.\n"
        f"**{COMMAND_PREFIX}roulette** : 1/6 de te faire muter 2 min.\n"
        f"**{COMMAND_PREFIX}ship @user1 @user2** : Compatibilité entre deux membres.\n"
        f"**{COMMAND_PREFIX}howgay @user** : Gaymètre (pour rire)."
    ), inline=False)
    embed.add_field(name="📊 Rang & Activité", value=(
        f"**{COMMAND_PREFIX}rank (@user)** : Ton niveau et ta progression.\n"
        f"**{COMMAND_PREFIX}leaderboard** : Top 10 membres.\n"
        f"**{COMMAND_PREFIX}top3** : Podium d'activité du jour.\n"
        f"**{COMMAND_PREFIX}daily** : Récompense quotidienne (reset à minuit).\n"
        f"**{COMMAND_PREFIX}streak (@user)** : Streak de daily consécutifs."
    ), inline=False)
    embed.add_field(name="🎮 Roblox", value=(
        f"**{COMMAND_PREFIX}profile (@user / pseudo)** : Profil complet d'un membre (Roblox, niveau, invitations). Sans argument = ton propre profil."
    ), inline=False)
    embed.add_field(name="💸 Donations", value=(
        f"**{COMMAND_PREFIX}RobuxLeaderBoard** : Affiche le topboard complet dans le salon courant.\n"
        f"**{COMMAND_PREFIX}RobuxDonatedProfile @user** : Profil de donation d'un membre (si dans le topboard)."
    ), inline=False)
    embed.add_field(name="📨 Invitations", value=(
        f"**{COMMAND_PREFIX}invites (@user)** : Ton nombre d'invitations et ton solde. Sans argument = toi-même.\n"
        f"**{COMMAND_PREFIX}inviteleaderboard** : Top 10 des inviteurs.\n"
        f"**{COMMAND_PREFIX}cashout [montant]** : Demande le paiement d'un montant (min. {INVITE_CASHOUT_MINIMUM} Robux)."
    ), inline=False)

    is_admin = ctx.author.guild_permissions.administrator or is_owner
    if is_admin:
        embed.add_field(name="⚙️ Admin", value=(
            f"**{COMMAND_PREFIX}setcountchannel** : Définit le salon de comptage.\n"
            f"**{COMMAND_PREFIX}setscore [nb]** : Modifie manuellement le score.\n"
            f"**{COMMAND_PREFIX}lock / unlock** : Verrouille ou déverrouille le salon.\n"
            f"**{COMMAND_PREFIX}restore** : Recrée le salon actuel."
        ), inline=False)
        embed.add_field(name="🔨 Modération", value=(
            f"**{COMMAND_PREFIX}msgdel [nb] (@user)** : Supprime des messages.\n"
            f"**{COMMAND_PREFIX}ban @user [min] [raison]** : Bannit (0 = permanent).\n"
            f"**{COMMAND_PREFIX}tempban @user [durée] [raison]** : Ban temporaire.\n"
            f"  └ Durée : `10m` = 10 min · `2h` = 2 heures · `7d` = 7 jours\n"
            f"**{COMMAND_PREFIX}pardon @user** : Débannit.\n"
            f"**{COMMAND_PREFIX}kick @user [raison]** : Expulse.\n"
            f"**{COMMAND_PREFIX}mute @user [raison]** : Mute permanent.\n"
            f"**{COMMAND_PREFIX}tempmute @user [durée] [raison]** : Mute temporaire.\n"
            f"  └ Durée : `10m` = 10 min · `2h` = 2 heures · `7d` = 7 jours\n"
            f"**{COMMAND_PREFIX}unmute @user** : Unmute."
        ), inline=False)
        embed.add_field(name="⚠️ Warns", value=(
            f"**{COMMAND_PREFIX}warn @user [raison]** : Avertissement simple ({WARNS_PER_BIGWARN} = 1 big warn auto).\n"
            f"**{COMMAND_PREFIX}bigwarn @user [raison]** : Big warn direct (nécessite Ban Members).\n"
            f"**{COMMAND_PREFIX}warnings @user** : Voir l'historique des warns d'un membre.\n"
            f"**{COMMAND_PREFIX}unwarn @user** : Retire le dernier warn simple.\n"
            f"**{COMMAND_PREFIX}unbigwarn @user** : Retire le dernier big warn (ne défait pas la sanction).\n"
            f"  └ Big Warn 1 = mute 1j · Big Warn 2 = mute 3j · Big Warn 3 = ban 31j + reset du cycle."
        ), inline=False)

    if is_owner:
        embed.add_field(name="👑 Owner — Général", value=(
            f"**{COMMAND_PREFIX}kill** : Éteint le bot.\n"
            f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [condition]** : Lance un giveaway.\n"
            f"**{COMMAND_PREFIX}safe @user** : Lève la quarantaine + whiteliste.\n"
            f"**{COMMAND_PREFIX}removesafe @user** : Remet sous surveillance anti-raid.\n"
            f"→ Restauration des rôles via bouton dans <#{ROLE_BACKUP_CHANNEL_ID}>."
        ), inline=False)
        embed.add_field(name="🎫 Owner — Tickets", value=(
            f"**{COMMAND_PREFIX}TicketCreatingChannel [category_id] [logs_id] [Message] [InsideMessage] [channel_id]**\n"
            f"→ Configure un point de création de tickets dans le salon spécifié."
        ), inline=False)
        embed.add_field(name="💰 Owner — Tableau de rémunération", value=(
            f"**{COMMAND_PREFIX}SetTableChannel** : Définit le salon d'affichage.\n"
            f"**{COMMAND_PREFIX}AddTableLine @user [valeur] [profession]** : Ajoute une ligne.\n"
            f"**{COMMAND_PREFIX}SetTableValue @user [valeur]** : Met à jour (TotalValue += valeur).\n"
            f"**{COMMAND_PREFIX}RemoveTableValue @user** : Retire un utilisateur.\n"
            f"**{COMMAND_PREFIX}GetTableUserValue @user (colonne)** : Affiche les données.\n"
            f"→ Colonnes : `value`, `total`, `profession`, `time`"
        ), inline=False)
        embed.add_field(name="💸 Owner — Donations", value=(
            f"**{COMMAND_PREFIX}RemoveTopBoardRobux [pseudo] [montant]** : Retire des Robux du total d'un donateur."
        ), inline=False)
        embed.add_field(name="📨 Owner — Invitations", value=(
            f"**{COMMAND_PREFIX}AdjustInviteBalance @user [montant] [raison]** : Ajuste le solde d'un membre (+/-).\n"
            f"**{COMMAND_PREFIX}ResetInviteFlag @user** : Permet à un ID de compter à nouveau comme nouvelle invitation.\n"
            f"→ Confirmation des paiements via bouton dans <#{INVITE_CASHOUT_CHANNEL_ID}>."
        ), inline=False)
        embed.add_field(name="💾 Owner — Backup & Setup", value=(
            f"**{COMMAND_PREFIX}backup** : Copie le serveur principal → backup *(backup only)*.\n"
            f"**{COMMAND_PREFIX}COMMANDSON** : Active toutes les commandes sur le serveur backup.\n"
            f"**{COMMAND_PREFIX}setuprobloxverify** : Envoie le message de vérification Roblox dans le salon dédié."
        ), inline=False)

    await ctx.send(embed=embed)

# --- Système ---

@bot.command()
async def setuprobloxverify(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    chan = bot.get_channel(ROBLOX_VERIFY_CHANNEL_ID)
    if not chan:
        return await ctx.send("❌ Salon de vérification introuvable.")

    embed = discord.Embed(
        title="🎮 Vérification Roblox",
        description=(
            "Pour accéder au serveur, tu dois lier ton compte Roblox.\n\n"
            "Clique sur le bouton ci-dessous pour commencer la liaison.\n"
            "Tu seras redirigé vers Roblox pour autoriser la connexion.\n\n"
            "Une fois terminé, tu obtiendras automatiquement le rôle **Membre**. ✅"
        ),
        color=discord.Color.blurple()
    )
    await chan.send(embed=embed, view=RobloxVerifyView())
    await ctx.send(f"✅ Message de vérification envoyé dans {chan.mention}.", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def kill(ctx):
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
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 4:
        return await ctx.send(
            f"❌ Format incorrect. Usage :\n"
            f"`{COMMAND_PREFIX}giveaway [minutes] [nb_gagnants] [prix] [condition]`"
        )
    try:
        minutes = int(m[0])
        winners_count = int(m[1])
    except ValueError:
        return await ctx.send("❌ `[minutes]` et `[nb_gagnants]` doivent être des nombres entiers.")

    prize = m[2]
    condition = m[3]
    end = time.time() + (minutes * 60)

    embed = discord.Embed(title="🎉 GIVEAWAY", color=discord.Color.gold())
    embed.add_field(name="Prix", value=prize, inline=False)
    embed.add_field(name="Condition", value=condition, inline=False)
    msg = await ctx.send(embed=embed, view=GiveawayView(bot))

    giveaway_data[str(msg.id)] = {
        "channel_id": ctx.channel.id,
        "prize": prize,
        "condition": condition,
        "winners_count": winners_count,
        "end_time": end,
        "participants": [],
        "ended": False
    }
    await save_giveaways_to_discord()

# --- Modération ---

@bot.command()
@commands.has_permissions(manage_messages=True)
async def msgdel(ctx, number: int, user: discord.Member = None):
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
    end_time = time.time() + duration * 60 if duration > 0 else None

    try:
        await user.ban(reason=reason)
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    key = f"{ctx.guild.id}:{user.id}"
    bans_data[key] = {
        "user_id": user.id,
        "guild_id": ctx.guild.id,
        "reason": reason,
        "end_time": end_time,
        "moderator": ctx.author.id
    }
    await save_bans_to_discord()

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
async def tempban(ctx, user: discord.Member, duration: str, *, reason: str = "Aucune raison fournie"):
    """
    Ban temporaire.
    Durée : 10m (minutes) · 2h (heures) · 7d (jours)
    Exemple : <aav>tempban @user 2h Spam
    """
    seconds = parse_duration(duration)
    if seconds is None:
        return await ctx.send(
            f"❌ Format de durée invalide.\n"
            f"Utilise : `{COMMAND_PREFIX}tempban @user <durée> [raison]`\n"
            f"Exemples : `10m` · `2h` · `7d`"
        )

    duration_str = format_duration(seconds)
    end_time     = time.time() + seconds

    try:
        await user.ban(reason=f"[TempBan {duration_str}] {reason}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur lors du ban : {e}")

    key = f"{ctx.guild.id}:{user.id}"
    tempban_data[key] = {
        "user_id":      user.id,
        "guild_id":     ctx.guild.id,
        "end_time":     end_time,
        "reason":       reason,
        "moderator_id": ctx.author.id,
        "username":     str(user)
    }
    await save_tempbans_to_discord()

    log_chan = bot.get_channel(TEMPBAN_LOG_CHANNEL_ID)
    if log_chan:
        from datetime import datetime, timezone
        expire_str = datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
        embed = discord.Embed(title="🔨 TempBan", color=discord.Color.red())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 Utilisateur",  value=f"{user} (`{user.id}`)",  inline=True)
        embed.add_field(name="⏱️ Durée",        value=f"**{duration_str}**",    inline=True)
        embed.add_field(name="📅 Expire le",    value=expire_str,               inline=True)
        embed.add_field(name="👮 Modérateur",   value=ctx.author.mention,       inline=True)
        embed.add_field(name="📝 Raison",       value=reason,                   inline=False)
        await log_chan.send(embed=embed)

    await ctx.send(
        f"🔨 **{user}** a été banni temporairement pour **{duration_str}**.\n"
        f"📝 Raison : {reason}"
    )

@bot.command()
@commands.has_permissions(ban_members=True)
async def pardon(ctx, user: discord.User):
    try:
        await ctx.guild.unban(user, reason=f"Pardonné par {ctx.author}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur : {e}")

    key = f"{ctx.guild.id}:{user.id}"
    if key in bans_data:
        del bans_data[key]
        await save_bans_to_discord()

    # Retire aussi du tempban si présent
    if key in tempban_data:
        del tempban_data[key]
        await save_tempbans_to_discord()

    log_chan = bot.get_channel(BAN_LOG_CHANNEL_ID)
    if log_chan:
        await log_chan.send(f"✅ **Unban** : {user} (`{user.id}`) pardonné par {ctx.author.mention}")
    await ctx.send(f"✅ {user} a été débanni.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, user: discord.Member, *, reason: str = "Aucune raison fournie"):
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
async def tempmute(ctx, user: discord.Member, duration: str, *, reason: str = "Aucune raison fournie"):
    """
    Mute temporaire.
    Durée : 10m (minutes) · 2h (heures) · 7d (jours)
    Exemple : <aav>tempmute @user 30m Spam vocal
    """
    seconds = parse_duration(duration)
    if seconds is None:
        return await ctx.send(
            f"❌ Format de durée invalide.\n"
            f"Utilise : `{COMMAND_PREFIX}tempmute @user <durée> [raison]`\n"
            f"Exemples : `10m` · `2h` · `7d`"
        )

    muted_role   = ctx.guild.get_role(MUTED_ROLE_ID)
    verified_role = ctx.guild.get_role(ROLE_VERIFIED_ID)

    if not muted_role:
        return await ctx.send("❌ Rôle Muted introuvable.")

    duration_str = format_duration(seconds)
    end_time     = time.time() + seconds

    try:
        await user.add_roles(muted_role, reason=f"[TempMute {duration_str}] {reason}")
        if verified_role and verified_role in user.roles:
            await user.remove_roles(verified_role, reason=f"[TempMute {duration_str}] {reason}")
    except Exception as e:
        return await ctx.send(f"❌ Erreur lors du mute : {e}")

    key = f"{ctx.guild.id}:{user.id}"
    tempmute_data[key] = {
        "user_id":      user.id,
        "guild_id":     ctx.guild.id,
        "end_time":     end_time,
        "reason":       reason,
        "moderator_id": ctx.author.id,
        "username":     str(user)
    }
    await save_tempmutes_to_discord()

    log_chan = bot.get_channel(TEMPMUTE_LOG_CHANNEL_ID)
    if log_chan:
        from datetime import datetime, timezone
        expire_str = datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
        embed = discord.Embed(title="🔇 TempMute", color=discord.Color.orange())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 Utilisateur",  value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="⏱️ Durée",        value=f"**{duration_str}**",           inline=True)
        embed.add_field(name="📅 Expire le",    value=expire_str,                      inline=True)
        embed.add_field(name="👮 Modérateur",   value=ctx.author.mention,              inline=True)
        embed.add_field(name="📝 Raison",       value=reason,                          inline=False)
        await log_chan.send(embed=embed)

    await ctx.send(
        f"🔇 **{user}** a été muté temporairement pour **{duration_str}**.\n"
        f"📝 Raison : {reason}"
    )

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, user: discord.Member):
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

    # Retire aussi du tempmute si présent
    key = f"{ctx.guild.id}:{user.id}"
    if key in tempmute_data:
        del tempmute_data[key]
        await save_tempmutes_to_discord()

    await ctx.send(f"🔊 {user.mention} unmute.")

@bot.command()
async def safe(ctx, user: discord.Member):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    user_id = str(user.id)
    safe_users.add(user.id)

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
        await ctx.send(f"✅ {user.mention} sorti de quarantaine, rôles restaurés et exclu de la surveillance anti-raid.")
    else:
        await ctx.send(f"✅ {user.mention} exclu de la surveillance anti-raid (pas en quarantaine formelle).")

    await send_log(f"🛡️ **Safe** : {user.mention} libéré et whitelisté par {ctx.author.mention}")

@bot.command()
async def removesafe(ctx, user: discord.Member):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    if user.id in safe_users:
        safe_users.discard(user.id)
        await ctx.send(f"🔍 {user.mention} est à nouveau sous surveillance anti-raid.")
    else:
        await ctx.send(f"ℹ️ {user.mention} n'était pas dans la liste blanche.")

    await send_log(f"🔍 **RemoveSafe** : {user.mention} remis sous surveillance par {ctx.author.mention}")

# --- Tickets ---

@bot.command()
@commands.has_permissions(administrator=True)
async def TicketCreatingChannel(ctx, *, args):
    m = re.findall(r'\[(.*?)\]', args)
    if len(m) < 5:
        return await ctx.send(
            f"❌ Format incorrect. Usage :\n"
            f"`{COMMAND_PREFIX}TicketCreatingChannel [category_id] [logs_id] [Message du salon] [Message du ticket] [channel_id]`"
        )

    try:
        category_id = int(m[0])
        logs_channel_id = int(m[1])
        channel_message = m[2]
        inside_ticket_message = m[3]
        actual_channel_id = int(m[4])
    except ValueError:
        return await ctx.send("❌ Les IDs doivent être des nombres entiers.")

    category = ctx.guild.get_channel(category_id)
    if not category or not isinstance(category, discord.CategoryChannel):
        return await ctx.send(f"❌ Catégorie introuvable avec l'ID `{category_id}`.")

    actual_channel = ctx.guild.get_channel(actual_channel_id)
    if not actual_channel:
        return await ctx.send(f"❌ Salon introuvable avec l'ID `{actual_channel_id}`.")

    logs_channel = ctx.guild.get_channel(logs_channel_id)
    if not logs_channel:
        return await ctx.send(f"❌ Salon de logs introuvable avec l'ID `{logs_channel_id}`.")

    ticket_id = str(uuid.uuid4())

    config = {
        "ticket_id": ticket_id,
        "actual_channel_id": actual_channel_id,
        "category_id": category_id,
        "logs_channel_id": logs_channel_id,
        "channel_message": channel_message,
        "inside_ticket_message": inside_ticket_message
    }
    ticket_configs[ticket_id] = config
    await save_ticket_config(config)

    view = TicketCreateView(ticket_id)
    bot.add_view(view)

    embed = discord.Embed(description=channel_message, color=discord.Color.blurple())
    embed.set_footer(text=f"Système de ticket — ID : {ticket_id[:8]}")
    await actual_channel.send(embed=embed, view=view)

    await ctx.send(
        f"✅ Système de tickets configuré dans {actual_channel.mention}.\n"
        f"Catégorie : `{category.name}` | Logs : {logs_channel.mention}\n"
        f"🆔 ID du ticket : `{ticket_id[:8]}`"
    )

# ==========================================
# COMMANDES TABLEAU DE RÉMUNÉRATION
# ==========================================

@bot.command()
async def SetTableChannel(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")
    global table_channel_id, table_message_id
    table_channel_id = ctx.channel.id
    table_message_id = None
    await save_table_to_log()
    await refresh_table_message(ctx.guild)
    await ctx.send(f"✅ Salon du tableau défini sur {ctx.channel.mention}.")

@bot.command()
async def AddTableLine(ctx, user: discord.Member, value: float, *, profession: str):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")
    from datetime import datetime, timezone
    uid = str(user.id)
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    if uid in table_data:
        return await ctx.send(
            f"❌ {user.mention} est déjà dans le tableau. "
            f"Utilisez `{COMMAND_PREFIX}SetTableValue` pour modifier sa valeur."
        )

    table_data[uid] = {
        "profession": profession,
        "value": value,
        "total_value": value,
        "last_modified": now
    }
    await save_table_to_log()
    await refresh_table_message(ctx.guild)
    await ctx.send(f"✅ {user.mention} ajouté. Valeur : `{value}` | Total : `{value}` | Profession : `{profession}`")

@bot.command()
async def SetTableValue(ctx, user: discord.Member, value: float):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")
    from datetime import datetime, timezone
    uid = str(user.id)
    if uid not in table_data:
        return await ctx.send(
            f"❌ {user.mention} n'est pas dans le tableau. "
            f"Utilisez `{COMMAND_PREFIX}AddTableLine` pour l'ajouter."
        )

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    old_total = table_data[uid]["total_value"]
    table_data[uid]["value"] = value
    table_data[uid]["total_value"] = round(old_total + value, 2)
    table_data[uid]["last_modified"] = now

    await save_table_to_log()
    await refresh_table_message(ctx.guild)
    await ctx.send(
        f"✅ Valeur mise à jour pour {user.mention}.\n"
        f"Nouvelle valeur : `{value}` | Nouveau total : `{table_data[uid]['total_value']}`"
    )

@bot.command()
async def RemoveTableValue(ctx, user: discord.Member):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")
    uid = str(user.id)
    if uid not in table_data:
        return await ctx.send(f"❌ {user.mention} n'est pas dans le tableau.")

    del table_data[uid]
    await save_table_to_log()
    await refresh_table_message(ctx.guild)
    await ctx.send(f"✅ {user.mention} retiré du tableau.")

@bot.command()
async def GetTableUserValue(ctx, user: discord.Member, column: str = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")
    uid = str(user.id)
    if uid not in table_data:
        return await ctx.send(f"❌ {user.mention} n'est pas dans le tableau.")

    entry = table_data[uid]

    if column is None:
        embed = discord.Embed(title=f"📋 Données de {user.display_name}", color=discord.Color.gold())
        embed.add_field(name="Profession", value=entry.get("profession", "—"), inline=True)
        embed.add_field(name="Valeur actuelle", value=str(entry.get("value", 0)), inline=True)
        embed.add_field(name="Total cumulé", value=str(entry.get("total_value", 0)), inline=True)
        embed.add_field(name="Dernière màj", value=entry.get("last_modified", "—"), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    else:
        col_map = {
            "value": ("Valeur actuelle", str(entry.get("value", 0))),
            "total": ("Total cumulé", str(entry.get("total_value", 0))),
            "profession": ("Profession", entry.get("profession", "—")),
            "time": ("Dernière màj", entry.get("last_modified", "—"))
        }
        col = column.lower()
        if col not in col_map:
            return await ctx.send("❌ Colonnes disponibles : `value`, `total`, `profession`, `time`")
        label, val = col_map[col]
        await ctx.send(f"📋 **{user.display_name}** — {label} : `{val}`")

# ==========================================
# COMMANDES ROBLOX & DONATIONS
# ==========================================

@bot.command()
async def profile(ctx, *, user_input: str = None):
    target_member = None

    if user_input is None:
        target_member = ctx.author
    else:
        try:
            converter = commands.MemberConverter()
            target_member = await converter.convert(ctx, user_input)
        except:
            user_lower = user_input.lower()
            for m in ctx.guild.members:
                if m.display_name.lower() == user_lower or m.name.lower() == user_lower:
                    target_member = m
                    break

    if not target_member:
        return await ctx.send(f"❌ Membre `{user_input}` introuvable.")

    uid = str(target_member.id)
    link_data = roblox_links.get(uid)

    embed = discord.Embed(
        title=f"📋 Profil de {target_member.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=target_member.display_avatar.url)

    # --- Roblox ---
    if link_data:
        roblox_username = link_data.get("roblox_username", "Inconnu")
        roblox_id       = link_data.get("roblox_id", "?")
        linked_at       = link_data.get("linked_at", "Inconnu")
        embed.add_field(name="🎮 Pseudo Roblox", value=f"**{roblox_username}**", inline=True)
        embed.add_field(name="🆔 Roblox ID",     value=f"`{roblox_id}`",        inline=True)
        embed.add_field(name="📅 Lié le",        value=linked_at,               inline=True)
        embed.add_field(
            name="🔗 Profil Roblox",
            value=f"[Voir sur Roblox](https://www.roblox.com/users/{roblox_id}/profile)",
            inline=False
        )
    else:
        embed.add_field(name="🎮 Roblox", value="❌ Compte Roblox non lié.", inline=False)

    # --- Niveau / XP ---
    xp_entry = xp_data.get(uid, {"xp": 0, "level": 0})
    level = get_level(xp_entry.get("xp", 0))
    embed.add_field(
        name="📊 Niveau",
        value=f"**{level}** ({xp_entry.get('xp', 0):,} XP)".replace(",", " "),
        inline=True
    )

    # --- Invitations ---
    invite_entry = invite_data.get("balances", {}).get(uid, {"count": 0, "balance": 0, "total_earned": 0})
    embed.add_field(
        name="📨 Invitations",
        value=f"**{invite_entry.get('count', 0)}** validée(s)",
        inline=True
    )
    balance = invite_entry.get("balance", 0)
    cashable = "✅ Cashable" if balance >= INVITE_CASHOUT_MINIMUM else f"(min. {INVITE_CASHOUT_MINIMUM} Robux)"
    embed.add_field(
        name="💸 Robux à cash out",
        value=f"**{balance}** Robux {cashable}",
        inline=True
    )

    embed.set_footer(text="Liaison OAuth Roblox officielle ✅" if link_data else "Compte Roblox non lié — <aav>setuprobloxverify pour se lier")
    await ctx.send(embed=embed)

@bot.command()
async def RobuxLeaderBoard(ctx):
    embed = build_scoreboard_embed()
    await ctx.send(embed=embed)

@bot.command()
async def RemoveTopBoardRobux(ctx, username: str, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    if amount <= 0:
        return await ctx.send("❌ Le montant doit être supérieur à 0.")

    target_uid = None
    for uid, entry in donations_data.items():
        if entry.get("username", "").lower() == username.lower():
            target_uid = uid
            break

    if not target_uid:
        return await ctx.send(f"❌ Aucun donateur nommé `{username}` dans le topboard.")

    old_total = donations_data[target_uid]["total"]
    new_total = max(0, old_total - amount)
    donations_data[target_uid]["total"] = new_total

    await save_donations_to_discord()
    await refresh_scoreboard()

    embed = discord.Embed(title="✂️ Robux retirés du Topboard", color=discord.Color.orange())
    embed.add_field(name="Joueur Roblox", value=f"**{username}**", inline=True)
    embed.add_field(name="Retiré", value=f"**{amount:,}** Robux".replace(",", " "), inline=True)
    embed.add_field(name="​", value="​", inline=True)
    embed.add_field(name="Ancien total", value=f"**{old_total:,}** Robux".replace(",", " "), inline=True)
    embed.add_field(name="Nouveau total", value=f"**{new_total:,}** Robux".replace(",", " "), inline=True)
    embed.set_footer(text=f"Modifié par {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command()
async def RobuxDonatedProfile(ctx, *, user_input: str = None):
    if user_input is None:
        uid = None
        for donor_uid, entry in donations_data.items():
            if entry.get("username", "").lower() == ctx.author.display_name.lower() or entry.get("username", "").lower() == ctx.author.name.lower():
                uid = donor_uid
                break
        display_name = ctx.author.display_name
        avatar_url = ctx.author.display_avatar.url
    else:
        uid = None
        avatar_url = None
        display_name = user_input
        try:
            converter = commands.MemberConverter()
            member = await converter.convert(ctx, user_input)
            for donor_uid, entry in donations_data.items():
                if entry.get("username", "").lower() == member.display_name.lower() or entry.get("username", "").lower() == member.name.lower():
                    uid = donor_uid
                    break
            display_name = member.display_name
            avatar_url = member.display_avatar.url
        except:
            for donor_uid, entry in donations_data.items():
                if entry.get("username", "").lower() == user_input.lower():
                    uid = donor_uid
                    display_name = entry.get("username", user_input)
                    break

    if not uid or uid not in donations_data:
        return

    entry = donations_data[uid]
    total = entry.get("total", 0)
    roblox_username = entry.get("username", display_name)

    sorted_donors = sorted(donations_data.items(), key=lambda x: x[1].get("total", 0), reverse=True)
    rank = next((i + 1 for i, (u, _) in enumerate(sorted_donors) if u == uid), "?")

    if rank == 1:
        medal = "🥇"
    elif rank == 2:
        medal = "🥈"
    elif rank == 3:
        medal = "🥉"
    elif isinstance(rank, int) and rank <= 10:
        medal = "🏅"
    else:
        medal = "💸"

    grand_total = sum(e.get("total", 0) for e in donations_data.values())
    percentage = round((total / grand_total) * 100, 1) if grand_total > 0 else 0

    bar_length = 20
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)

    embed = discord.Embed(title=f"{medal} Profil Donation — {roblox_username}", color=discord.Color.gold())
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="💰 Total donné",   value=f"**{total:,}** Robux".replace(",", " "), inline=True)
    embed.add_field(name="🏆 Rang",          value=f"**#{rank}** sur {len(donations_data)}",  inline=True)
    embed.add_field(
        name="📊 Contribution",
        value=f"`{bar}` **{percentage}%**\ndu total des donations",
        inline=False
    )
    embed.set_footer(text="💝 Merci pour ton soutien à Aavixyria !")
    await ctx.send(embed=embed)

# ==========================================
# COMMANDES — SYSTÈME D'INVITATIONS
# ==========================================

@bot.command()
async def invites(ctx, member: discord.Member = None):
    target = member or ctx.author
    uid = str(target.id)
    entry = invite_data.get("balances", {}).get(uid, {"count": 0, "balance": 0, "total_earned": 0})

    embed = discord.Embed(title=f"📨 Invitations de {target.display_name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Invitations valides", value=f"**{entry.get('count', 0)}**", inline=True)
    embed.add_field(name="Solde actuel",        value=f"**{entry.get('balance', 0)}** Robux", inline=True)
    embed.add_field(name="Total gagné (historique)", value=f"**{entry.get('total_earned', 0)}** Robux", inline=True)
    embed.set_footer(text=f"Minimum pour cash out : {INVITE_CASHOUT_MINIMUM} Robux")
    await ctx.send(embed=embed)

@bot.command()
async def inviteleaderboard(ctx):
    balances = invite_data.get("balances", {})
    sorted_inviters = sorted(balances.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:10]

    if not sorted_inviters:
        return await ctx.send("Aucune invitation enregistrée pour le moment.")

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (uid, entry) in enumerate(sorted_inviters):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lines.append(
            f"{medal} **{name}** — {entry.get('count', 0)} invitation(s) · "
            f"{entry.get('balance', 0)} Robux en solde"
        )

    embed = discord.Embed(title="🏆 Leaderboard des invitations", color=discord.Color.gold())
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command()
async def cashout(ctx, amount: int):
    uid = str(ctx.author.id)
    balances = invite_data.setdefault("balances", {})
    entry = balances.get(uid, {"count": 0, "balance": 0, "total_earned": 0})
    current_balance = entry.get("balance", 0)

    if amount < INVITE_CASHOUT_MINIMUM:
        return await ctx.send(f"❌ Le montant minimum pour un cashout est de **{INVITE_CASHOUT_MINIMUM} Robux**.")
    if amount > current_balance:
        return await ctx.send(f"❌ Solde insuffisant. Ton solde actuel est de **{current_balance} Robux**.")

    entry["balance"] = current_balance - amount
    balances[uid] = entry

    request_id = str(uuid.uuid4())
    cashouts = invite_data.setdefault("cashouts", {})
    cashouts[request_id] = {
        "user_id": ctx.author.id,
        "username": str(ctx.author),
        "amount": amount,
        "status": "pending",
        "requested_at": discord.utils.utcnow().strftime("%d/%m/%Y à %H:%M UTC"),
        "paid_by": None,
        "paid_at": None
    }
    await save_invite_data()

    chan = bot.get_channel(INVITE_CASHOUT_CHANNEL_ID)
    if chan:
        embed = discord.Embed(title="💸 Demande de cashout", color=discord.Color.orange())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Utilisateur", value=f"{ctx.author.mention} (`{ctx.author}`)", inline=True)
        embed.add_field(name="Montant",     value=f"**{amount}** Robux",                    inline=True)
        embed.add_field(name="Statut",      value="⏳ En attente de paiement",               inline=False)
        embed.set_footer(text=f"ID de la demande : {request_id[:8]}")
        await chan.send(embed=embed, view=ConfirmPaymentView(request_id))
        await ctx.send(
            f"✅ Demande de cashout de **{amount} Robux** envoyée dans {chan.mention}.\n"
            f"Solde restant : **{entry['balance']} Robux**."
        )
    else:
        await ctx.send("⚠️ Salon de cashout introuvable, mais la demande a été enregistrée.")

@bot.command()
async def AdjustInviteBalance(ctx, user: discord.Member, amount: int, *, reason: str = "Aucune raison fournie"):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    uid = str(user.id)
    balances = invite_data.setdefault("balances", {})
    entry = balances.get(uid, {"count": 0, "balance": 0, "total_earned": 0})
    entry["balance"] = max(0, entry.get("balance", 0) + amount)
    if amount > 0:
        entry["total_earned"] = entry.get("total_earned", 0) + amount
    balances[uid] = entry
    await save_invite_data()

    sign = "+" if amount >= 0 else ""
    await ctx.send(
        f"✅ Solde de {user.mention} ajusté de **{sign}{amount} Robux**.\n"
        f"Nouveau solde : **{entry['balance']} Robux**\n"
        f"Raison : {reason}"
    )

@bot.command()
async def ResetInviteFlag(ctx, user: discord.Member):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    uid = str(user.id)
    if uid in already_invited_ids:
        already_invited_ids.discard(uid)
        await save_already_invited()
        await ctx.send(
            f"✅ {user.mention} peut de nouveau être compté comme une nouvelle invitation "
            f"s'il rejoint le serveur à l'avenir."
        )
    else:
        await ctx.send(f"ℹ️ {user.mention} n'était pas dans la liste des membres déjà invités.")

# ==========================================
# COMMANDES — SYSTÈME DE WARNS / BIG WARNS
# ==========================================

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, user: discord.Member, *, reason: str = "Aucune raison fournie"):
    key = f"{ctx.guild.id}:{user.id}"
    entry = warn_data.get(key, {"warns": 0, "last_warn_at": 0, "big_warns": 0, "last_bigwarn_at": 0, "history": []})

    now = time.time()
    now_str = discord.utils.utcnow().strftime("%d/%m/%Y à %H:%M UTC")
    entry["warns"] = entry.get("warns", 0) + 1
    entry["last_warn_at"] = now
    entry.setdefault("history", []).append({
        "type": "warn", "reason": reason, "moderator_id": ctx.author.id, "at": now_str
    })

    escalated = False
    sanction_text = None
    if entry["warns"] >= WARNS_PER_BIGWARN:
        entry["warns"] -= WARNS_PER_BIGWARN
        entry["big_warns"] = entry.get("big_warns", 0) + 1
        entry["last_bigwarn_at"] = now
        entry["history"].append({
            "type": "bigwarn", "reason": f"Escalade automatique (3 warns) — {reason}",
            "moderator_id": ctx.author.id, "at": now_str
        })
        escalated = True

    warn_data[key] = entry
    await save_warn_data()

    if escalated:
        sanction_text = await apply_bigwarn_sanction(user, entry["big_warns"], reason, ctx.author)

    log_chan = bot.get_channel(WARN_LOG_CHANNEL_ID)
    if log_chan:
        embed = discord.Embed(title="⚠️ Warn", color=discord.Color.orange() if escalated else discord.Color.yellow())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Utilisateur",   value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Modérateur",    value=ctx.author.mention,              inline=True)
        embed.add_field(name="Warns simples", value=f"{entry['warns']}/{WARNS_PER_BIGWARN}", inline=True)
        embed.add_field(name="Big warns",     value=f"{entry.get('big_warns', 0)}/3",        inline=True)
        embed.add_field(name="Raison",        value=reason,                          inline=False)
        if escalated:
            embed.add_field(
                name="⚠️ Escalade automatique",
                value=f"3 warns atteints → Big Warn déclenché.\n{sanction_text or ''}",
                inline=False
            )
        await log_chan.send(embed=embed)

    if escalated:
        await ctx.send(f"⚠️ {user.mention} a atteint 3 warns → **Big Warn automatique** déclenché.\n{sanction_text}")
    else:
        await ctx.send(f"⚠️ {user.mention} averti ({entry['warns']}/{WARNS_PER_BIGWARN} avant big warn). Raison : {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def bigwarn(ctx, user: discord.Member, *, reason: str = "Aucune raison fournie"):
    key = f"{ctx.guild.id}:{user.id}"
    entry = warn_data.get(key, {"warns": 0, "last_warn_at": 0, "big_warns": 0, "last_bigwarn_at": 0, "history": []})

    now = time.time()
    entry["big_warns"] = entry.get("big_warns", 0) + 1
    entry["last_bigwarn_at"] = now
    entry.setdefault("history", []).append({
        "type": "bigwarn", "reason": reason, "moderator_id": ctx.author.id,
        "at": discord.utils.utcnow().strftime("%d/%m/%Y à %H:%M UTC")
    })

    warn_data[key] = entry
    await save_warn_data()

    sanction_text = await apply_bigwarn_sanction(user, entry["big_warns"], reason, ctx.author)

    log_chan = bot.get_channel(WARN_LOG_CHANNEL_ID)
    if log_chan:
        embed = discord.Embed(title="🚨 Big Warn (direct)", color=discord.Color.dark_orange())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Utilisateur", value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Modérateur",  value=ctx.author.mention,              inline=True)
        embed.add_field(name="Big warns",   value=f"{entry['big_warns']}/3",       inline=True)
        embed.add_field(name="Raison",      value=reason,                          inline=False)
        embed.add_field(name="Sanction",    value=sanction_text or "—",            inline=False)
        await log_chan.send(embed=embed)

    await ctx.send(f"🚨 Big Warn direct appliqué à {user.mention} ({entry['big_warns']}/3).\n{sanction_text}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings(ctx, user: discord.Member):
    key = f"{ctx.guild.id}:{user.id}"
    entry = warn_data.get(key, {"warns": 0, "big_warns": 0, "history": []})

    embed = discord.Embed(title=f"⚠️ Historique de {user.display_name}", color=discord.Color.orange())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Warns simples", value=f"{entry.get('warns', 0)}/{WARNS_PER_BIGWARN}", inline=True)
    embed.add_field(name="Big warns",     value=f"{entry.get('big_warns', 0)}/3",               inline=True)

    history = entry.get("history", [])[-10:]
    if history:
        lines = []
        for h in reversed(history):
            tag = "🚨 Big Warn" if h["type"] == "bigwarn" else "⚠️ Warn"
            lines.append(f"{tag} — {h['at']} par <@{h['moderator_id']}>\n> {h['reason']}")
        embed.add_field(name="Historique récent (10 derniers)", value="\n\n".join(lines)[:1024], inline=False)
    else:
        embed.add_field(name="Historique", value="Aucun warn enregistré.", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def unwarn(ctx, user: discord.Member):
    key = f"{ctx.guild.id}:{user.id}"
    entry = warn_data.get(key)
    if not entry or entry.get("warns", 0) <= 0:
        return await ctx.send(f"ℹ️ {user.mention} n'a aucun warn simple à retirer.")

    entry["warns"] -= 1
    history = entry.get("history", [])
    for i in range(len(history) - 1, -1, -1):
        if history[i]["type"] == "warn":
            history.pop(i)
            break
    await save_warn_data()
    await ctx.send(f"✅ Un warn simple retiré à {user.mention}. Nouveau total : {entry['warns']}/{WARNS_PER_BIGWARN}.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unbigwarn(ctx, user: discord.Member):
    key = f"{ctx.guild.id}:{user.id}"
    entry = warn_data.get(key)
    if not entry or entry.get("big_warns", 0) <= 0:
        return await ctx.send(f"ℹ️ {user.mention} n'a aucun big warn à retirer.")

    entry["big_warns"] -= 1
    history = entry.get("history", [])
    for i in range(len(history) - 1, -1, -1):
        if history[i]["type"] == "bigwarn":
            history.pop(i)
            break
    await save_warn_data()
    await ctx.send(
        f"✅ Un big warn retiré à {user.mention}. Nouveau total : {entry['big_warns']}/3.\n"
        f"⚠️ La sanction déjà appliquée (mute/ban) n'est pas annulée automatiquement — utilise "
        f"`{COMMAND_PREFIX}unmute` ou `{COMMAND_PREFIX}pardon` si besoin."
    )

# ==========================================
# VIEW — PIERRE FEUILLE CISEAUX
# ==========================================

class RPSView(discord.ui.View):
    CHOICES = {"🪨": "Pierre", "📄": "Feuille", "✂️": "Ciseaux"}
    WINS = {"🪨": "✂️", "📄": "🪨", "✂️": "📄"}

    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.picks = {}
        self.message = None

        for emoji in self.CHOICES:
            btn = discord.ui.Button(label=self.CHOICES[emoji], emoji=emoji, style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(emoji)
            self.add_item(btn)

    def _make_callback(self, emoji):
        async def callback(interaction: discord.Interaction):
            user = interaction.user
            if user.id not in (self.challenger.id, self.opponent.id):
                return await interaction.response.send_message("Ce duel ne te concerne pas !", ephemeral=True)
            if user.id in self.picks:
                return await interaction.response.send_message("Tu as déjà choisi !", ephemeral=True)
            self.picks[user.id] = emoji
            await interaction.response.send_message(f"Tu as choisi {emoji} — en attente de l'adversaire...", ephemeral=True)

            if len(self.picks) == 2:
                c_pick = self.picks[self.challenger.id]
                o_pick = self.picks[self.opponent.id]
                if c_pick == o_pick:
                    result = "⚖️ **Égalité !**"
                elif self.WINS[c_pick] == o_pick:
                    result = f"🏆 **{self.challenger.display_name}** gagne ! ({c_pick} bat {o_pick})"
                else:
                    result = f"🏆 **{self.opponent.display_name}** gagne ! ({o_pick} bat {c_pick})"

                embed = discord.Embed(title="🪨📄✂️ Résultat", color=discord.Color.blurple())
                embed.add_field(name=self.challenger.display_name, value=c_pick, inline=True)
                embed.add_field(name="VS", value="⚔️", inline=True)
                embed.add_field(name=self.opponent.display_name, value=o_pick, inline=True)
                embed.description = result
                self.stop()
                await interaction.message.edit(embed=embed, view=None)
        return callback

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

# ==========================================
# COMMANDES FUN & UTILES (MEMBRES)
# ==========================================

@bot.command()
async def rps(ctx, opponent: discord.Member):
    if opponent.bot or opponent == ctx.author:
        return await ctx.send("❌ Choisis un vrai adversaire !")
    embed = discord.Embed(
        title="🪨📄✂️ Pierre / Feuille / Ciseaux",
        description=(
            f"{ctx.author.mention} défie {opponent.mention} !\n"
            f"Les deux joueurs doivent cliquer sur leur choix (visible uniquement par eux)."
        ),
        color=discord.Color.blurple()
    )
    view = RPSView(ctx.author, opponent)
    msg = await ctx.send(embed=embed, view=view)
    view.message = msg

@bot.command()
async def roll(ctx, faces: int = 6):
    if faces < 2:
        return await ctx.send("❌ Le dé doit avoir au moins 2 faces.")
    if faces > 1000000:
        return await ctx.send("❌ Maximum 1 000 000 faces.")
    result = random.randint(1, faces)
    await ctx.send(f"🎲 {ctx.author.mention} lance un d{faces} et obtient **{result}** !")

@bot.command()
async def coinflip(ctx):
    result = random.choice(["🪙 **Pile !**", "🪙 **Face !**"])
    await ctx.send(f"{ctx.author.mention} — {result}")

@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    positives = [
        "Absolument !", "Sans aucun doute.", "Les signes pointent vers oui.",
        "Très certainement.", "Tu peux compter dessus.", "Oui, définitivement."
    ]
    neutres = [
        "Difficile à dire.", "Repose ta question plus tard.",
        "Je ne peux pas te le dire maintenant.", "Concentre-toi et redemande.",
        "Ne compte pas dessus... ou peut-être si ?"
    ]
    negatives = [
        "N'y compte pas.", "Mes sources disent non.",
        "Les perspectives ne sont pas bonnes.", "Très peu probable.", "Non."
    ]
    all_responses = [
        (positives, discord.Color.green()),
        (neutres, discord.Color.orange()),
        (negatives, discord.Color.red())
    ]
    pool, color = random.choice(all_responses)
    response = random.choice(pool)
    embed = discord.Embed(color=color)
    embed.add_field(name="🔮 Question", value=question, inline=False)
    embed.add_field(name="🎱 Réponse", value=response, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def roulette(ctx):
    if random.randint(1, 6) == 1:
        muted_role = ctx.guild.get_role(MUTED_ROLE_ID)
        membre_role = ctx.guild.get_role(ROLE_VERIFIED_ID)
        if muted_role:
            try:
                await ctx.author.add_roles(muted_role, reason="Roulette russe")
                if membre_role and membre_role in ctx.author.roles:
                    await ctx.author.remove_roles(membre_role)
                await ctx.send(
                    f"💀 **BANG !** {ctx.author.mention} est muté pendant 2 minutes... "
                    f"Pas de chance !"
                )
                await asyncio.sleep(120)
                await ctx.author.remove_roles(muted_role, reason="Roulette russe — fin")
                if membre_role:
                    await ctx.author.add_roles(membre_role)
            except:
                pass
        else:
            await ctx.send(f"💀 **BANG !** {ctx.author.mention} aurait été muté... mais le rôle est introuvable !")
    else:
        await ctx.send(f"🔫 *clic* — {ctx.author.mention} a survécu ! (1 chance sur 6)")

# ==========================================
# COMMANDES RANG & LEADERBOARD
# ==========================================

@bot.command()
async def rank(ctx, member: discord.Member = None):
    target = member or ctx.author
    uid = str(target.id)
    entry = xp_data.get(uid, {"xp": 0, "level": 0})
    total_xp = entry["xp"]
    level, xp_in_level, xp_needed = xp_progress(total_xp)

    bar_length = 20
    filled = int(bar_length * xp_in_level / xp_needed) if xp_needed > 0 else bar_length
    bar = "█" * filled + "░" * (bar_length - filled)

    sorted_users = sorted(xp_data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    rank_pos = next((i + 1 for i, (uid2, _) in enumerate(sorted_users) if uid2 == uid), "?")

    embed = discord.Embed(title=f"📊 Niveau de {target.display_name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Niveau",   value=f"**{level}**", inline=True)
    embed.add_field(name="XP Total", value=f"**{total_xp:,}**".replace(",", " "), inline=True)
    embed.add_field(name="Rang",     value=f"**#{rank_pos}**", inline=True)
    embed.add_field(
        name=f"Progression vers le niveau {level + 1}",
        value=f"`{bar}` {xp_in_level}/{xp_needed} XP",
        inline=False
    )

    next_role_level = next((lvl for lvl in sorted(LEVEL_ROLES) if lvl > level), None)
    if next_role_level:
        role = ctx.guild.get_role(LEVEL_ROLES[next_role_level])
        role_name = role.name if role else f"Niveau {next_role_level}"
        embed.add_field(name="Prochain rôle", value=f"{role_name} au niveau **{next_role_level}**", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    sorted_users = sorted(xp_data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]

    if not sorted_users:
        return await ctx.send("Aucune donnée d'XP pour le moment.")

    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (uid, entry) in enumerate(sorted_users):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"ID:{uid}"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lines.append(
            f"{medal} **{name}** — Niv. {entry.get('level', 0)} "
            f"({entry.get('xp', 0):,} XP)".replace(",", " ")
        )

    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    from datetime import datetime, timezone
    uid = str(ctx.author.id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = xp_data.get(uid, {"xp": 0, "level": 0, "streak": 0, "last_daily": None, "xp_today": 0})

    if entry.get("last_daily") == today:
        return await ctx.send(
            f"⏳ {ctx.author.mention} Tu as déjà réclamé ta récompense aujourd'hui. Reviens demain !"
        )

    yesterday = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                 .__class__.fromtimestamp(
                     datetime.now(timezone.utc).timestamp() - 86400, tz=timezone.utc
                 ).strftime("%Y-%m-%d"))
    last = entry.get("last_daily")
    if last == yesterday:
        entry["streak"] = entry.get("streak", 0) + 1
    else:
        entry["streak"] = 1

    streak = entry["streak"]
    bonus_xp = min(50 + (streak - 1) * 10, 200)
    entry["xp"] = entry.get("xp", 0) + bonus_xp
    entry["level"] = get_level(entry["xp"])
    entry["last_daily"] = today
    entry["xp_today"] = entry.get("xp_today", 0) + bonus_xp
    old_level = xp_data.get(uid, {}).get("level", 0)
    xp_data[uid] = entry
    await save_xp_to_discord()
    await check_level_up(ctx.guild, ctx.author, old_level, entry["level"])

    embed = discord.Embed(title="🎁 Récompense quotidienne", color=discord.Color.green())
    embed.add_field(name="XP gagné",  value=f"+**{bonus_xp}** XP", inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{streak}** jour(s)", inline=True)
    embed.add_field(name="XP Total",  value=f"**{entry['xp']:,}**".replace(",", " "), inline=True)
    if streak >= 7:
        embed.set_footer(text=f"🔥 Incroyable ! {streak} jours consécutifs !")
    await ctx.send(embed=embed)

@bot.command()
async def streak(ctx, member: discord.Member = None):
    from datetime import datetime, timezone
    target = member or ctx.author
    uid = str(target.id)
    entry = xp_data.get(uid, {})
    s = entry.get("streak", 0)
    last = entry.get("last_daily", "Jamais")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    claimed_today = last == today

    embed = discord.Embed(title=f"🔥 Streak de {target.display_name}", color=discord.Color.orange())
    embed.add_field(name="Jours consécutifs", value=f"**{s}** jour(s)", inline=True)
    embed.add_field(name="Dernier daily",     value=last,                inline=True)
    embed.add_field(
        name="Aujourd'hui",
        value="✅ Réclamé" if claimed_today else "❌ Pas encore réclamé",
        inline=True
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def top3(ctx):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    today_scores = []
    for uid, entry in xp_data.items():
        xp_today = entry.get("xp_today", 0) if entry.get("last_xp_date") == today else 0
        if xp_today > 0:
            member = ctx.guild.get_member(int(uid))
            if member:
                today_scores.append((member, xp_today))

    today_scores.sort(key=lambda x: x[1], reverse=True)
    top = today_scores[:3]

    if not top:
        return await ctx.send("Aucune activité enregistrée aujourd'hui pour le moment.")

    medals = ["🥇", "🥈", "🥉"]
    embed = discord.Embed(title="🏆 Top 3 du jour", color=discord.Color.gold())
    lines = [f"{medals[i]} **{m.display_name}** — {xp} XP aujourd'hui" for i, (m, xp) in enumerate(top)]
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command()
async def slots(ctx):
    uid = str(ctx.author.id)
    now = time.time()
    cooldown = 600
    last_used = slots_cooldowns.get(uid, 0)
    remaining = cooldown - (now - last_used)

    if remaining > 0:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        return await ctx.send(
            f"⏳ {ctx.author.mention} Attends encore **{mins}m {secs}s** avant de rejouer !"
        )

    slots_cooldowns[uid] = now
    symbols = ["🍒", "🍋", "🍇", "⭐", "💎", "🔔"]
    weights = [35, 25, 20, 12, 5, 3]
    s1, s2, s3 = random.choices(symbols, weights=weights, k=3)

    if s1 == s2 == s3:
        if s1 == "💎":
            result = "💰 **JACKPOT DIAMANT !** +500 XP"
            xp_gain = 500
        elif s1 == "⭐":
            result = "🌟 **JACKPOT ÉTOILE !** +200 XP"
            xp_gain = 200
        elif s1 == "🔔":
            result = "🔔 **JACKPOT CLOCHE !** +150 XP"
            xp_gain = 150
        else:
            result = f"🎉 **Jackpot {s1} !** +100 XP"
            xp_gain = 100
    elif s1 == s2 or s2 == s3 or s1 == s3:
        result = "✨ **Paire !** +30 XP"
        xp_gain = 30
    else:
        result = "😬 Pas de chance... +5 XP de consolation"
        xp_gain = 5

    entry = xp_data.get(uid, {"xp": 0, "level": 0, "streak": 0, "last_daily": None, "xp_today": 0})
    old_level = entry.get("level", 0)
    entry["xp"] = entry.get("xp", 0) + xp_gain
    entry["level"] = get_level(entry["xp"])
    xp_data[uid] = entry
    await save_xp_to_discord()
    await check_level_up(ctx.guild, ctx.author, old_level, entry["level"])

    embed = discord.Embed(title="🎰 Machine à sous", color=discord.Color.gold())
    embed.description = f"# {s1} {s2} {s3}\n{result}"
    embed.set_footer(text="Prochain tour dans 10 minutes")
    await ctx.send(embed=embed)

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member):
    seed = (user1.id + user2.id) % 101
    random.seed(seed)
    percent = random.randint(0, 100)
    random.seed()

    bar_length = 20
    filled = int(bar_length * percent / 100)
    bar = "❤️" * filled + "🖤" * (bar_length - filled)

    if percent >= 90:
        comment = "💍 Âmes sœurs !"
        color = discord.Color.red()
    elif percent >= 70:
        comment = "💕 Très bonne complicité !"
        color = discord.Color.magenta()
    elif percent >= 50:
        comment = "💛 Ça pourrait marcher..."
        color = discord.Color.yellow()
    elif percent >= 30:
        comment = "🌊 Pas évident..."
        color = discord.Color.blue()
    else:
        comment = "💔 Mieux vaut rester amis."
        color = discord.Color.dark_gray()

    embed = discord.Embed(title="💘 Ship-o-mètre", color=color)
    embed.description = (
        f"**{user1.display_name}** ❤️ **{user2.display_name}**\n\n"
        f"`{bar}`\n"
        f"**{percent}%** — {comment}"
    )
    await ctx.send(embed=embed)

@bot.command()
async def howgay(ctx, member: discord.Member = None):
    target = member or ctx.author
    seed = target.id % 101
    random.seed(seed)
    percent = random.randint(0, 100)
    random.seed()

    bar_length = 20
    filled = int(bar_length * percent / 100)
    bar = "🌈" * filled + "⬜" * (bar_length - filled)

    if percent == 100:
        comment = "💯 Maximum atteint 🏳️‍🌈"
    elif percent >= 80:
        comment = "C'est clairement établi 🌈"
    elif percent >= 50:
        comment = "La moitié du chemin est faite"
    elif percent >= 20:
        comment = "Un tout petit peu peut-être ?"
    else:
        comment = "Presque rien 😌"

    embed = discord.Embed(
        title=f"🌈 Gaymètre de {target.display_name}",
        color=discord.Color.from_rgb(255, 105, 180)
    )
    embed.description = f"`{bar}`\n**{percent}%** — {comment}"
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

# ==========================================
# VIEW — TIC-TAC-TOE
# ==========================================

class TicTacToeButton(discord.ui.Button):
    def __init__(self, row, col):
        super().__init__(style=discord.ButtonStyle.secondary, label="​", row=row)
        self.row_pos = row
        self.col_pos = col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current_player():
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        if self.label != "​":
            return await interaction.response.send_message("Cette case est déjà prise !", ephemeral=True)

        symbol = "❌" if view.turn == 0 else "⭕"
        self.label = symbol
        self.style = discord.ButtonStyle.danger if view.turn == 0 else discord.ButtonStyle.primary
        self.disabled = True
        view.board[self.row_pos][self.col_pos] = view.turn + 1
        view.turn = 1 - view.turn

        winner = view.check_winner()
        if winner:
            winner_member = view.players[winner - 1]
            for child in view.children:
                child.disabled = True
            embed = discord.Embed(
                title="🎮 Tic-Tac-Toe",
                description=f"🏆 **{winner_member.display_name}** a gagné !",
                color=discord.Color.green()
            )
            view.stop()
            await interaction.response.edit_message(embed=embed, view=view)
        elif view.is_draw():
            for child in view.children:
                child.disabled = True
            embed = discord.Embed(title="🎮 Tic-Tac-Toe", description="⚖️ **Match nul !**", color=discord.Color.orange())
            view.stop()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            embed = discord.Embed(
                title="🎮 Tic-Tac-Toe",
                description=f"Tour de **{view.current_player().display_name}** ({'❌' if view.turn == 0 else '⭕'})",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=view)


class TicTacToeView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=120)
        self.players = [player1, player2]
        self.turn = 0
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        self.message = None
        for r in range(3):
            for c in range(3):
                self.add_item(TicTacToeButton(r, c))

    def current_player(self):
        return self.players[self.turn]

    def check_winner(self):
        b = self.board
        lines = [
            [b[0][0], b[0][1], b[0][2]],
            [b[1][0], b[1][1], b[1][2]],
            [b[2][0], b[2][1], b[2][2]],
            [b[0][0], b[1][0], b[2][0]],
            [b[0][1], b[1][1], b[2][1]],
            [b[0][2], b[1][2], b[2][2]],
            [b[0][0], b[1][1], b[2][2]],
            [b[0][2], b[1][1], b[2][0]],
        ]
        for line in lines:
            if line[0] != 0 and line[0] == line[1] == line[2]:
                return line[0]
        return None

    def is_draw(self):
        return all(self.board[r][c] != 0 for r in range(3) for c in range(3))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

@bot.command()
async def tictactoe(ctx, opponent: discord.Member):
    if opponent.bot or opponent == ctx.author:
        return await ctx.send("❌ Choisis un vrai adversaire !")
    view = TicTacToeView(ctx.author, opponent)
    embed = discord.Embed(
        title="🎮 Tic-Tac-Toe",
        description=(
            f"**{ctx.author.display_name}** (❌) VS **{opponent.display_name}** (⭕)\n"
            f"Tour de **{ctx.author.display_name}** (❌)"
        ),
        color=discord.Color.blurple()
    )
    msg = await ctx.send(embed=embed, view=view)
    view.message = msg

# ==========================================
# VIEW — PENDU
# ==========================================

PENDU_WORDS = [
    "discord", "serveur", "giveaway", "moderation", "roblox", "communaute",
    "botixirya", "verification", "quarantaine", "rémunération", "programmation",
    "python", "commande", "permission", "administrateur", "leaderboard", "streak",
    "jackpot", "bouton", "categorie", "ticket", "sauvegarde", "statistiques"
]

PENDU_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]

class PenduView(discord.ui.View):
    def __init__(self, ctx, word: str):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.word = word.lower()
        self.guessed = set()
        self.errors = 0
        self.max_errors = 6
        self.message = None

    def display_word(self):
        return " ".join(c if c in self.guessed else "_" for c in self.word)

    def is_won(self):
        return all(c in self.guessed for c in self.word)

    def build_embed(self):
        color = discord.Color.green() if self.is_won() else (
            discord.Color.red() if self.errors >= self.max_errors else discord.Color.blurple()
        )
        embed = discord.Embed(title="🪢 Pendu", color=color)
        embed.add_field(name="Pendu",            value=PENDU_STAGES[self.errors], inline=False)
        embed.add_field(name="Mot",              value=f"`{self.display_word()}`", inline=False)
        guessed_str = " ".join(sorted(self.guessed)) if self.guessed else "—"
        embed.add_field(name="Lettres essayées", value=guessed_str,               inline=True)
        embed.add_field(name="Erreurs",          value=f"{self.errors}/{self.max_errors}", inline=True)
        return embed

@bot.command()
async def pendu(ctx):
    word = random.choice(PENDU_WORDS)
    game = PenduView(ctx, word)

    embed = game.build_embed()
    embed.set_footer(text="Tape une lettre dans le chat pour jouer !")
    msg = await ctx.send(embed=embed)
    game.message = msg

    def check(m):
        return (
            m.channel == ctx.channel
            and m.author == ctx.author
            and len(m.content) == 1
            and m.content.isalpha()
        )

    while game.errors < game.max_errors and not game.is_won():
        try:
            guess_msg = await bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            await msg.edit(embed=discord.Embed(
                title="🪢 Pendu",
                description=f"⏱️ Temps écoulé ! Le mot était **{word}**.",
                color=discord.Color.orange()
            ))
            return

        letter = guess_msg.content.lower()
        try:
            await guess_msg.delete()
        except:
            pass

        if letter in game.guessed:
            continue

        game.guessed.add(letter)
        if letter not in game.word:
            game.errors += 1

        embed = game.build_embed()
        if game.is_won():
            embed.description = f"🎉 Bravo **{ctx.author.display_name}** ! Le mot était **{word}** !"
        elif game.errors >= game.max_errors:
            embed.description = f"💀 Perdu ! Le mot était **{word}**."
        else:
            embed.set_footer(text="Tape une lettre dans le chat pour jouer !")

        await msg.edit(embed=embed)

# ==========================================
# COMMANDES BACKUP
# ==========================================

@bot.command()
async def COMMANDSON(ctx):
    global commands_on_backup
    if ctx.guild.id != BACKUP_SERVER_ID:
        return
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Réservé au propriétaire.")
    commands_on_backup = True
    await ctx.send("✅ Toutes les commandes sont maintenant actives sur ce serveur.")

@bot.command()
async def backup(ctx):
    if ctx.guild.id != BACKUP_SERVER_ID:
        return await ctx.send("❌ Cette commande ne fonctionne que sur le serveur de backup.")
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Réservé au propriétaire.")

    main_guild = bot.get_guild(MAIN_SERVER_ID)
    if not main_guild:
        return await ctx.send("❌ Impossible d'accéder au serveur principal.")

    backup_guild = ctx.guild
    status_msg = await ctx.send("🔄 Démarrage de la backup...")

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
                    name=role.name, color=role.color, permissions=role.permissions,
                    hoist=role.hoist, mentionable=role.mentionable, reason="Botixirya Backup"
                )
                role_map[role.id] = new_role
                existing_roles[role.name] = new_role
                await asyncio.sleep(0.4)
            except Exception as e:
                await ctx.send(f"⚠️ Rôle `{role.name}` ignoré : {e}")

    await status_msg.edit(content="🔄 Copie des catégories en cours...")
    category_map = {}
    existing_channels = {c.name: c for c in backup_guild.channels}

    for category in main_guild.categories:
        if category.name in existing_channels:
            category_map[category.id] = existing_channels[category.name]
        else:
            try:
                new_cat = await backup_guild.create_category(name=category.name, reason="Botixirya Backup")
                category_map[category.id] = new_cat
                existing_channels[category.name] = new_cat
                await asyncio.sleep(0.4)
            except Exception as e:
                await ctx.send(f"⚠️ Catégorie `{category.name}` ignorée : {e}")

    await status_msg.edit(content="🔄 Copie des salons en cours...")

    def convert_overwrites(source_overwrites: dict) -> dict:
        result = {}
        for target, perms in source_overwrites.items():
            if isinstance(target, discord.Role):
                new_target = backup_guild.default_role if target.is_default() else role_map.get(target.id)
            else:
                new_target = None
            if new_target:
                result[new_target] = perms
        return result

    for channel in main_guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue
        if channel.name in existing_channels:
            continue
        cat = category_map.get(channel.category_id) if channel.category_id else None
        overwrites = convert_overwrites(channel.overwrites)
        try:
            if isinstance(channel, discord.TextChannel):
                await backup_guild.create_text_channel(
                    name=channel.name, category=cat, topic=channel.topic or "",
                    overwrites=overwrites, reason="Botixirya Backup"
                )
            elif isinstance(channel, discord.VoiceChannel):
                await backup_guild.create_voice_channel(
                    name=channel.name, category=cat,
                    overwrites=overwrites, reason="Botixirya Backup"
                )
            await asyncio.sleep(0.4)
        except Exception as e:
            await ctx.send(f"⚠️ Salon `{channel.name}` ignoré : {e}")

    await status_msg.edit(content="✅ **Backup terminée !**\nRôles, catégories et salons copiés depuis le serveur principal.")

# ==========================================

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
