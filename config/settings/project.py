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

# seller
# ------------------------------------------------------------------------------
V2RAY_N_DLL = env.str("V2RAY_N_DLL")
V2RAY_NG_DLL = env.str("V2RAY_NG_DLL")
FAIR_VPN_DLL = env.str("FAIR_VPN_DLL")
