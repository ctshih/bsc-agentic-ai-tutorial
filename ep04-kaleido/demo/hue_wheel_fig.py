"""
hue_wheel_fig.py — 產生「HSV 色相環」教學圖
=============================================
教材與影片都會講「色相差幾度」，但讀者不一定知道顏色為什麼可以用角度表示。
這支程式畫一張圖說明三件事：

  1. 色相（hue）是色環上的一個角度：0° 紅、120° 綠、240° 藍，繞一圈回到原點。
  2. 因為是「環」，兩個顏色的差距最多只有 180° —— 這就是能量函數裡
     min(Δ, 360−Δ) 那一項在做的事（繞另一邊比較近就走另一邊）。
  3. Kaleido 只動色相：飽和度固定為 1、明度交給訊號強度。

右半邊用真實資料舉例：同一對神經元在隨機配色與 Kaleido 配色下的色相角。
數值從 data/neurons.json 與 data/render.json 讀出來，不是手寫的。

輸出：images/hue-wheel.png（經 shot.py 由 hue_wheel.html 截圖）
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

R_OUT, R_IN = 86, 56          # 色環外半徑、內半徑
SEG = 360                     # 色環切成幾段（每段 1 度）


def ring(cx, cy, r_out=R_OUT, r_in=R_IN):
    """用 SEG 個扇形拼出一個色相環。每段填 hsl(角度)。"""
    out = []
    for k in range(SEG):
        a0 = k * 360.0 / SEG
        a1 = (k + 1) * 360.0 / SEG
        # SVG 的 y 軸向下，所以用 -sin 讓角度逆時針增加（0° 在右邊）
        p = []
        for r, (aa, bb) in ((r_out, (a0, a1)), (r_in, (a1, a0))):
            for a in (aa, bb):
                p.append((cx + r * math.cos(math.radians(a)),
                          cy - r * math.sin(math.radians(a))))
        d = (f"M{p[0][0]:.2f},{p[0][1]:.2f} A{r_out},{r_out} 0 0 0 {p[1][0]:.2f},{p[1][1]:.2f} "
             f"L{p[2][0]:.2f},{p[2][1]:.2f} A{r_in},{r_in} 0 0 1 {p[3][0]:.2f},{p[3][1]:.2f} Z")
        out.append(f'<path d="{d}" fill="hsl({a0:.1f} 100% 50%)"/>')
    return "".join(out)


def marker(cx, cy, angle, label, side=1):
    """在色環上標一個角度：一條指針 + 一個色點 + 文字。"""
    a = math.radians(angle)
    x1, y1 = cx + (R_IN - 4) * math.cos(a), cy - (R_IN - 4) * math.sin(a)
    x2, y2 = cx + (R_OUT + 16) * math.cos(a), cy - (R_OUT + 16) * math.sin(a)
    tx, ty = cx + (R_OUT + 30) * math.cos(a), cy - (R_OUT + 30) * math.sin(a)
    anchor = "start" if math.cos(a) > 0.15 else ("end" if math.cos(a) < -0.15 else "middle")
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#1b2733" stroke-width="2.5"/>'
            f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="7" fill="hsl({angle} 100% 50%)" '
            f'stroke="#1b2733" stroke-width="2"/>'
            f'<text x="{tx:.1f}" y="{ty + 5:.1f}" text-anchor="{anchor}" '
            f'class="mk">{label}</text>')


def tick(cx, cy, angle, text):
    a = math.radians(angle)
    tx, ty = cx + (R_OUT + 22) * math.cos(a), cy - (R_OUT + 22) * math.sin(a)
    anchor = "start" if math.cos(a) > 0.15 else ("end" if math.cos(a) < -0.15 else "middle")
    return (f'<text x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="{anchor}" '
            f'class="tick">{text}</text>')


def chip(h):
    return f'<span class="chip" style="background:hsl({h} 100% 50%)"></span>'


def main():
    meta = json.loads((DATA / "neurons.json").read_text(encoding="utf-8"))
    rend = json.loads((DATA / "render.json").read_text(encoding="utf-8"))
    by = {r["id"]: r for r in meta["neurons"]}

    # 挑「隨機配色下色相差最小」的那一對當例子：對比最戲劇化
    c = min(rend["clashes"], key=lambda x: x["hue_gap_random"])
    a_id, b_id = c["pair"]
    ra, rb = by[a_id]["hue_random"], by[b_id]["hue_random"]
    ka, kb = by[a_id]["hue_kaleido"], by[b_id]["hue_kaleido"]

    # --- 左：色相環的說明
    cx1, cy1 = 146, 176
    left = ring(cx1, cy1)
    for ang, name in ((0, "0° 紅"), (60, "60° 黃"), (120, "120° 綠"),
                      (180, "180° 青"), (240, "240° 藍"), (300, "300° 洋紅")):
        left += tick(cx1, cy1, ang, name)
    left += (f'<text x="{cx1}" y="{cy1 - 6}" text-anchor="middle" class="ctr">色相</text>'
             f'<text x="{cx1}" y="{cy1 + 14}" text-anchor="middle" class="ctr2">hue</text>')

    # --- 中：隨機配色的那一對
    cx2, cy2 = 146, 176
    mid = ring(cx2, cy2)
    mid += marker(cx2, cy2, ra, f"{ra:.1f}°")
    mid += marker(cx2, cy2, rb, f"{rb:.1f}°")

    # --- 右：Kaleido 配色的同一對
    cx3, cy3 = 146, 176
    right = ring(cx3, cy3)
    right += marker(cx3, cy3, ka, f"{ka:.1f}°")
    right += marker(cx3, cy3, kb, f"{kb:.1f}°")

    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<style>
  :root{{--ink:#1b2733;--soft:#5a6b7b;--line:#e4e8ee;--red:#dc2626;--green:#16a34a}}
  *{{box-sizing:border-box}}
  body{{margin:0;padding:26px 30px;background:#fff;color:var(--ink);
       font-family:"Noto Sans TC","Microsoft JhengHei","PingFang TC",system-ui,sans-serif}}
  .row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}}
  .card{{border:2px solid var(--line);border-radius:14px;padding:16px 18px 12px}}
  .card.bad{{border-color:#fecaca;background:#fef2f2}}
  .card.ok{{border-color:#bbf7d0;background:#f0fdf4}}
  h3{{margin:0 0 2px;font-size:16.5px}}
  .card.bad h3{{color:var(--red)}} .card.ok h3{{color:var(--green)}}
  .sub{{margin:0 0 6px;font-size:12.5px;color:var(--soft);min-height:32px}}
  svg{{display:block;margin:0 auto}}
  .tick{{font-size:11.5px;fill:#5a6b7b;font-family:inherit}}
  .mk{{font-size:12.5px;fill:#1b2733;font-weight:700;font-family:inherit}}
  .ctr{{font-size:15px;fill:#1b2733;font-weight:700;font-family:inherit}}
  .ctr2{{font-size:11px;fill:#8b98a5;font-family:inherit}}
  .gap{{text-align:center;font-size:15px;margin:2px 0 0;font-weight:700}}
  .card.bad .gap{{color:var(--red)}} .card.ok .gap{{color:var(--green)}}
  .chips{{display:flex;gap:6px;justify-content:center;margin:8px 0 0}}
  .chip{{width:52px;height:26px;border-radius:6px;border:1.5px solid #1b2733}}
  .note{{margin:16px 0 0;padding:12px 16px;border-left:4px solid #2563eb;
        background:#eff4ff;border-radius:0 8px 8px 0;font-size:14px;line-height:1.65}}
  .note b{{color:#2563eb}}
  code{{background:#fff;border:1px solid var(--line);border-radius:4px;padding:1px 5px;
       font-family:Consolas,monospace;font-size:.92em}}
</style></head><body>
<div class="row">

  <div class="card">
    <h3>顏色 = 色環上的一個角度</h3>
    <p class="sub">HSV 色彩模型的「色相」。繞一圈 360° 回到原點。</p>
    <svg width="320" height="352" viewBox="0 0 320 352">{left}</svg>
    <div class="chips">{chip(0)}{chip(120)}{chip(240)}</div>
    <p class="gap" style="color:#5a6b7b">紅、綠、藍相隔 120°</p>
  </div>

  <div class="card bad">
    <h3>隨機配色：差 {c['hue_gap_random']}°</h3>
    <p class="sub">{a_id}<br>{b_id}</p>
    <svg width="320" height="352" viewBox="0 0 320 352">{mid}</svg>
    <div class="chips">{chip(ra)}{chip(rb)}</div>
    <p class="gap">兩顆幾乎同色，分不出來</p>
  </div>

  <div class="card ok">
    <h3>Kaleido：差 {c['hue_gap_kaleido']}°</h3>
    <p class="sub">同樣這兩條神經元<br>被重新指派了色相角</p>
    <svg width="320" height="352" viewBox="0 0 320 352">{right}</svg>
    <div class="chips">{chip(ka)}{chip(kb)}</div>
    <p class="gap">一眼就能分開</p>
  </div>

</div>

<p class="note"><b>為什麼公式裡要寫 min(Δ, 360−Δ)？</b>
因為色相是一個<b>環</b>：10° 和 350° 看起來只差 20°，不是 340°。
繞哪一邊近就算哪一邊，所以兩個顏色的差距<b>最多只有 180°</b>——那就是對比色，也是最好分辨的狀態。
<br><b>Kaleido 只動色相這一個維度</b>：飽和度固定為 1，明度交給每個體素的訊號強度。
所以「配色」這件事，就是把色環上 N 個等距的角度，重新分配給 N 條神經元。</p>
</body></html>
"""
    out = ROOT / "hue_wheel.html"
    out.write_text(html, encoding="utf-8")
    print(f"完成 -> {out}")
    print(f"  例子：{a_id} / {b_id}")
    print(f"  隨機 {ra}° 與 {rb}°（差 {c['hue_gap_random']}°）")
    print(f"  Kaleido {ka}° 與 {kb}°（差 {c['hue_gap_kaleido']}°）")


if __name__ == "__main__":
    main()
