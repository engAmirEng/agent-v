from ._setup import env

# telebot
# ------------------------------------------------------------------------------
BOT_TOKEN = env.str("BOT_TOKEN")
PROXY_URL = env.str("PROXY_URL", None)


# hiddify
# ------------------------------------------------------------------------------
HIDDIFY_URL = env.str("HIDDIFY_URL")
HIDDIFY_SECRET = env.str("HIDDIFY_SECRET")
HIDDIFY_AGENT_UUID = env.str("HIDDIFY_AGENT_UUID")
