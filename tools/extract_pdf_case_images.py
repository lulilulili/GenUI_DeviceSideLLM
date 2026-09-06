"""Extract row-major PDF card examples from the four black-background evidence images."""
from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    1: {"count": 14, "top": 190, "ratio": 2.0, "pad": 8},
    2: {"count": 28, "top": 320, "ratio": 1.0, "pad": 8},
    3: {"count": 15, "top": 380, "ratio": 2.0, "pad": 10},
    4: {"count": 11, "top": 480, "ratio": 1.0, "pad": 10},
}


def components(image, top):
    gray = image.convert("L").crop((0, top, image.width, image.height))
    mask = gray.point(lambda value: 255 if value > 16 else 0).filter(ImageFilter.MaxFilter(21))
    scale = 4
    mask = mask.resize((max(1, mask.width // scale), max(1, mask.height // scale)), Image.Resampling.NEAREST)
    pix, width, height = mask.load(), mask.width, mask.height
    seen, boxes = set(), []
    for y in range(height):
        for x in range(width):
            if pix[x, y] == 0 or (x, y) in seen:
                continue
            queue, seen_now = deque([(x, y)]), []
            seen.add((x, y))
            while queue:
                cx, cy = queue.popleft(); seen_now.append((cx, cy))
                for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                    if 0 <= nx < width and 0 <= ny < height and pix[nx, ny] and (nx, ny) not in seen:
                        seen.add((nx, ny)); queue.append((nx, ny))
            xs, ys = zip(*seen_now)
            box = (min(xs)*scale, min(ys)*scale+top, (max(xs)+1)*scale, (max(ys)+1)*scale+top)
            if (box[2]-box[0]) * (box[3]-box[1]) > 1400 and box[3]-box[1] > 40:
                boxes.append(box)
    return boxes


def row_major(boxes):
    remaining, rows = sorted(boxes, key=lambda b: (b[1], b[0])), []
    while remaining:
        anchor = remaining[0]
        threshold = max(24, (anchor[3]-anchor[1]) * .45)
        row = [box for box in remaining if abs(box[1]-anchor[1]) < threshold]
        rows.append(sorted(row, key=lambda b: b[0]))
        remaining = [box for box in remaining if box not in row]
    return [box for row in rows for box in row]


def ratio_box(box, ratio, pad, width, height):
    x1,y1,x2,y2=box; x1-=pad; y1-=pad; x2+=pad; y2+=pad
    current_w,current_h=x2-x1,y2-y1
    if current_w/current_h < ratio:
        extra=(current_h*ratio-current_w)/2; x1-=extra; x2+=extra
    else:
        extra=(current_w/ratio-current_h)/2; y1-=extra; y2+=extra
    return tuple(map(round,(max(0,x1),max(0,y1),min(width,x2),min(height,y2))))


def main():
    output = ROOT / "web" / "assets" / "pdf-cases"
    output.mkdir(parents=True, exist_ok=True)
    for page, config in CONFIG.items():
        source = ROOT / "web" / "assets" / f"pdf-{['','2x1','2x2','3x2','3x3'][page]}.jpg"
        image = Image.open(source).convert("RGB")
        boxes = row_major(components(image, config["top"]))
        if len(boxes) != config["count"]:
            raise RuntimeError(f"page {page}: expected {config['count']} cards, detected {len(boxes)}: {boxes}")
        for index, box in enumerate(boxes, 1):
            crop = image.crop(ratio_box(box, config["ratio"], config["pad"], image.width, image.height))
            crop.save(output / f"P{page}-{index:02}.jpg", quality=92)
        print(f"page {page}: {len(boxes)} cards")


if __name__ == "__main__":
    main()
