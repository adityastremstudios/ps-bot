TICK = "<:check:807913701151342592>"
CROSS = "<:xmark:807913737805234176>"

DIAMOND = "<a:diamond:899295009289949235>"  # Quotient Premium

INFO = "<:info2:899020593188462693>"  # blue round i symbol

TEXT_CHANNEL = "<:text:815827264679706624>"  # text channel symbol

EXIT = "<:exit:926048897548300339>"  # back , exit symbol

PLANT = "<:plant:1253293916724264981>"

PLUS_SIGN = "<:add:844825523003850772>"  # green plus symbol

LOADING = "<a:loading:815826684262744124>"

CREDIT_CARD = "<:card:1254124258750365918>"

F_WORD = "<:f_word:1254123534729351178>"

IMAGE_SYMBOL = "<:image:1254123107694936156>"

BELL = "<a:ringing_bell:1256877114125189153>"

YOUTUBE = "<:yt:1264245964315689041>"

# Paginator:

PREVIOUS_PAGE = "<:left:878668491660623872>"
NEXT_PAGE = "<:right:878668370331983913>"

FIRST_PAGE = "<:double_left:878668594530099220>"
LAST_PAGE = "<:double_right:878668437193359392>"


def regional_indicator(c: str) -> str:
    """Returns a regional indicator emoji given a character."""
    return chr(0x1F1E6 - ord("A") + ord(c.upper()))


def keycap_digit(c: int | str) -> str:
    """Returns a keycap digit emoji given a character."""
    c = int(c)
    if 0 < c < 10:
        return str(c) + "\U0000FE0F\U000020E3"
    if c == 10:
        return "\U000FE83B"

    raise ValueError("Invalid keycap digit")
