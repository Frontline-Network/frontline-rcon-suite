from rcon.discord import make_allowed_mentions
from rcon.user_config.webhooks import DiscordMentionWebhook


def test_validated_user_and_role_mentions_are_allowed():
    config = DiscordMentionWebhook(url='https://discord.com/api/webhooks/123/token',
        user_mentions=['<@123456>'], role_mentions=['<@&987654>'])
    assert make_allowed_mentions(config.user_mentions, config.role_mentions) == {
        'users': ['123456'], 'roles': ['987654']}


def test_old_user_syntax_is_supported_and_suffixes_are_not_allowed():
    assert make_allowed_mentions(['<@!123>', '<@456>extra'], ['<@&789>extra']) == {'users': ['123']}
