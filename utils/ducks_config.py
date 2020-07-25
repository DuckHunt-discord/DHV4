def _(s):
    return s


DUCKS_IMAGES = {
    'emoji': "https://media.discordapp.net/attachments/734810933091762188/735596788408385750/PicsArt_07-22-03.38.37.png",
    'glare': "https://cdn.discordapp.com/emojis/436542355257163777.png",
    'eyebrows': "https://cdn.discordapp.com/emojis/436542355504627712.png",
    'wave': "https://cdn.discordapp.com/emojis/436542355345113091.png",
    'lurk': "https://cdn.discordapp.com/emojis/436542355030409219.png",
    'sip': "https://cdn.discordapp.com/emojis/436548864170786836.png",
    'ghost': "https://cdn.discordapp.com/emojis/660287926902718504.gif",
}

normal = {
    'traces': ["-,_,.-'`'°-,_,.-'`'°", "-,..,.-'`'°-,_,.-'`'°", "-._..-'`'°-,_,.-'`'°", "-,_,.-'`'°-,_,.-''`"],
    'faces': ["\\_O<", "\\_o<", "\\_Õ<", "\\_õ<", "\\_Ô<", "\\_ô<", "\\_Ö<", "\\_ö<", "\\_Ø<", "\\_ø<", "\\_Ò<", "\\_ò<", "\\_Ó<", "\\_ó<", "\\_0<", "\\_©<", "\\_@<", "\\_º<",
              "\\_°<", "\\_^<", "/_O<", "/_o<", "/_Õ<", "/_õ<", "/_Ô<", "/_ô<", "/_Ö<", "/_ö<", "/_Ø<", "/_ø<", "/_Ò<", "/_ò<", "/_Ó<", "/_ó<", "/_0<", "/_©<", "/_@<", "/_^<",
              "§_O<", "§_o<", "§_Õ<", "§_õ<", "§_Ô<", "§_ô<", "§_Ö<", "§_ö<", "§_Ø<", "§_ø<", "§_Ò<", "§_ò<", "§_Ó<", "§_ó<", "§_0<", "§_©<", "§_@<", "§_º<", "§_°<", "§_^<",
              "\\_O-", "\\_o-", "\\_Õ-", "\\_õ-", "\\_Ô-", "\\_ô-", "\\_Ö-", "\\_ö-", "\\_Ø-", "\\_ø-", "\\_Ò-", "\\_ò-", "\\_Ó-", "\\_ó-", "\\_0-", "\\_©-", "\\_@-", "\\_º-",
              "\\_°-", "\\_^-", "/_O-", "/_o-", "/_Õ-", "/_õ-", "/_Ô-", "/_ô-", "/_Ö-", "/_ö-", "/_Ø-", "/_ø-", "/_Ò-", "/_ò-", "/_Ó-", "/_ó-", "/_0-", "/_©-", "/_@-", "/_^-",
              "§_O-", "§_o-", "§_Õ-", "§_õ-", "§_Ô-", "§_ô-", "§_Ö-", "§_ö-", "§_Ø-", "§_ø-", "§_Ò-", "§_ò-", "§_Ó-", "§_ó-", "§_0-", "§_©-", "§_@-", "§_^-", "\\_O{", "\\_o{",
              "\\_Õ{", "\\_õ{", "\\_Ô{", "\\_ô{", "\\_Ö{", "\\_ö{", "\\_Ø{", "\\_ø{", "\\_Ò{", "\\_ò{", "\\_Ó{", "\\_ó{", "\\_0{", "\\_©{", "\\_@{", "\\_º{", "\\_°{", "\\_^{",
              "/_O{", "/_o{", "/_Õ{", "/_õ{", "/_Ô{", "/_ô{", "/_Ö{", "/_ö{", "/_Ø{", "/_ø{", "/_Ò{", "/_ò{", "/_Ó{", "/_ó{", "/_0{", "/_©{", "/_@{", "/_^{", "§_O{", "§_o{",
              "§_Õ{", "§_õ{", "§_Ô{", "§_ô{", "§_Ö{", "§_ö{", "§_Ø{", "§_ø{", "§_Ò{", "§_ò{", "§_Ó{", "§_ó{", "§_0{", "§_©{", "§_@{", "§_º{", "§_°{", "§_^{"],
    'emojis': ["<a:a_Duck_01:439546956986187777>", "<:official_Duck_01_reversed:439576463436546050>"],
    'shouts': ["COIN", "COIN", "COIN", "COIN", "COIN", "KWAK", "KWAK", "KWAAK", "KWAAK", "KWAAAK", "KWAAAK", "COUAK", "COUAK", "COUAAK", "COUAAK", "COUAAAK", "COUAAAK", "QUAK",
               "QUAK", "QUAAK", "QUAAK", "QUAAAK", "QUAAAK", "QUACK", "QUACK", "QUAACK", "QUAACK", "QUAAACK", "QUAAACK", "COUAC", "COUAC", "COUAAC", "COUAAC", "COUAAAC", "COUAAAC",
               "COUACK", "COUACK"],
    'usernames': [_("A duck"), _("Mr. Duck"), _("ISO Duck")],
    'avatar_urls': [DUCKS_IMAGES['emoji']],
}

ghost = {
    'traces': [],
    'faces': [],
    'emojis': [],
    'shouts': [],
    'usernames': [_('Invisible Duck'), _('Ghost Duck'), _('Boooo Duck')],
    'avatar_urls': [DUCKS_IMAGES['ghost']],
}

prof = {**normal,
        'shouts': [],
        'usernames': [_("Pr. Duck"), _("EnsDuck")],
        'avatar_urls': [DUCKS_IMAGES['glare']],
        }

baby = {**normal,
        'shouts': ["COIN", "Piou ?", "Coin ?", "Coin!", "COIIIIIINNNNNN!"],
        'usernames': [_("Smol Duck"), _("Mini Duck"), _("Ducky"), _("Duckie")],
        'avatar_urls': [DUCKS_IMAGES['lurk'], DUCKS_IMAGES['sip'], DUCKS_IMAGES['wave']],
        }

mechanical = {
    **normal,
    'faces': ['%_%', '%>%', "% _ %", '• _ %', '% _ •'],
    'emojis': ['<a:Duck_ducks:477799859894878208>'],
    'shouts': ["BZZZZZAAAAK", "BZAAAACK", "BZAACK"],
}

moad = {
    **normal,
    'shouts': [_("**I am your mother...**")],
}
