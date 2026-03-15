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
from flask import Flask
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
GIVEAWAY_FILE = "giveaways.json"

BAN_LOG_CHANNEL_ID = 1481201790375563498         # Logs bans
KICK_LOG_CHANNEL_ID = 1481202403574284310        # Logs kicks
MUTE_LOG_CHANNEL_ID = 1481202820500684841        # Logs mutes
MUTED_ROLE_ID = 1481203639107325983              # Rôle Muted
BANS_FILE = "bans.json"

OWNER_ID = 1339332485930160189                   # ID du propriétaire
MAIN_SERVER_ID = 1472951773026062482             # Serveur principal
BACKUP_SERVER_ID = 1481205788566618115           # Serveur de backup

RAID_THRESHOLD = 3                               # Nb suppressions déclenchant l'anti-raid
RAID_WINDOW = 30                                 # Fenêtre de temps en secondes

ROLE_BACKUP_CHANNEL_ID = 1481211118843203647     # Sauvegarde des rôles avant quarantaine
RAID_LOG_CHANNEL_ID = 1481211696109326466        # Logs des tentatives de raid

TICKET_MEMORY_CHANNEL_ID = 1482417571549544690   # Mémoire des configs de tickets
# ==========================================

# --- État global ---
current_count = 0
last_user_id = None
active_counting_channel = 0
commands_on_backup = False
deletion_tracker = {}    # {guild_id: {user_id: {"channels": [...], "roles": [...]}}}
quarantined_users = {}   # {user_id: [role_ids]}
safe_users = set()       # Utilisateurs exclus de la surveillance anti-raid
ticket_configs = {}      # {actual_channel_id: {category_id, logs_channel_id, channel_message, inside_ticket_message}}

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
# SYSTÈME DE TICKETS — MÉMOIRE
# ==========================================

async def save_ticket_config(config: dict):
    """
    Sauvegarde une config de ticket dans le salon mémoire.
    Format : TICKET_CONFIG|<json>
    Remplace l'entrée existante si l'actual_channel_id est déjà présent.
    """
    mem_chan = bot.get_channel(TICKET_MEMORY_CHANNEL_ID)
    if not mem_chan:
        return
    # Supprimer l'ancienne entrée pour ce channel si elle existe
    async for msg in mem_chan.history(limit=200):
        if msg.content.startswith("TICKET_CONFIG|"):
            try:
                old = json.loads(msg.content[len("TICKET_CONFIG|"):])
                if old.get("actual_channel_id") == config["actual_channel_id"]:
                    await msg.delete()
                    break
            except:
                pass
    await mem_chan.send(f"TICKET_CONFIG|{json.dumps(config, ensure_ascii=False)}")

async def load_ticket_configs():
    """Charge toutes les configs de tickets depuis le salon mémoire au démarrage."""
    global ticket_configs
    mem_chan = bot.get_channel(TICKET_MEMORY_CHANNEL_ID)
    if not mem_chan:
        return
    async for msg in mem_chan.history(limit=200):
        if msg.content.startswith("TICKET_CONFIG|"):
            try:
                config = json.loads(msg.content[len("TICKET_CONFIG|"):])
                cid = config["actual_channel_id"]
                ticket_configs[cid] = config
            except:
                pass

# ==========================================
# ANTI-RAID
# ==========================================

async def quarantine_user(guild, member, silent: bool = False):
    """
    Retire tous les rôles et bloque toutes les permissions.
    Seul le propriétaire est immunisé.
    silent=True : utilisé par <aav>unsafe → pas de log de raid, juste la mise en quarantaine.
    silent=False : utilisé par l'anti-raid automatique → log complet dans le salon raid.
    """
    if member.id == OWNER_ID:
        return

    user_id = str(member.id)
    roles_avant = [r.id for r in member.roles if r != guild.default_role]
    quarantined_users[user_id] = roles_avant

    # --- Sauvegarde des rôles dans le salon dédié + bouton de restauration ---
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

    # --- Retrait des rôles ---
    try:
        await member.edit(roles=[], reason="Quarantaine" if silent else "Anti-Raid : suppressions en masse détectées")
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
                reason="Quarantaine manuelle" if silent else "Anti-Raid"
            )
        except:
            pass

    # --- Logs selon le mode ---
    if not silent:
        # Raid automatique → log complet dans le salon raid
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
        # Quarantaine manuelle → simple log général, pas de faux raid
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(
                f"🔒 **Quarantaine manuelle** : {member.mention} (`{member.id}`) — rôles retirés, accès révoqué."
            )

