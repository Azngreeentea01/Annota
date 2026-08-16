from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
assets.mkdir(exist_ok=True)

# Render from a supersampled master so Windows and macOS icon sizes stay crisp.
BASE = 512
SCALE = 4
S = BASE * SCALE


def sc(value: int) -> int:
    return value * SCALE


master = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(master)

white = (255, 255, 255, 255)
white_soft = (255, 255, 255, 72)
white_faint = (255, 255, 255, 34)
lavender = (176, 155, 250, 255)
purple = (112, 73, 226, 255)
purple_deep = (91, 55, 199, 255)
shadow = (55, 33, 116, 54)

# Soft outer shadow and premium rounded app tile.
d.rounded_rectangle((sc(34), sc(42), sc(478), sc(486)), radius=sc(118), fill=shadow)
d.rounded_rectangle((sc(28), sc(28), sc(484), sc(484)), radius=sc(122), fill=purple)
d.rounded_rectangle((sc(40), sc(40), sc(472), sc(472)), radius=sc(110), fill=lavender)

# Subtle two-layer highlight creates depth without muddying small sizes.
d.rounded_rectangle((sc(55), sc(54), sc(457), sc(230)), radius=sc(94), fill=white_faint)
d.ellipse((sc(354), sc(68), sc(422), sc(136)), fill=white_soft)

# White annotation/chat surface with a clear tail.
d.rounded_rectangle((sc(112), sc(112), sc(392), sc(338)), radius=sc(48), fill=white)
d.polygon([(sc(182), sc(326)), (sc(154), sc(404)), (sc(246), sc(334))], fill=white)

# Selection-corner marks. Thick geometry survives 16/20/24 px rendering.
stroke = sc(18)
corner = sc(43)
for x, y, sx, sy in [
    (168, 172, 1, 1),
    (336, 172, -1, 1),
    (168, 280, 1, -1),
    (336, 280, -1, -1),
]:
    x0, y0 = sc(x), sc(y)
    d.line((x0, y0, x0 + sx * corner, y0), fill=purple_deep, width=stroke)
    d.line((x0, y0, x0, y0 + sy * corner), fill=purple_deep, width=stroke)

# Pointer cursor: white keyline plus deep-purple interior for high contrast.
outer = [
    (sc(286), sc(242)),
    (sc(344), sc(398)),
    (sc(376), sc(342)),
    (sc(438), sc(316)),
]
inner = [
    (sc(300), sc(262)),
    (sc(347), sc(374)),
    (sc(370), sc(330)),
    (sc(416), sc(313)),
]
d.polygon(outer, fill=white)
d.polygon(inner, fill=purple_deep)
d.line((sc(315), sc(286), sc(345), sc(352)), fill=(155, 126, 238, 255), width=sc(7))

# Primary PNG and Windows ICO.
png_img = master.resize((BASE, BASE), Image.Resampling.LANCZOS)
png = assets / "annota.png"
ico = assets / "annota.ico"
png_img.save(png, optimize=True)
png_img.save(
    ico,
    format="ICO",
    sizes=[
        (16, 16),
        (20, 20),
        (24, 24),
        (32, 32),
        (40, 40),
        (48, 48),
        (64, 64),
        (96, 96),
        (128, 128),
        (256, 256),
    ],
)

# macOS iconset. build_macos.sh runs iconutil on macOS to create annota.icns.
iconset = assets / "Annota.iconset"
iconset.mkdir(exist_ok=True)
mac_sizes = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}
for filename, size in mac_sizes.items():
    master.resize((size, size), Image.Resampling.LANCZOS).save(iconset / filename, optimize=True)

print(f"Created high-quality icon: {png}")
print(f"Created multi-size Windows icon: {ico}")
print(f"Created macOS iconset: {iconset}")
