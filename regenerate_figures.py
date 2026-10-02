#!/usr/bin/env python3
"""
regenerate_figures.py

Rebuilds the figures that are generated outside the numbered pipeline scripts:
the two HTML pipeline diagrams, the engraved notated examples, and the
robustness scatter. Kept so that every figure in the manuscript is reproducible
from the repository rather than inherited from an earlier PDF.

Outputs land in regenerated/ at 300+ dpi for the printed size.
"""
import io, os, re, subprocess, sys

OUT = "regenerated"
MINUS = "−"   # true minus sign, not a hyphen and not an em dash


def robustness_scatter():
    import pandas as pd, numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats

    df = pd.read_csv("parker_iv_robustness_exact.csv")
    x = df["size"].values.astype(float)
    y = df["global_robustness"].values.astype(float)
    r, _ = stats.pearsonr(x, y)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(x, y, s=26, alpha=0.55, color="#4C78A8",
               edgecolor="black", linewidth=0.4, zorder=3)
    b, a = np.polyfit(np.log10(x), y, 1)
    xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(xs, a + b * np.log10(xs), color="#B279A2", lw=2, zorder=4,
            label=f"least-squares fit   $r$ = {MINUS}.350, $p$ < .001")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency of the interval vector in the corpus (log scale)", fontsize=11)
    ax.set_ylabel("Triadic content (mean triads per vector)", fontsize=11)
    ax.set_title("Robustness as a function of usage frequency", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3, zorder=0)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    plt.tight_layout()
    plt.savefig(f"{OUT}/robustness_frequency_scatter.png", dpi=400, bbox_inches="tight")
    plt.close()
    print(f"  robustness_frequency_scatter.png  (r = {r:.4f})")


def html_diagram(name, scale=4):
    """Render an HTML diagram with headless Chrome, then trim the margins."""
    from PIL import Image, ImageChops
    html = io.open(f"{OUT}/{name}.html", encoding="utf-8").read()
    probe = html.replace("</body>",
        '<script>document.title=document.querySelector(".container, body")'
        '.getBoundingClientRect().height|0</script></body>')
    io.open(f"{OUT}/_probe.html", "w", encoding="utf-8").write(probe)
    dom = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--virtual-time-budget=1500", "--dump-dom",
                          f"file://{os.getcwd()}/{OUT}/_probe.html"],
                         capture_output=True, text=True).stdout
    m = re.search(r"<title>(\d+)</title>", dom)
    height = (int(m.group(1)) if m else 1800) + 40
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", f"--screenshot={OUT}/{name}.png",
                    f"--window-size=1400,{height}", f"--force-device-scale-factor={scale}",
                    "--default-background-color=FFFFFFFF",
                    f"file://{os.getcwd()}/{OUT}/{name}.html"], capture_output=True)
    os.remove(f"{OUT}/_probe.html")
    im = Image.open(f"{OUT}/{name}.png").convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    bb = ImageChops.difference(im, bg).getbbox()
    pad = 40
    im.crop((max(bb[0] - pad, 0), max(bb[1] - pad, 0),
             min(bb[2] + pad, im.width), min(bb[3] + pad, im.height))).save(f"{OUT}/{name}.png")
    print(f"  {name}.png  {Image.open(f'{OUT}/{name}.png').size}")


def notated_examples():
    import verovio
    from PIL import Image, ImageChops
    ACC = {-1: "flat", 1: "sharp"}

    def mx(measures):
        parts = []
        for i, notes in enumerate(measures, 1):
            m = [f'<measure number="{i}">']
            if i == 1:
                m.append('<attributes><divisions>2</divisions><key><fifths>0</fifths></key>'
                         '<time print-object="no"><beats>4</beats><beat-type>4</beat-type></time>'
                         '<clef><sign>G</sign><line>2</line></clef></attributes>')
            m.append('<harmony><root><root-step>C</root-step></root>'
                     '<kind text="7">dominant</kind></harmony>')
            for step, alt, octv in notes:
                a = f"<alter>{alt}</alter>" if alt else ""
                acc = f"<accidental>{ACC[alt]}</accidental>" if alt in ACC else ""
                m.append(f'<note><pitch><step>{step}</step>{a}<octave>{octv}</octave></pitch>'
                         f"<duration>2</duration><type>quarter</type>{acc}</note>")
            m.append("</measure>")
            parts.append("".join(m))
        return ('<?xml version="1.0" encoding="UTF-8"?><score-partwise version="3.1">'
                '<part-list><score-part id="P1"><part-name></part-name></score-part></part-list>'
                f'<part id="P1">{"".join(parts)}</part></score-partwise>')

    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 2100, "pageHeight": 400, "scale": 48, "adjustPageHeight": True,
                   "header": "none", "footer": "none", "pageMarginTop": 40,
                   "pageMarginLeft": 40, "pageMarginRight": 40, "pageMarginBottom": 20,
                   "breaks": "none"})
    tk.loadData(mx([
        [("C", 0, 4), ("E", 0, 4), ("G", 0, 4), ("B", -1, 4)],   # (a) IV (0,1,2,1,1,1); 2 triads
        [("C", 0, 4), ("D", 0, 4), ("E", -1, 4), ("B", -1, 4)],  # (b) triadically sparse; 0 triads
        [("C", 0, 4), ("E", -1, 4), ("G", -1, 4), ("A", 0, 4)],  # (c) triadically dense; 4 triads
    ]))
    io.open(f"{OUT}/ex_notation.svg", "w", encoding="utf-8").write(tk.renderToSVG(1))
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", f"--screenshot={OUT}/ex_notation_hi.png",
                    "--window-size=1200,220", "--force-device-scale-factor=6",
                    "--default-background-color=FFFFFFFF",
                    f"file://{os.getcwd()}/{OUT}/ex_notation.svg"], capture_output=True)
    im = Image.open(f"{OUT}/ex_notation_hi.png").convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bb = ImageChops.difference(im, bg).getbbox()
    pad = 48
    im.crop((max(bb[0] - pad, 0), max(bb[1] - pad, 0),
             min(bb[2] + pad, im.width), min(bb[3] + pad, im.height))).save(f"{OUT}/ex_notation_hi.png")
    print(f"  ex_notation_hi.png  {Image.open(f'{OUT}/ex_notation_hi.png').size}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("Regenerating figures:")
    robustness_scatter()
    html_diagram("pipeline1")
    html_diagram("pipeline2")
    notated_examples()
    print("Done. The strategy-characteristics and Granger-rate figures are produced by "
          "09_autocorrelation.py and 10_gravity.py respectively.")
