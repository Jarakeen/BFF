import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.uesp.uesp_parser import (
    UespParser,
    parse_page_html,
    _HEALTH_VETERAN_MARKER,
    _extract_health,
)

html = """
<table class="infobox">
    <tr>
        <th>Health</th>
        <td>
            <a href="/wiki/File:ON-icon-Normal.png"></a>22,721,708
            <br>
            <a href="/wiki/Online:Veteran"></a>116,430,960
        </td>
    </tr>
</table>

<p>
    <a href="/wiki/Online:Veteran"></a>145,538,704 (hard mode)
</p>
"""

parsed = parse_page_html(html)

print("=" * 70)
print("DIRECT _extract_health RESULT")
print("=" * 70)

infobox_health = parsed.infobox.get("health", "")
print("infobox:", repr(infobox_health))
print("result:", _extract_health({"text": infobox_health}))

print("=" * 70)
print("BLOCK INSPECTION")
print("=" * 70)

for block in parsed.all_blocks:
    print("TYPE:", repr(block.get("type")))
    print("TEXT:", repr(block.get("text")))
    print(
        "HAS VETERAN:",
        _HEALTH_VETERAN_MARKER in block.get("text", ""),
    )

    text = block.get("text", "")

    if _HEALTH_VETERAN_MARKER in text:
        after = text.split(_HEALTH_VETERAN_MARKER, 1)[1]
        print("AFTER MARKER:", repr(after))

print("=" * 70)
print("DIRECT _health_from_page RESULT")
print("=" * 70)

health = UespParser()._health_from_page(parsed)

print("normal  :", repr(health.normal))
print("veteran :", repr(health.veteran))
print("hardmode:", repr(health.hardmode))