# --- 切り抜き関数（高精度） ---
def high_crop_mainstat(image):
    width, height = image.size
    # 元の高さ: 0.220 - 0.120 = 0.100 -> 3/4移動 (+0.075)
    return image.crop((
        int(width * 0.548),
        int(height * 0.195),
        int(width * 0.890),
        int(height * 0.295),
    ))


def high_crop_substats(image):
    width, height = image.size
    # 元の高さ: 0.500 - 0.200 = 0.300 -> 3/4移動 (+0.225)
    return image.crop((
        int(width * 0.500),
        int(height * 0.425),
        int(width * 0.950),
        int(height * 0.725),
    ))


# --- 切り抜き関数（通常） ---
def normal_crop_type(image):
    width, height = image.size
    # 元の高さ: 236 - 184 = 52px -> 3/4移動 (+39px)
    return image.crop((
        int(width * (1260 / 1920)),
        int(height * (223 / 1080)),
        int(width * (1578 / 1920)),
        int(height * (275 / 1080)),
    ))


def normal_crop_mainstat(image):
    width, height = image.size
    # 元の高さ: 364 - 232 = 132px -> 3/4移動 (+99px)
    return image.crop((
        int(width * (1256 / 1920)),
        int(height * (331 / 1080)),
        int(width * (1530 / 1920)),
        int(height * (463 / 1080)),
    ))


def normal_crop_substats(image):
    width, height = image.size
    # 元の高さ: 634 - 474 = 160px -> 3/4移動 (+120px)
    return image.crop((
        int(width * (1286 / 1920)),
        int(height * (594 / 1080)),
        int(width * (1510 / 1920)),
        int(height * (754 / 1080)),
    ))