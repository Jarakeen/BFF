Skill Damage
The damage formula

I'm not sure that's documented anywhere in a really accessible way, but basically it all boils down to this. The equation for skill damage numbers usually takes the form:

(k1 * max(maxStam, maxMag)) + (k2 * max(weaponDmg, spellDmg))

The k1 and k2 coefficients are different for each ability, but [k1] is almost always equal to [k2*10.5]. To put it in more practical terms, you'll get approximately the same damage increase from 100 weapon/spell damage and 1050 max stamina/magicka.

I want to highlight that it does NOT matter whether your Stamina or Magicka is higher, as in the above equation, it only ever uses the higher value. Same with Weapon Damage/Spell Damage.

UESP has the actual coefficient values for each skill, which you can see here -- try playing around with the max magicka/stamina and weapon/spell damage sliders for various skills, and you can see the calculation in action! There's also a master list of skills and their coefficients here.

Light attack and heavy attack damage is calculated with a similar formula.
Other factors

The above damage formula basically describes how the damage numbers on your skill tooltips are calculated. In practice, there are other factors that change how much damage you'll actually do. The main two factors are:

    Percent damage increases/decreases: These can come from various sources. For example, the Deadly Aim CP star permanently increases your single target damage by 6%. Or another example: in a dungeon, the team's healer will usually give you the Minor Berserk buff which increases your outgoing damage by 5%. Tbh I don't know the details of how these % modifies work (how does it interact with other % increases/decreases, what is the order of operations, etc.).

    Critical hits: crits provide an extra damage multiplier. See the Crits section below

    Your target will mitigate incoming damage with their Armor (aka Resistances). See the Armor section below

    Your character level. If you're under max level (lvl 50 cp160) then your actual damage (seen in floating damage numbers) will be higher than your damage tooltips. This is a part of the game's level scaling. I don't know the full details of this, but generally speaking, a low level character will have low damage tooltips, but they get an extra damage bonus that brings their damage output up to be in the same ballpark as a max-level character with rather unoptimized gear.

Weapon damage vs. Spell damage

As you can tell from the equation above, the Weapon Damage and Spell Damage stats are mostly redundant and interchangeable. Only the highest of the two stats is ever used for calculations.

It may seem weird, but it's because of historical reasons. A while back, the two stats were more distinct (in the old days, each ability would scale with one or the other specifically). In the past couple years however, we've gotten a series of "hybridization" updates that essentially merged the two stats together--you'll notice that the stats are almost always the same value; there are very few ways to increase one without also increasing the other.
How Character Stats are Calculated

A max-level character (Lvl 50 CP 160) has the following stats.

    Health: 16000 base + modifiers

    Magicka & Stamina: 12000 base + modifiers

    Weapon & Spell Damage: 1000 base + the Damage stat of your equipped weapon + modifiers

    Weapon & Spell Critical: 10% base + modifiers

    Penetration: 0 base + modifiers

    Physical & Spell Resistance: 0 base + the sum of the Armor stat of your equipped armor + modifiers

Obviously, the term "modifiers" is exceedingly broad, but basically it incorporates things like passive skills, gear set bonuses, gear traits, gear enchantments, mundus stone, provisioning buffs, CP stars, temporary buffs, etc. etc. etc.

Due to level scaling, characters under the max level will have higher base stats than those listed above. Their base stats will decrease a little bit each level until they reach the level cap.
Crit Chance & Crit Damage

This excellent guide covers the info really well: Skinny Cheeks Crit Guide

I want to highlight again, in your in-game character stats you'll see both "Weapon Critical" and "Spell Critical" stats: this is due to the "hybridization" history. The game only ever uses the higher of the two stats; although most of the time, your Weapon Critical and Spell Critical will be the same anyway.
Armor (aka Resistances) & Offensive Penetration

Another excellent Skinny Cheeks guide on this topic: Skinny Cheeks Armor & Penetration Guide

To add on a little to the guide:

    Before hybridization, there was both Physical & Spell Penetration. Nowadays, the game always uses the higher of the two values, but these will always be the same value anyways.

    Physical Resistance and Spell Resistance are actually different.

        Physical Resistance is used against Martial damage types: Physical, Bleed, Poison, and Disease damage

        Spell Resistance is used against Magical damage types: Magic, Fire, Frost, and Shock damage

Other References

Here are some other resources I use to collect info relating to this stuff:

    ESO Hub Sets Library: info on all gear sets in the game

    UESP list of named Buffs/Debuffs: all Major/Minor buffs/debuffs

    UESP Build Editor: Comprehensive build editor that does all the above calculations for you. It also shows you HOW it did the calculations, so it's a super valuable learning tool. It's also VERY useful for checking numbers when tweaking gear sets, race, CP passives, etc. without having to do it in-game
