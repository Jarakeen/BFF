from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.uesp.uesp_parser import parse_page_html


html = """
<table class="infobox">
    <tr>
        <th>Group size</th>
        <td>4</td>
    </tr>
</table>

<h2><span id="Sets">Sets</span></h2>
<table>
    <tr>
        <th>Set Name</th>
        <th>Bonuses</th>
        <th>Armor Weight</th>
    </tr>
    <tr>
        <td>
            <a href="/wiki/Online:Cinders_of_Anthelmir">
                Cinders of Anthelmir
            </a>
        </td>
        <td>Some bonus</td>
        <td>Light Armor</td>
    </tr>
</table>

<h2><span id="Achievements">Achievements</span></h2>
<p>
    There are achievements:
    <a href="/wiki/Online:Some_Dungeon_Achievements">
        achievements
    </a>
</p>
<table>
    <tr>
        <th>Achievement</th>
        <th>Points</th>
        <th>Description</th>
        <th>Reward</th>
    </tr>
    <tr>
        <td>
            <a href="/wiki/Online:Some_Conqueror">
                Some Conqueror
            </a>
        </td>
        <td>10</td>
        <td>Defeat the bosses.</td>
        <td>Title: Conqueror</td>
    </tr>
</table>
"""


parsed = parse_page_html(html)

print("=" * 70)
print("INFOBOX")
print("=" * 70)
print(parsed.infobox)

print("=" * 70)
print("SECTION KEYS")
print("=" * 70)
print(list(parsed.sections.keys()))

print("=" * 70)
print("SETS SECTION")
print("=" * 70)
for key, blocks in parsed.sections.items():
    if "set" in key.lower():
        print("KEY:", repr(key))
        for block in blocks:
            print(block)

print("=" * 70)
print("ACHIEVEMENT SECTION")
print("=" * 70)
for key, blocks in parsed.sections.items():
    if "achievement" in key.lower():
        print("KEY:", repr(key))
        for block in blocks:
            print(block)
