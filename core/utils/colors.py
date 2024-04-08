def to_rgba(color, opacity=1.0):
    rgb = [int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "rgba({},{},{},{})".format(rgb[0], rgb[1], rgb[2], opacity)