async def track_deletion(guild, user, dtype):
    """Suit les suppressions. dtype : 'channels' ou 'roles'. Propriétaire et utilisateurs safe sont immunisés."""
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
    """
    Bouton posté dans le salon de sauvegarde des rôles.
    Permet au propriétaire de restaurer les rôles d'un utilisateur en quarantaine
    sans avoir besoin de le @mentionner (il ne voit aucun salon).
    custom_id encode guild_id:user_id pour la persistance après redémarrage.
    """
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
            return await interaction.response.send_message(
                "❌ Réservé au propriétaire.", ephemeral=True
            )

        # Extraction des IDs depuis le custom_id du bouton cliqué
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
            # Tenter de fetch si pas en cache
            try:
                member = await guild.fetch_member(user_id)
            except:
                return await interaction.response.send_message(
                    "❌ Membre introuvable (il a peut-être quitté le serveur).", ephemeral=True
                )

        # Lecture des rôles depuis le contenu du message (ligne ROLE_BACKUP|...)
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

        # Fallback sur la mémoire en RAM si le message ne contient plus les rôles
        if not found_roles:
            for rid in quarantined_users.get(str(user_id), []):
                role = guild.get_role(rid)
                if role:
                    found_roles.append(role)

        # Restauration des rôles
        try:
            await member.edit(roles=found_roles, reason=f"Restauration par {interaction.user}")
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erreur restauration rôles : {e}", ephemeral=True)

        # Suppression des overrides de permissions
        for channel in guild.channels:
            try:
                overwrite = channel.overwrites_for(member)
                if overwrite.send_messages is False or overwrite.read_messages is False:
                    await channel.set_permissions(member, overwrite=None)
            except:
                pass

        # Nettoyage mémoire
        quarantined_users.pop(str(user_id), None)

        # Log dans le salon raid
        raid_log_chan = bot.get_channel(RAID_LOG_CHANNEL_ID)
        if raid_log_chan:
            roles_names = ", ".join(r.name for r in found_roles) or "aucun"
            await raid_log_chan.send(
                f"✅ **Rôles restaurés** : {member.mention} (`{member.id}`)\n"
                f"Par : {interaction.user.mention}\n"
                f"Rôles : {roles_names}"
            )

        # Désactivation du bouton après usage
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
# VIEWS — TICKETS
# ==========================================

class TicketCreateView(discord.ui.View):
    """
    Vue persistante avec le bouton 'Create Ticket'.
    Le custom_id encode l'ID du salon de création pour retrouver la config.
    """
    def __init__(self, actual_channel_id: int):
        super().__init__(timeout=None)
        self.actual_channel_id = actual_channel_id
        btn = discord.ui.Button(
            label="🎫 Create Ticket",
            style=discord.ButtonStyle.blurple,
            custom_id=f"create_ticket:{actual_channel_id}"
        )
        btn.callback = self.create_ticket_callback
        self.add_item(btn)

    async def create_ticket_callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Récupération de la config via l'ID du salon encodé dans le custom_id
        channel_id = int(interaction.data["custom_id"].split(":")[1])
        config = ticket_configs.get(channel_id)
        if not config:
            return await interaction.response.send_message(
                "❌ Configuration du ticket introuvable.", ephemeral=True
            )

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        ticket_channel_name = f"ticket-{user.name.lower().replace(' ', '-')}"
        existing = discord.utils.get(guild.text_channels, name=ticket_channel_name)
        if existing:
            return await interaction.response.send_message(
                f"❌ Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True
            )

        # Catégorie cible
        category = guild.get_channel(config["category_id"])

        # Création du salon ticket avec permissions restreintes
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        # Donner accès aux admins
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

        # Message d'accueil dans le ticket
        embed = discord.Embed(
            description=config["inside_ticket_message"],
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Ticket de {user.display_name}")
        await ticket_channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {ticket_channel.mention}", ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    """Vue persistante avec le bouton 'Close Ticket'."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        # Lecture des infos depuis le topic du salon
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

        # Seuls le créateur du ticket, les admins et le propriétaire peuvent fermer
        is_admin = user.guild_permissions.administrator
        is_owner = user.id == OWNER_ID
        is_creator = user.id == ticket_owner_id

        if not (is_admin or is_owner or is_creator):
            return await interaction.response.send_message(
                "❌ Tu n'as pas la permission de fermer ce ticket.", ephemeral=True
            )

        await interaction.response.send_message("🔒 Fermeture du ticket en cours...")

        # --- Collecte des messages pour les logs ---
        messages = []
        async for msg in channel.history(limit=500, oldest_first=True):
            if msg.author == guild.me and msg.components:
                continue  # Ignorer les messages avec boutons (les messages du bot)
            if msg.content:
                messages.append(f"{msg.author.display_name}:\n{msg.content}\n")

        log_content = "\n".join(messages) if messages else "(aucun message)"

        # --- Envoi du fichier TXT dans le salon de logs ---
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

        # Suppression du salon après un court délai
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
    bot.add_view(CloseTicketView())

    # Ré-enregistrement des vues de restauration de rôles persistantes
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

    # Restauration du score depuis le salon DB
    db_chan = bot.get_channel(DB_CHANNEL_ID)
    if db_chan:
        async for message in db_chan.history(limit=50):
            if "BACKUP_COUNT|" in message.content:
                parts = message.content.split("|")
                current_count = int(parts[1])
                last_user_id = int(parts[2]) if parts[2] != "None" else None
                active_counting_channel = int(parts[3])
                break

    # Restauration des configs de tickets + enregistrement des vues persistantes
    await load_ticket_configs()
    for channel_id, config in ticket_configs.items():
        bot.add_view(TicketCreateView(channel_id))

    if not check_giveaways.is_running():
        check_giveaways.start()
    if not check_bans.is_running():
        check_bans.start()

    await send_log(f"✅ **Botixirya** prêt. Score : `{current_count}` | Configs tickets : `{len(ticket_configs)}`")

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
        f"**{COMMAND_PREFIX}msgdel [nb] (@user)** : Supprime des messages.\n"
        f"**{COMMAND_PREFIX}ban @user [min] [raison]** : Bannit (0 = permanent).\n"
        f"**{COMMAND_PREFIX}pardon @user** : Débannit.\n"
        f"**{COMMAND_PREFIX}kick @user [raison]** : Expulse.\n"
        f"**{COMMAND_PREFIX}mute @user [raison]** : Mute.\n"
        f"**{COMMAND_PREFIX}unmute @user** : Unmute.\n"
        f"**{COMMAND_PREFIX}safe @user** : Lève la quarantaine + whiteliste (exclut de l'anti-raid) **(owner only)**.\n"
        f"**{COMMAND_PREFIX}removesafe @user** : Remet sous surveillance anti-raid **(owner only)**.\n"
        f"→ La restauration des rôles se fait via le bouton dans <#{ROLE_BACKUP_CHANNEL_ID}>."
    ), inline=False)
    embed.add_field(name="🎫 Tickets", value=(
        f"**{COMMAND_PREFIX}TicketCreatingChannel [category_id] [logs_id] [Message] [InsideMessage] [channel_id]**\n"
        f"→ Configure un point de création de tickets dans le salon spécifié."
    ), inline=False)
    embed.add_field(name="🎁 Giveaway", value=(
        f"**{COMMAND_PREFIX}giveaway [min] [gagnants] [prix] [condition]**"
    ), inline=False)
    embed.add_field(name="💾 Backup", value=(
        f"**{COMMAND_PREFIX}backup** : Copie le serveur principal → backup *(backup only)*.\n"
        f"**{COMMAND_PREFIX}COMMANDSON** : Active toutes les commandes sur le serveur backup *(owner only)*."
    ), inline=False)
    await ctx.send(embed=embed)

