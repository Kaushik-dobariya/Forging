import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = BASE_DIR / "app" / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def create_gradient_asset(
    filename: str,
    width: int,
    height: int,
    top_color: tuple,
    bot_color: tuple,
    accent_color: tuple,
    title: str,
    badge: str = "FORGE INDUSTRIAL",
    overlay_lines: bool = True,
):
    out_path = IMAGES_DIR / filename
    img = Image.new("RGB", (width, height), top_color)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(height):
        factor = y / height
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * factor)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * factor)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Technical grid lines
    if overlay_lines:
        grid_step = 60
        for x in range(0, width, grid_step):
            draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 12), width=1)
        for y in range(0, height, grid_step):
            draw.line([(0, y), (width, y)], fill=(255, 255, 255, 12), width=1)

    # Radial metallic / furnace glow in lower right
    center_x = int(width * 0.75)
    center_y = int(height * 0.65)
    for radius in range(int(height * 0.6), 0, -10):
        alpha = int((1.0 - (radius / (height * 0.6))) * 60)
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=(accent_color[0], accent_color[1], accent_color[2]),
            width=2,
        )

    # Technical border accents (hairline frame)
    margin = 24
    draw.rectangle(
        [margin, margin, width - margin, height - margin],
        outline=(accent_color[0], accent_color[1], accent_color[2]),
        width=1,
    )
    # Corner markers
    corner_len = 20
    draw.line([(margin, margin), (margin + corner_len, margin)], fill=accent_color, width=3)
    draw.line([(margin, margin), (margin, margin + corner_len)], fill=accent_color, width=3)
    draw.line([(width - margin, margin), (width - margin - corner_len, margin)], fill=accent_color, width=3)
    draw.line([(width - margin, margin), (width - margin, margin + corner_len)], fill=accent_color, width=3)
    draw.line([(margin, height - margin), (margin + corner_len, height - margin)], fill=accent_color, width=3)
    draw.line([(margin, height - margin), (margin, height - margin - corner_len)], fill=accent_color, width=3)
    draw.line([(width - margin, height - margin), (width - margin - corner_len, height - margin)], fill=accent_color, width=3)
    draw.line([(width - margin, height - margin), (width - margin, height - margin - corner_len)], fill=accent_color, width=3)

    # Text overlays
    draw.text((margin + 30, margin + 30), badge, fill=accent_color)
    draw.text((margin + 30, margin + 60), title, fill=(245, 244, 240))
    draw.text((margin + 30, height - margin - 40), f"SPEC: ISO 9001 / IATF 16949 • RES: {width}x{height}", fill=(142, 155, 168))

    img.save(str(out_path), quality=90)
    print(f"Generated asset: {out_path}")


def generate_all():
    primary = (23, 33, 43)        # #17212B
    graphite = (40, 50, 60)       # #28323C
    dark_slate = (15, 22, 29)     # #0F161D
    copper = (183, 121, 63)       # #B7793F
    warm_ember = (207, 142, 82)   # #CF8E52
    steel_blue = (45, 70, 95)

    # 1. Hero Slides
    create_gradient_asset(
        "hero_slide_1.webp", 1920, 1080, dark_slate, graphite, copper,
        "PRECISION FORGED FOR PERFORMANCE // 6,300T PRESS DIVISION",
        "FORGE PRECISION ENGINEERING • HEAVY DIE FORGING",
    )
    create_gradient_asset(
        "hero_slide_2.webp", 1920, 1080, graphite, steel_blue, warm_ember,
        "BUILT AROUND YOUR ENGINEERING REQUIREMENTS // 5-AXIS CNC MACHINING",
        "AUTOMOTIVE & AEROSPACE COMPONENT CATALOG",
    )
    create_gradient_asset(
        "hero_slide_3.webp", 1920, 1080, dark_slate, primary, copper,
        "QUALITY AT EVERY STAGE // NABL SPECTROMETRY & 100% ULTRASONIC NDT",
        "METALLURGY & COMPLIANCE LABORATORY",
    )

    # 2. Key Capabilities & Technical Features
    create_gradient_asset("hero_furnace.webp", 1200, 800, dark_slate, (70, 35, 15), warm_ember, "SCADA THERMAL NORMALIZING FURNACE")
    create_gradient_asset("open_die_forging.webp", 1200, 800, dark_slate, graphite, copper, "HEAVY OPEN DIE FORGING UP TO 15 MT")
    create_gradient_asset("closed_die_forging.webp", 1200, 800, graphite, dark_slate, copper, "CLOSED-DIE PRECISION DROP HAMMER LINE")
    create_gradient_asset("ring_rolling.webp", 1200, 800, dark_slate, steel_blue, copper, "CNC SEAMLESS ROLLED RINGS (DIA UP TO 3,000mm)")
    create_gradient_asset("cnc_machining.webp", 1200, 800, steel_blue, dark_slate, warm_ember, "PRECISION 5-AXIS CNC MACHINING CENTERS")
    create_gradient_asset("heat_treatment.webp", 1200, 800, (60, 25, 10), dark_slate, warm_ember, "POLYMER & WATER QUENCH HEAT TREATMENT")
    create_gradient_asset("testing_lab.webp", 1200, 800, dark_slate, steel_blue, copper, "NABL CERTIFIED METALLURGY & NDT LAB")

    # 3. Facilities
    create_gradient_asset("plant_exterior.webp", 1200, 800, dark_slate, graphite, copper, "120,000 SQ FT ADVANCED MANUFACTURING PLANT")
    create_gradient_asset("press_shop.webp", 1200, 800, graphite, steel_blue, warm_ember, "HEAVY HYDRAULIC FORGING PRESS SHOP BAY")
    create_gradient_asset("die_shop.webp", 1200, 800, steel_blue, dark_slate, copper, "CAD/CAM TOOL & DIE DESIGN CENTER")

    # 4. Brand Logo
    logo = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    # Badge
    d.rectangle([10, 15, 110, 65], fill=(23, 33, 43, 255), outline=(183, 121, 63, 255), width=2)
    d.text((28, 30), "FORGE", fill=(183, 121, 63, 255))
    # Brand Name
    d.text((125, 24), "PRECISION FORGING", fill=(23, 33, 43, 255))
    d.text((125, 44), "METALLURGY & ENGINEERING", fill=(91, 100, 112, 255))
    logo.save(str(IMAGES_DIR / "logo.png"))
    print("Generated logo.png")

    # 5. Favicon
    fav = Image.new("RGBA", (64, 64), (23, 33, 43, 255))
    fav_d = ImageDraw.Draw(fav)
    fav_d.rectangle([4, 4, 60, 60], outline=(183, 121, 63, 255), width=3)
    fav_d.text((16, 20), "F", fill=(183, 121, 63, 255))
    fav.save(str(BASE_DIR / "app" / "static" / "favicon.ico"))
    print("Generated favicon.ico")


if __name__ == "__main__":
    generate_all()
