"""Live bindings to existing module settings; opening this catalog never rewrites them."""
import json
from sqlalchemy import select
from rcon.models import enter_session, MessageTemplate, PlayerMessageTranslation
from rcon.player_messages import source_hash, stored_key, template_revision, fields

TRANSLATIONS = {
    'no_leader.warning': (
        'Achtung, {player_name}! Dein Squad ({squad_name}) hat keinen Squadleader. Nach {max_warnings} Warnungen folgen Bestrafungen und anschließend ein Kick. Bisherige Warnungen: {received_warnings}.\nNächste Prüfung in {next_check_seconds}s.',
        'Attention, {player_name} ! Votre escouade ({squad_name}) n’a pas de chef. Après {max_warnings} avertissements, des sanctions puis une expulsion suivront. Avertissements reçus : {received_warnings}.\nProchaine vérification dans {next_check_seconds}s.'),
    'no_leader.punish': (
        'Dein Squad ({squad_name}) benötigt einen Squadleader.\nAutomatische Bestrafung ({received_punishes}/{max_punishes}).\nNächste Prüfung in {next_check_seconds} Sekunden.',
        'Votre escouade ({squad_name}) doit avoir un chef.\nSanction automatique ({received_punishes}/{max_punishes}).\nProchaine vérification dans {next_check_seconds} secondes.'),
    'no_leader.kick': (
        'Dein Squad ({squad_name}) benötigt einen Squadleader. Die Schonfrist von {kick_grace_period}s ist abgelaufen. Die vorherigen Warnungen wurden nicht befolgt.',
        'Votre escouade ({squad_name}) doit avoir un chef. Le délai de {kick_grace_period}s est écoulé. Les avertissements précédents n’ont pas été suivis.'),
    'solo_tank.warning': (
        'Achtung, {player_name}! Auf diesem Server sind keine Solopanzer erlaubt. Nach {max_warnings} Warnungen folgen Bestrafungen und anschließend ein Kick. Bisherige Warnungen: {received_warnings}.\nNächste Prüfung in {next_check_seconds}s.',
        'Attention, {player_name} ! Les chars en solo sont interdits. Après {max_warnings} avertissements, des sanctions puis une expulsion suivront. Avertissements reçus : {received_warnings}.\nProchaine vérification dans {next_check_seconds}s.'),
    'solo_tank.punish': (
        'Du hast gegen die Solopanzer-Regel verstoßen.\nAutomatische Bestrafung ({received_punishes}/{max_punishes}). Nächste Prüfung in {next_check_seconds}s.',
        'Vous avez enfreint la règle interdisant les chars en solo.\nSanction automatique ({received_punishes}/{max_punishes}). Prochaine vérification dans {next_check_seconds}s.'),
    'solo_tank.kick': (
        'Du hast gegen die Solopanzer-Regel verstoßen. Die Schonfrist von {kick_grace_period}s ist abgelaufen. Die vorherigen Warnungen wurden nicht befolgt.',
        'Vous avez enfreint la règle interdisant les chars en solo. Le délai de {kick_grace_period}s est écoulé. Les avertissements précédents n’ont pas été suivis.'),
    'level.warning': (
        'Achtung, {player_name}! Du erfüllst diese Levelregel nicht: {violation}\nNach {max_warnings} Warnungen folgen Bestrafungen und anschließend ein Kick. Bisherige Warnungen: {received_warnings}. Nächste Prüfung in {next_check_seconds}s.',
        'Attention, {player_name} ! Vous ne respectez pas cette règle de niveau : {violation}\nAprès {max_warnings} avertissements, des sanctions puis une expulsion suivront. Avertissements reçus : {received_warnings}. Prochaine vérification dans {next_check_seconds}s.'),
    'level.punish': (
        'Du hast gegen diese Levelregel verstoßen: {violation}.\nAutomatische Bestrafung ({received_punishes}/{max_punishes}). Nächste Prüfung in {next_check_seconds} Sekunden.',
        'Vous avez enfreint cette règle de niveau : {violation}.\nSanction automatique ({received_punishes}/{max_punishes}). Prochaine vérification dans {next_check_seconds} secondes.'),
    'level.kick': (
        'Du hast gegen diese Levelregel verstoßen: {violation}. Die Schonfrist von {kick_grace_period}s ist abgelaufen. Die vorherigen Warnungen wurden nicht befolgt.',
        'Vous avez enfreint cette règle de niveau : {violation}. Le délai de {kick_grace_period}s est écoulé. Les avertissements précédents n’ont pas été suivis.'),
    'level.force_kick': ('Du erfüllst diese Levelregel nicht: {violation}.', 'Vous ne respectez pas cette règle de niveau : {violation}.'),
    'level.min_level': ('Zugang erst ab Level {level}.', 'Accès à partir du niveau {level}.'),
    'level.max_level': ('Zugang höchstens bis Level {level}.', 'Accès jusqu’au niveau {level} maximum.'),
    'level.violation': ('Für {role} wird mindestens Level {level} benötigt.', 'Le rôle {role} exige au moins le niveau {level}.'),
    'level.announcement': (
        'Auf diesem Server gelten Levelregeln.\n\n{min_level_msg}{max_level_msg}{level_thresholds_msg}\nDanke für dein Verständnis.',
        'Ce serveur applique des règles de niveau.\n\n{min_level_msg}{max_level_msg}{level_thresholds_msg}\nMerci de votre compréhension.'),
    'seeding.warning': (
        'Achtung, {player_name}! Du verstößt gegen diese Seeding-Regel: {violation}\nNach {max_warnings} Warnungen folgen Bestrafungen und anschließend ein Kick. Bisherige Warnungen: {received_warnings}. Nächste Prüfung in {next_check_seconds}s.',
        'Attention, {player_name} ! Vous enfreignez cette règle de remplissage : {violation}\nAprès {max_warnings} avertissements, des sanctions puis une expulsion suivront. Avertissements reçus : {received_warnings}. Prochaine vérification dans {next_check_seconds}s.'),
    'seeding.punish': (
        'Du hast gegen diese Seeding-Regel verstoßen: {violation}.\nAutomatische Bestrafung ({received_punishes}/{max_punishes}). Nächste Prüfung in {next_check_seconds} Sekunden.',
        'Vous avez enfreint cette règle de remplissage : {violation}.\nSanction automatique ({received_punishes}/{max_punishes}). Prochaine vérification dans {next_check_seconds} secondes.'),
    'seeding.kick': (
        'Du hast gegen die Seeding-Regeln verstoßen. Die Schonfrist von {kick_grace_period}s ist abgelaufen. Die vorherigen Warnungen wurden nicht befolgt.',
        'Vous avez enfreint les règles de remplissage. Le délai de {kick_grace_period}s est écoulé. Les avertissements précédents n’ont pas été suivis.'),
    'seeding.announcement': (
        'Der Server wird gefüllt. Dabei gelten besondere Regeln.\n\n- {disallowed_roles} sind bis {disallowed_roles_max_players} Spielern nicht erlaubt.\n- {disallowed_weapons} sind bis {disallowed_weapons_max_players} Spielern nicht erlaubt.\n\nDanke fürs Mithelfen!',
        'Le serveur est en phase de remplissage. Des règles particulières s’appliquent.\n\n- {disallowed_roles} sont interdits jusqu’à {disallowed_roles_max_players} joueurs.\n- {disallowed_weapons} sont interdits jusqu’à {disallowed_weapons_max_players} joueurs.\n\nMerci de votre aide !'),
    'seeding.disallowed_roles.violation': ('{role} ist während des Seedings nicht erlaubt.', '{role} est interdit pendant le remplissage.'),
    'seeding.disallowed_weapons.violation': ('{weapon} ist während des Seedings nicht erlaubt.', '{weapon} est interdit pendant le remplissage.'),
    'seeding.enforce_cap_fight.violation': ('Während des Seedings darf der vierte Punkt nicht angegriffen werden.', 'Il est interdit d’attaquer le quatrième point pendant le remplissage.'),
}