# --- Système ---

@bot.command()
@commands.has_permissions(administrator=True)
async def kill(ctx):
    """Éteint le bot (score sauvegardé en temps réel)."""
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
    """Lève la quarantaine, restaure les rôles en mémoire et exclut l'utilisateur de la surveillance anti-raid. (Owner uniquement)"""
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Commande réservée au propriétaire.")

    user_id = str(user.id)

    # Ajout à la liste blanche anti-raid
    safe_users.add(user.id)

    # Levée des overrides de permissions
    for channel in ctx.guild.channels:
        try:
            overwrite = channel.overwrites_for(user)
            if overwrite.send_messages is False or overwrite.read_messages is False:
                await channel.set_permissions(user, overwrite=None)
        except:
            pass

    # Restauration des rôles si en quarantaine
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
    """Remet un utilisateur sous surveillance anti-raid (inverse de safe). (Owner uniquement)"""
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
    """
    Configure un point de création de tickets.
    Format : [category_id] [logs_channel_id] [ChannelMessage] [InsideTicketMessage] [actual_channel_id]
    """
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

    # Vérifications
    category = ctx.guild.get_channel(category_id)
    if not category or not isinstance(category, discord.CategoryChannel):
        return await ctx.send(f"❌ Catégorie introuvable avec l'ID `{category_id}`.")

    actual_channel = ctx.guild.get_channel(actual_channel_id)
    if not actual_channel:
        return await ctx.send(f"❌ Salon introuvable avec l'ID `{actual_channel_id}`.")

    logs_channel = ctx.guild.get_channel(logs_channel_id)
    if not logs_channel:
        return await ctx.send(f"❌ Salon de logs introuvable avec l'ID `{logs_channel_id}`.")

    # Sauvegarde de la config
    config = {
        "actual_channel_id": actual_channel_id,
        "category_id": category_id,
        "logs_channel_id": logs_channel_id,
        "channel_message": channel_message,
        "inside_ticket_message": inside_ticket_message
    }
    ticket_configs[actual_channel_id] = config
    await save_ticket_config(config)

    # Enregistrement de la vue persistante
    view = TicketCreateView(actual_channel_id)
    bot.add_view(view)

    # Envoi du message dans le salon cible
    embed = discord.Embed(
        description=channel_message,
        color=discord.Color.blurple()
    )
    await actual_channel.send(embed=embed, view=view)

    await ctx.send(
        f"✅ Système de tickets configuré dans {actual_channel.mention}.\n"
        f"Catégorie : `{category.name}` | Logs : {logs_channel.mention}"
    )

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
    """Copie la structure du serveur principal vers ce serveur. (backup server only)"""
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
