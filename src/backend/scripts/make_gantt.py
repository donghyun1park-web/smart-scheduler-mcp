import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from datetime import date
from tools.boq_sequencer import build_earthwork_network, run_cpm, add_calendar

fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font = fm.FontProperties(fname=fp)
matplotlib.rcParams["axes.unicode_minus"] = False

tasks = run_cpm(build_earthwork_network(rock_days=242))
cal = add_calendar(tasks, date(2026, 5, 1))
core_end_id = max((t for t in tasks if t.phase == "토공사"), key=lambda t: t.ef).id
core_end_date = cal[core_end_id][1]

fig, ax = plt.subplots(figsize=(13, 6.5))
ax.set_facecolor("#fbfbfa")
tasks_rev = list(reversed(tasks))
for i, t in enumerate(tasks_rev):
    s, e = cal[t.id]
    dur = (e - s).days
    if t.phase == "구조물의존":
        color, hatch = "#b0a89c", "//"
    elif t.critical:
        color, hatch = "#c0392b", None
    else:
        color, hatch = "#5b7ba5", None
    ax.barh(i, dur, left=s, height=0.55, color=color, edgecolor="white",
            linewidth=0.8, hatch=hatch, zorder=3)
    ax.text(s, i, f" {t.id} {t.name}", va="center", ha="left",
            fontproperties=font, fontsize=9, color="#222", zorder=4)
    if t.tf > 0:
        ax.text(e, i, f"  TF{t.tf}", va="center", ha="left",
                fontproperties=font, fontsize=7.5, color="#888", zorder=4)

# 본공정 완료 기준선
ax.axvline(core_end_date, color="#1a8a4a", linewidth=1.4, linestyle="--", zorder=2)
ax.text(core_end_date, len(tasks_rev) - 0.3, " 토공사 본공정 완료\n (공정표 일치)", fontproperties=font,
        fontsize=8.5, color="#1a8a4a", va="top", ha="left", zorder=5)

ax.set_yticks(range(len(tasks_rev)))
ax.set_yticklabels([])
ax.set_ylim(-0.6, len(tasks_rev) - 0.4)
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
plt.setp(ax.get_xticklabels(), fontsize=8)
ax.grid(axis="x", color="#e3e3e0", linewidth=0.7, zorder=0)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)

core_wd = max(t.ef for t in tasks if t.phase == "토공사")
ax.set_title(f"홍은동 토공사 CPM 초안 Gantt  (BOQ→CPM 자동생성 · 본공정 {core_wd}WD≈16.3개월)",
             fontproperties=font, fontsize=12, color="#1a1a1a", pad=12, loc="left")
ax.legend(handles=[Patch(color="#c0392b", label="Critical Path"),
                   Patch(color="#5b7ba5", label="여유공정"),
                   Patch(facecolor="#b0a89c", hatch="//", label="구조물 의존(별도)")],
          loc="lower right", prop=font, frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig("samples/홍은동_CPM_gantt.png", dpi=150, bbox_inches="tight")
plt.savefig("/mnt/user-data/outputs/홍은동_CPM_gantt.png", dpi=150, bbox_inches="tight")
print("Gantt 저장 완료")