def _at(model, path):
    for part in path.split('.'):
        model = getattr(model, part)
    return model


def autobalancer_definition(config,key):
    from rcon.autobalancer.messages import SYSTEM, SYSTEM_FR
    variants={locale:(SYSTEM_FR[key] if locale=='fr' else SYSTEM[key][0 if locale=='de' else 1])
                     if key in SYSTEM else getattr(getattr(config,'messages' if locale=='de' else 'messages_'+locale),key)
              for locale in ('de','en','fr')}
    return {'key':'autobalancer.'+key,'source':variants['de'],'defaults':variants,
            'source_hash':source_hash(json.dumps(variants,sort_keys=True,ensure_ascii=False)),
            'group':'autobalancer','action':'message'}


def bindings():
    from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
    from rcon.user_config.auto_mod_solo_tank import AutoModNoSoloTankUserConfig
    from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
    from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
    result = []
    for prefix, cls in [('no_leader',AutoModNoLeaderUserConfig),('solo_tank',AutoModNoSoloTankUserConfig),
                         ('level',AutoModLevelUserConfig),('seeding',AutoModSeedingUserConfig)]:
        current, default = cls.load_from_db(), cls()
        for suffix in ('warning','punish','kick','force_kick','min_level','max_level','violation','announcement',
                       'disallowed_roles.violation','disallowed_weapons.violation','enforce_cap_fight.violation'):
            path = suffix + '_message'
            try: source, original = _at(current,path), _at(default,path)
            except AttributeError: continue
            variants = {}
            if source == original and prefix+'.'+suffix in TRANSLATIONS:
                de,fr = TRANSLATIONS[prefix+'.'+suffix]
                variants = {'de':de,'en':source,'fr':fr}
            result.append({'key':'automod.'+prefix+'.'+suffix,'source':source,'defaults':variants,
                           'group':'automod','action':suffix.split('.')[-1]})
    from rcon.user_config.name_kicks import NameKickUserConfig
    from rcon.user_config.vac_game_bans import VacGameBansUserConfig
    from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig
    for name,cls,field,de,fr in [
        ('name.kick',NameKickUserConfig,'kick_reason','Dein Spielername ist nicht erlaubt.','Votre pseudonyme est interdit.'),
        ('vac.reason',VacGameBansUserConfig,'ban_on_vac_history_reason','VAC-/Spielsperre in der Vergangenheit (vor {DAYS_SINCE_LAST_BAN} Tagen).','Antécédent de bannissement VAC/jeu (il y a {DAYS_SINCE_LAST_BAN} jours).'),
        ('teamkill.reason',BanTeamKillOnConnectUserConfig,'message','Deine erste Aktion auf dem Server war ein Teamkill. Deshalb wurdest du gesperrt.','Votre première action sur le serveur était un tir allié mortel. Vous avez donc été banni.')]:
        source=getattr(cls.load_from_db(),field)
        variants={'de':de,'en':source,'fr':fr} if source==getattr(cls(),field) else {}
        result.append({'key':'automod.'+name,'source':source,'defaults':variants,'group':'automod','action':'reason'})
    config = AutobalancerUserConfig.load_from_db()
    from rcon.autobalancer.messages import SYSTEM, SYSTEM_FR
    for key in sorted(set(SYSTEM) | set(type(config.messages).model_fields)):
        result.append(autobalancer_definition(config,key))
    from rcon.autobalancer.feedback import ended_message
    for uncertain in (False,True):
        name = 'uncertain' if uncertain else 'ended'
        source = ended_message('', switch_uncertain=uncertain)
        result.append({'key':'autobalancer.legacy_'+name,'source':source,
                       'defaults':{'de':SYSTEM[name][0],'en':SYSTEM[name][1],'fr':SYSTEM_FR[name]},
                       'group':'autobalancer','action':'message'})
    settings = RconServerSettingsUserConfig.load_from_db()
    from rcon.user_config.rcon_server_settings import WINDOWS_STORE_PLAYER_MESSAGE
    source=settings.windows_store_players.player_message
    result.append({'key':'automod.windows_store.reason','source':source,
                   'defaults':{'de':'Windows-Store-Spieler sind auf diesem Server nicht zugelassen.',
                               'en':source,'fr':'Les joueurs du Windows Store ne sont pas autorisés sur ce serveur.'} if source==WINDOWS_STORE_PLAYER_MESSAGE else {},
                   'group':'automod','action':'reason'})
    for field in ('message_header','message_footer'):
        result.append({'key':'messages.'+field,'source':getattr(settings.message_enhancements,field),
                       'defaults':{},'group':'moderation','action':'message'})
    return result


def catalog():
    definitions = bindings()
    with enter_session() as sess:
        for row in sess.scalars(select(MessageTemplate).where(MessageTemplate.category.in_(['REASON','MESSAGE']))):
            definitions.append({'key':f'manual:{row.id}','source':row.content,'title':row.title,
                                'defaults':{},'group':'moderation','action':'reason' if row.category.value=='REASON' else 'message'})
        rows = {r.key:r for r in sess.scalars(select(PlayerMessageTranslation))}
        for item in definitions:
            saved = rows.get(stored_key(item['key']))
            item.setdefault('source_hash',source_hash(item['source']))
            matches = bool(saved and saved.source_hash==item['source_hash'] and saved.source_content==item['source'])
            item['translations'] = {**item['defaults'], **(saved.translations if matches else {})}
            item['saved_translations'] = saved.translations if saved else {}
            item['needs_review'] = bool(saved and not matches)
            item['revision'] = template_revision(item['source'],saved,item['source_hash'])
            try: item['placeholders'] = sorted(name for name,_,_ in fields(item['source']))
            except ValueError: item['placeholders'] = []
    return definitions
