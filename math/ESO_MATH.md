

Class Representative
Hello and welcome to my guide on damage dealing in ESO!

First of all, this is not meant to tell you what set is BiS or what is not. There is no universal BiS in a game as complex as ESO. Sets are situational, buffs are situational, so always be critical of what others tell you, test it yourself, reflect on what you're told. This guide is meant to get players to understand how the game functions at its core, with all the math and statistics behind it. So ideally, after you read this guide, you should be able to determine yourself which set or skill setup suits your build perfectly and why.

As for the general source of these formulae: they are taken from uesp.net. These guys developed an addon that collects actual ingame damage values and performs regressions with these in order to obtain the true damage coefficients behind the skills. If you question the site and the reliability of the information presented here, i suggest you learn a bit about panel data analysis through multivariate regressions. On the skill coefficient webiste, the R² (indicating the explanatory power of the model used or in this case, how accurate the calculation is) is 99.99% in all cases, with 100% being the most accurate it can be.

We're gonna go through the whole damage calculation formula and determine how different amplifiers affect your base stats, what diminishing returns are in the context of additive calculations, and then do a skill example along the way.

Part One: Calculating Damage

Let's start with the whole damage formula for a magicka skill and then break it down into pieces:

Average Damage done = (Skill Coefficient for Maximum Magicka*Maximum Magicka + Skill Coefficient for Spell Damage*SpellDamage+Flat Damage Amps)*(1 + Spell Critical Chance * Spell Critical Damage)*(1 + Damage Done )* (Spell Armor Mitigation)*(1 + Damage Taken)*(1+Execute Bonus)*(1+Bloodthirsty Bonus)



This looks fairly complex, but it is easier than you think if we break it down into pieces. This formula determines the average damage you will do with your skills, light attacks and heavy attacks in general. Mathematically, we want to maximise the value of this formula, because then we achieve the highest average damage. This is showing the term for magicka toons, but the stamina version looks exactly like that as well.
Please note that all damage and healing you do in cyrodiil and battlegrounds is halved. So for PvP, simply divide the whole formula by 2.
1. Base Damage, Scaling and Skill Coefficients

The first part of the formula is responsible for the base damage you get from your main stats. Every skill in the game has one of the two resource types to scale with, either stamina or magicka. In most cases, it depends on the resource the skill uses, so if a skill costs magicka, it will use your maximum magicka and spell damage. If it costs stamina, it will use your maximum stamina and weapon damage to determine the damage it causes. There are exceptions to this though: Ultimates and certain skills scale with your highest resource, so if your maximum magicka and spell damage is higher than your maximum stamina and weapon damage, the will use magicka and spell damage and vice-versa. The non-ultimates that follow this pattern usually indicate that they use the highest resource in their tooltip.

Some skills, notably sorcerer pets, shields, some healing skills and the final hit of the templar skill backlash and its morphs only use your maximum resource (in some cases your maximum health). Increasing your weapon or spell damage will not have any effect on the strength of these skills.


1. 1. Diminishing Returns in Base Stats

Knowing this, we can already say that maximising your base stats is important to increase your damage. However, you need to take into account that the returns you get from either of those stats are diminishing with increased size prior to the additions you make. Your damage increase in % from going from 2000 spell damage to 2500 is bigger than your damage increase from 2500 to 3000:

40000*0.05+2000*0.5=3000 <=> 0%
40000*0.05+2500*0.5=3250 <=> + ~8.33%
40000*0.05+3000*0.5=3500 <=> + ~7.70%

So the more you already have from one of these, the less benefit you will have, relative to the damage you had before. This is why stacking too much into one resource and neglecting most of the others is often detrimental and not ideal to achieve the highest possible damage.

NOTE: Do not forget that maximum magicka/maximum health also increases your shield strength and therefore has a bit more utility than spell damage/weapon damage. So consider this when you have to decide between maximum resource and other stat choices.

1.2. What are skill coefficients and what is the scaling ratio?

Skill coefficients determine the damage a skill does and are responsible for the difference in damage between skills. Every skill has its own coefficients, one for the maximum resource and one for the weapon stat.
Let's do an example:

Funnel Health from the Nightblade has a 0.0961044 for the maximum resource and 1.00801 for spell damage. This means that the base damage of the ability, without any amplifiers, is equal to roughly 10% of your maximum magicka, plus the value of your spell damage. When you look at the two coefficients, we can see that one is about 10 times bigger than the other. This is not random, it is the same for all skills that scale with your maximum resource and weapon stat. The scaling ratio, calculated by dividing the coefficient for the weapon stat by the coefficient fro maximum resource is always equal to 10.5:

Scaling ratio=Skill Coefficient for Spell Damage/Skill Coefficient for Maximum Magicka=10.5

What does this mean? It shows that spell damage affects your damage done by skills 10.5 times more than your maximum resource. However, the game is balanced around this ratio. Your spell damage will often be around 10 times smaller than your maximum magicka, and the sets and buffs in the game only allow a cetain level of spell damage that you can achieve, and maximum magicka bonuses are in general also around 10.5 times higher than spell damage bonuses.

You can find the respective skill coefficients here:

https://esoitem.uesp.net/viewSkillCoef.php
1.2.1. Maximum resources

Maximum resources are one of the two core determinants of base damage. You get it through enchantments, set bonuses, passives, food and drinks and attribute points. As I stated above, maximising (or rather idealising) the amount you have is crucial to doing damage. Here's the formula in general:

Maximum Magicka =((142 * Level + 858 + 111 * Attribute Flat Magicka + Item Flat Magicka + Set Flat Magicka)*(1 + 0.004 * min(CP.Magicka, 100) - 0.00002 * pow(min(CP.Magicka, 100), 2)) + Food Flat Magicka + Mundus Flat Magicka + Skill2 Flat Magicka)*(1 + Skill % Magicka + Buff % Magicka)

This again looks complicated, but it is easier if we break it down into pieces. The first term (142 * Level + 858) is simply the base magicka that every maximum level character has, and is equal to 10230. On top of that, we add the attributes we invested, which are 64 at maximum: 111*64=7104. Afterwards we have most of the flat magicka bonuses you can get, such as regular set bonuses.

Here's the tricky part: These base values get amplified by 20%, which is the result of this part of the formula: (1 + 0.004 * min(CP.Magicka, 100) - 0.00002 * pow(min(CP.Magicka, 100), 2))=0.2. This is the reward that all players that invest at least 100 cps into the respective cp tree get. So if you wonder why max magicka bonuses are lower than spell damage flat bonuses with regard to the scaling ratio, then this is the reason why. Most flat bonuses to maximum resources are amplified strongly by your cp level, which is also why investing too much into maximum resources is very detrimental in no-cp content (e.g. battlegrounds).

The last amplifier includes things like warhorn, inner light, bound aegis/armaments and passives (nightblades' magicka flood), racial passives et cetera. This affects all bonuses you can get, and is multiplicative with the cp buff.
1.2.2. Weapon stats

Weapon stats are the second determinant of base damage, and they are calculated almost equally to the maximum resource equivalent, but a little easier:

Spell Damage = (Item Flat Spell Damage + Set Flat Spell Damage + Mundus Flat Spell Damage)*(1 + Skill % Spell Damage + Buff % Spell Damage)

Here, we don't have to consider special scaling from cps, it is simply adding up all flat buffs, then adding up all % buffs you have and then multiplying the two. Spell damage amps can come from set bonuses, your weapon itself (with different values for different weapons) and mundus stones (warrior, apprentice).

Here's the stats from weapons on cp 160 level:

Staves, Bows, Restoration Staffs: 1335
Dual Wield: 1335 + 26% from offhand = 1335+0.26*1335=1682 (includes the 6% from offhand passive, as you will most likely have it)
Two-handed: 1571
One hand and shield: 1335

So you see that twohanders and dual wield have the highest base damage, while the others are equal at 1335. Dual wield always has 20% from the offhand added to the main hand weapon, which is also the proc chance for enchantments on the offhand, but we will get to enchantments and status effects later.
2. Critical Chance, Critical Resistance and Critical Hit Damage

This is an interesting part, because it is a bit more abstract to measure and at the same time easier to calculate. Critical chance is, simply put, the chance you have to deal more damage to the enemy because you hit them in a critical position or spot. This mechanic is part of many MMOs out there, and it is often based on pure luck. Criticial damage then determines the additional damage you do when you critically strike the enemy. So if you want to calculate the average damage you get from critical chance and critical damage, you have to use the following formula:

Average Critical Damage = (1 + Spell Critical Chance * (Spell Critical Damage-Critical Resitance)

So we multiply the critical chance with the critical damage, because the return you get from either of these depends on the other one. If you have a low critical chance, additional critical damage will obviously not be that beneficial to you and vice-versa.
2.1. Critical chance

Critical chance is subject to a bit of inconsistency in the game. Some set bonuses tell you that they increase the crictical rating by 10%, while others say they increase it by 1943 (not in %). Converting absolutes in % is fairly easy: simply divide the number by 219. So for the 1943, we have a % value of 8.87% critical chance. Critical chance can come from set bonuses, cp passives, armor passives, class passives etc.

So all you have to do is to add up all flat values and divide them by 219 to get the %-value and then add that to the %-buffs you have:

Critical Chance = (Set Flat Spell Crit + Skill Flat SpellCrit + Buff Flat SpellCrit)*(1/219) + 0.10 + Item % SpellCrit + Mundus % Spell Crit + Skill % Spell Crit + CP % Spell Crit


The base critical chance is 10%, which you find as a flat value in the formula above.

NOTE: Proc Sets, so flat damage sets do not benefit from critical, because they are unable to critically strike. So if you want to use many of those in your build, critical chance is likely not that beneficial to you. Same holds for critical damage.
2.2. Critical Damage and Critical Resistance

Critical damage is only applied when you do a critical strike. So if you have 50% critical chance, you will get critical damage in 50% of cases. You always have a base critical hit damage of 50%, so in any case, you get that bonus damage. In PvE, critical damage is easy to calculate:

SpellCritDamage = (CP % Spell Crit Damage + Skill % Crit Damage + Mundus % Crit Damage + Set % Crit Damage + Item % Crit Damage + Buff % Crit Damage + 0.5)

So again simply add up all source you have and the base value of 50%. In PvP, a second factor influences the amount of critical damage you do and receive, namely critical resistance. Critical resistance can be obtained through the cp passive "resistant", set bonuses and impenetrable armor. Both indicate crit resistance as flat values, so we have to translate it into % values so we can compare it to critical damage. 6600 critical resistance mitigate 100% critical damage, so we can say that 66 critical resitance are equal to 1% less critical damage you take:

Critical resistance in % = (Item Flat Crit Resist + Set Flat Crit Resist + Skill Flat Crit Resist + CP Flat Crit Resist)/6600

NOTE: In PvP, this stat is fairly important because other players can (and will) critically strike against you. Also note that in no-CP campaigns, critical chance is lower, so invetsing into critical resistance is less useful there. In PvE, enemies can NOT critically strike, so critical resistance is not useful there.
2.3. Critical sets and cp increases.

Due to the CP cap increases we get with many updates, we can put more points into critical damage done cp passives. This results in a slow takeover of sets that give you critical chance, because their effectiveness increases with more points put into the cp-star elfborn, as i stated above. This resulted in many players saying that mother's sorrow is universally better than julianos. This is not true (at least not yet): The two sets are within a narrow margin of each other, mother's sorrow is only better if you have major and minor force available at a rate that is very high (often unrealistically high) and if you are a nightblade or templar. Further, when comparing the sets, you have to consider that critical chance buffs enchantment (and poison) damage, while spell damage does not. This gives mother's sorrow another edge over Julianos. Nonetheless, dont let someone rip you off by paying 500k for a staff of MS, instead, craft yourself Julianos and do something useful with your money. Send someone tons of potatoes, for example.
3. Damage Done

Damage done is basically the universal damage amplifier that affects any damage you do, or a certain type of damage only. There are damage done cps for damage over time effects, direct damage, elemental damage and weapon specific damage done bonuses within the blue cp tree. When you want to calculate the damage you do with a skill, you have to consider these amplifiers and choose the right amplifiers as well.

Here's also where everything comes in that wasn't there before that is not a proc. All other sources of damage done (major and minor slayer, animal companion passive, swords damage done passive, minor and major berserk, warden passive) get added up here, so they all work additively. As always before the relation holds that the more you already have, the less benefit you have from additional damage done passives.


Since the majority of damage done passives come from cp, damage done is more effective in no cp content, which is why using a sword can be a viable option.
3.1. Choosing the right CPs

Knowing whether a skill is magic damage, physical etc is fairly easy since it is stated in the tooltip. The difficult part is to assess whther the skill is considered as direct damage or damage over time. Damage over time abilities are either ground-based aoes or debuffs. Both tooltips generally indicate that the ability does something over a certain period or periodically for a timespan. But there are also combinations of the two that deal initial damage and have a seperate DoT-component. Examples are:
Direct damage:

Thrust your weapon with disciplined precision at an enemy, dealing ? Physical Damage and taunting them to attack you for 15 seconds.

This ability is considered as direct, because it only has a one-time hit that occurs immediately.
Pure DoT-Damage:

Unleash a swarm of fetcherflies to relentlessly attack an enemy, dealing ? Magic Damage over 10 seconds.

No initial hit indicated in the tooltip, only the damage over time component.
Combination of direct and DoT:

Slice an enemy with both weapons to cause deep lacerations, dealing ? Physical Damage with each weapon and causing them to bleed for an additional ? Physical Damage over 9
seconds

Here we have an initial hit that is considered direct damage and a damage over time component.

What does this tell us? You have to choose the right CP-Constellation to suit your damage distribution. If you have lots of direct damage (as nightblades do for example) then you will most likely invest more into master-at-arms. If you are more DoT oriented (as dragonknights are), then you will put more into thaumaturge. Weapon cp trees only affect your light and heavy attacks, so these are a bit more niche than the others, but it can be worth putting a few points into these as well, especially after the scaling changes of light and heavy attacks in summerset.
If you use a lot of proc sets, then elfborn and precise strikes might not be the best for you. I recommend using constellations and combat metrics from @Solinur , because these addons tell you exactly what kind of damage (direct or DoT) you do and which skill does which percentage of your damage so you can build around that.

Combat Metrics Add-On:

http://www.esoui.com/downloads/info1360-CombatMetrics.html

Constellations Add-On:

http://www.esoui.com/downloads/info1736-Constellations.html
3.2. Jump points and diminishing returns in CP stars

The damage done cp points have jump points. What does this mean? They round the benefit you get to the lower full % value. So if you have 15.3% benefit from the elemental expert tree, then you will only get 15% instead of 15.3%. Take this into account when you build our cp distribution to not waste any points. Find a constellation that lets you always be just above 1% in your damage done cps, and then put the rest into spell erosion/piercing for more penetration for example, which does not show any jump points.

Secondly, cp stars show diminishing returns. The more you invest into one star, the less benefit you will have. With the first 64 points into mooncalf, you get 13% recovery. The last 36 will only net you 2% recovery, so it is not worth putting more into there. Try to distribute them in a way that gives you a good "return on investment". Generally, points above the high 60's are mostly detrimental and you'd be better off choosing another star instead.
4. Armor Penetration and Mitigation

This is probably the most complex part of damage calculation, simply because the formula is a bit unintuitive. In ESO, every enemy (may it be a NPC or a player) has a resistance value. You can circumvent that resistance by using items and passives that let you "pierce" through the armor and deal higher damage to the target. So in general, you want to circumvent all armor the enemy has to deal "true" damage. This can either be achieved through own penetration, meaning all sets, buffs etc that increase your own armor penetration rating, or through debuffing the enemy, and thus reducing resistances. There are % amps and flat stats for penetration, and I will go through it in detail.

The formula looks like this:

Armor Mitigation =1-((((Target Resistance - Target Debuffs)*(1 - % Penetration ) - Penetration)/(Target.EffectiveLevel * 1000))))

So we start with 1. We start with one because the "true" damage let's us do the full damage. If we manage to achieve the full penetration, we simply do not deduct anything from 1, and therefore do the full unmitigated damage.

Then we have the target's resistance, which is 18200 in PvE for all veteran content mobs and target dummies. In PvP, it depends on how much spell or physical resitance your target has. Then we deduct all the debuffs the target has on it. There are multiple debuffs that apply to this category, such as major and minor fracture or breach (5280 and 1320, respectively), the 5- piece of roar of alkosh (3010) and the crusher weapon enchantment (which is amplifiable with torug's pact and infused and yields 1622, 2108 and 2741, respectively).

Afterwards we deduct % penetration amps, such as the Maul + Mace bonuses that ignore up to 20% of the target's resistance. The key takeaway here is that these %- amps are applied after debuffs, but not after your own penetration. This means that major and minor fracture reduce the effectiveness of mauls and maces, but sets like spriggan, twice-fanged serpent, penetration cps etc do NOT. So be aware which debuffs you have available, because if there are only few debuffs, you might even be better off with a mace over a dagger. The Break-even point between amces and daggers lies somewhere around 5000 & 6000 of penetration debuffs (which is often achieved in trials, but less in four man and solo content). I can provide statistics on this upon request.

After that, your own penetration value is deducted, so here's where most of the sets and the lover mundus belong. You might notice how penetration is mostly shown as a flat value, such as 5280 and 1320 for the major and minor debuffs. This needs to be converted into a % value so we can multiply it with the rest. That's what the denominator of the above formula is for:

The effectiveness of penetration depends on the level of the target. In PvE, enemies are considered as level 50 because they don't have CPs, so the denominator in these cases is 50000, while in PvP it is mostly 66000.
In no cp pvp, players are also considered as level 50, so here it is also 50000.
NOTE: There is a type of damage that ignores armor resistance either way, oblivion damage. Oblivion damage cannot be mitigated, so skills that indicate that they deal oblivion damage will always inflict their true damage value. They are often based on the enemy's health. This is mostly irrelevant for PvE, but in PvP, this is often an effective strategy against targets with high resistances and high health values.
5. Damage Taken

This is one of the more interesting debuffs, because it is basically the only one that mostly gives you the damage buff it shows in the tooltip, because there are not as many debuffs giving you that option. Debuffs falling into this category are Engulfing Flames (up to 10% Flame damage taken based on spell damage and maximum magicka coefficients), Incapacitating Strike/Soul Harvest (20% damage taken from your attacks), Minor Vulnerability (8% damage taken), Major Vulnerability (30% damage taken), Martial Knowledge Item set (8% damage taken), Z'en's redress item set (1% per DoT you applied to the enemy) and the Morag tong set (10% Poison damage). Additionally, Dragonhold introduced the stagger debuff on stamina Dragonoknights, letting the enemy take 195 more damage on anything that hits them. Similarly, harrowstrom added Draugrkin's grip, whicha dds 617 damage taken to the enemy.This debuff damage can be amplified by other damage taken amplifiers such as Minor + Major Vulnerability, critical chance and damage and circumventing enemy penetration, but will not benefit from personal damage done amplifiers such as CP or Minor / Major Berserk.


The formula is easy (unverified for flam damage taken debuff):

Damage taken = (1+ Sum of Flat Damage Taken)*(1+Sum of % Amplifiers)

So you add the flat values in, add up all sources of damage taken and 1, and then multiply the two components.
Part Two: Special Cases

Now that we covered the basic calculation of damage, we can go into a few specialties, such as damage types, status effects and enchantments, proc damage, oblivion damage, rotations.
1. Damage Types

There are 8 damage types in eso, namely Magic Damage, Fire Damage, Shock Damage, Frost Damage, Oblivion Damage, Physical Damage (including bleeds), Poison Damage and Disease Damage.
All of them are used by different skills and classes. Magic damage and physical damage are the "neutral" sources of damage, so they do not apply any status effects. More importantly, poison and disease are not considered as subcategories of physical damage, so things that specifically buff your physical damage do not necessarily buff the other two. Same holds for magic damage and fire, shock and frost damage. There are sets that buff only abilities of a certain type. If you consider using these, I recommend using combat metrics to check how much of your damage actually is from that specific damage type and then you can compare it to something that possibly buffs all your damage to see whether it is useful or not.

As a starting point, you can check which kind of damage you have and which sources you can use to amplify the damage you have:


Screenshot_2018-07-30-23-55-062.png

Cells with an X indicate that the damage source (indictaed in columns) buff the damage type (indicated in rows).


3. Status Effects and enchantments

Many of the abovementioned damage types have the chance to apply status effects. Status effects are a fun gimmick in eso and have become a fairly integral part of many builds, given that they can be very powerful if they are used right. All of these scale with your highest resource (meaning either spell damage and magicka or weapon damage and stamina) and they can critically strike, so even a stamina dk can deal damage with fire abilities and burning. In this case, the charged trait is interesting, and we will go through the chances of applying these effects in this chapter as well.

Here's a list of status effects and their functionality:


Burning: Applies on Fire Damage ; 4 Second DoT that ticks three times (at 0, 2 and 4 seconds)
Concussion: Applies on Shock Damage ; Direct Damage hit and applies minor vulnerability to the target for 4 seconds, increasing their damage taken by 8%.
Chilled: Applies on Frost Damage ; Direct Damage Hit and applies minor maim to the target for 4 seconds, reducing their damage done by 15%.
Poisoned: Applies on Poison Damage ; 6 second DoT that ticks 4 times (at 0, 2, 4 and 6 seconds) ; significantly lower damage than Burning per tick
Diseased: Applies on Disease Damage; Initial Hit and applies Minor Defile to the target, reducing their healing taken and health recovery by 15%.


3.1. So when do they get applied?

Here's a list (taken from older patch notes):

Weapon enchants 20%
Standard ability 10%
Area of effect abilities 5%
Damage over time abilities 3%
Area of effect damage over time abilities 1%
Light and Heavy Attacks 0%

So Enchantments are very effective in proccing status effects, so take that into account when choosing an enchant for your build. If you need minor vulnerability, go for shock. If you need higher burning uptime to strengthen your own blockade, use fire. If you have all these buffs available already (e.g. on a Dragonknight) use an absorb magicka enchant for higher sustain. You can either use the charged trait, torug's pact or the infused trait to increase your status effect chances, and there are passives and sets increasing it as well. While wielding a destruction staff, your chances are increased by 100%. This does NOT mean that you will always apply it, but that your chances are doubled. Here's the formula:

Chance to apply Status effects = Base Chance*(1+% increases)

So with a destruction staff, the chances will be doubled. If you use charged on top (220% increased chance), you will have a to multiply the base chance with 4.2 (Base chance*(1+100%+220%)). Infused basically doubles the chance, as it doubles the speed at which the enchant goes off (reduces cooldown by 50%).

3.2. Wolfhunter Update, Status Effects and Enchantments

The Infused Trait will carry over to the front bar, so if you have infused on the back bar, you will proc it more often on the front bar as well (ONLY the back bar enchantment is affected). Charged will not carry over, the destruction staff passive for status effects also does not carry over.

I tested this thoroughly by examining the status effect chances of each combination:

Infused staff procs every two ticks of elemental blockade. Charged procs every four and leads to a status effect chance of the enchantment of roughly 40% (27 out of 65 in my test). Precise leads to the same result as charged, so charged does not affect the front bar. Same goes for the destruction staff passive. With a resto staff front bar, the proc chance drops to 20%, so you lose half of your proc chance of status effects (11 procs out of 54).

What is possibly however, is to use charged and /or torug's pact on the front bar and have it affect your back bar enchantment, so you can use an infused fire enchant on the back bar and if you you swap to a charged staff the chance for burning is increased. Here i had 67 status effect procs out of 80 (84%).

4. Proc Sets

Proc sets have been item to debates ever since they have been introduced. They basically give you free damage and do what a skill would do, but bound to certain conditions. So the general notion is: If you do X, then you have a Y% chance to cause Z damage (sometimes over W seconds). These are interesting because they allow a certain amount of damage without relying on a perfect rotation. So they are especially interesting for players that don't have the time to invest into rotation practice or simply are new to the game, becasue they can still do enough damage with these sets. I wanted to talk about them because they are basically everywhere in the game. Especially now that the relequen set was introduced, they even reach into many high-end trials.

Proc sets do only scale with damage done and penetration. So you can NOT increase their effectiveness by achieveing higher stats. So if you want to build around these sets, go for penetration and damage done, such as major+minor slayer and the lover mundus stone.

5. Oblivion Damage

This damage type is interesting, because it always inflicts the damage it shows on the tooltip, no matter what the the emeny does. It circumvents passives, armor mitigation and shields, and therefore can be very effective in PvP. In PvE, it is mostly irrelevant. While it is good to fight against targets that shield stack and have high resistances, it is also very easy to make it too strong because there is no other counterplay other than trying to outheal it somehow.

With Elsweyr, Oblivion Damge was altered to be %-based on your Enemy's Health. So it will inflict 3% of the health of the target on Sloads Semblance, for example. This means that it is very strong against high health targets, and weaker against low health targets. Also, they have an upper limit to the damage they can inflict (oblivion enchant has 4875 damage as the upper limit for example). Note that Oblivion enchantments will not be boosted in strength by the infused trait (neither damage done nor upper limit), they will only proc more often.

6. Rotations

Rotations are the core of damage dealing, may it be in PvE or PvP. In both aspects of the game you want to use your skills as effective as possible, line them up in a certain order so that you achieve the highest damage without wasting resources and casts. As for PvE, rotations are often muscle memory. Here's a guideline on how you can try and idealise your rotation.

1. Don't copy a rotation from high-end players. It is far easier to memorise things you come up with yourself. Use other builds as additional input, but come up with your own build. Have a look at the skills that are available to you. Look at the cost, the damage they do and the duration they have. Optimize step-by-step and then consider other guides to see how you can improve.
2. Structure them in a way on your bar that is easily memorable and suits their duration. Line them up clockwise or counter-clockwise so you simply use them one after the other, and some twice or three times in the case of a spammable.
3. Practice on target dummies. It sounds boring and can be frustrating in the beginning, but if you cannot do good damage on one of these, how will you do it in a raid later on?
4. Slowly adjust your rotation to your needs. It is muscle memory, so it will take time.
5. If you go into a new trial or dungeon, ALWAYS leave slots for utility skills. May it be a shield, vigor, whatever. No need in tryharding for the highest dps if you dont know whats going on.

Part Two: Resource Management


While maximizing damage, it is important to take the amount of resources into account, we have figured that out earlier. It is also important to not run out of juice while in combat, because without resources to cast skills from, damage will drop significantly.
In ESO, that is commonly accounted for under the consideration of sustain. In order to maximize damage, you want a level of sustain (or resource management) that lets you not run out of resources until the very end of the fight, or in PvP, lets you sustain as long possible, ideally infinitely. Running out of resources in PvP is a quite certain death.
So if damage maximization is the goal, sustain is a secondary constraint mechanic that needs to be considered. There are various ways of resource gain in ESO, and we will go through them all step-by-step here. They can be classified into four categories: Recovery, Cost Reduction, Heavy Attacks and Flat Restorations.
4.1 Recovery

Recovery is a core mechanic in ESO that everyone automatically has access to. It restores health, stamina and magicka every 2 seconds. Health recovery has a base value of 309 at full level, while stamina and magicka recovery have a base value of 514.

The formula for recoveries generally looks as follows:

Recovery = (Base Value + Flat Recovery Bonuses)*(1+%-Amplifiers)*(1-%-Debuffs)

If you want to convert it to a value per second, you have to divide the formula by 2 because it ticks every 2 seconds by default. It is important to note that the debuffs that are applied to you are not deducted from your Amplifiers, but multiplied instead, making them more effective. Debuffs can be any defile you take, which reduces your health recovery by a %-amount, or the Siphoner CP star, which decreases enemy’s recoveries (all three) by a %-amount). A simple example would be to have base health recovery, with minor and major fortitude and major defile on:

Health Recovery = (309 + 0)*(1+20%+10%)*(1-30%) = 280

So, the 30% do not cancel out, because the defile is applied multiplicatively. Similar to spell damage, critical chance etc., recoveries also have major and minor buffs that amplify them by 20% and 10%, respectively:

Magicka – Intellect
Stamina – Endurance
Health - Fortitude

Only health recovery has a major and minor debuff that reduces it, called defile, reducing it by 30% and 15%, respectively. Health recovery is not a sustain mechanic per se, but it makes sense to explain it together with the other two. There are too many buffs and amplifiers to name them all here, but they all follow the formula as shown above.
A specialty to recovery is that it can be stopped by actions you perform. Sprinting and blocking will stop your stamina recovery while active, and blocking with an ice staff and the tri-focus passive or casting mist-form (vampire skill) will stop your magicka recovery. So if you play a build that sprints a lot or blocks a lot, you should be careful not to invest too much into stamina recovery and go for a reduction in cost of those actions. This brings us to the second sustain tool: cost reduction
4.2 Cost Reduction

Cost reduction is another core mechanic of resource management in ESO. It reduces the cost of your active skills, and therefore contributes to sustain as long as you keep casting something. Here, we can identify a clear tradeoff between cost reduction and recovery. Recovery ticks all the time as long as you do not stop it by performing the abovementioned actions. Cost reduction on the other hand only has a benefit while you are casting skills, or perform the abovementioned actions.
The formula for cost reductions looks as follows:

Skill Cost = (Base Cost * (1 - CP Cost Reduction) - Flat Cost Reduction)*(1 - % - Cost Reduction)

This formula has two key takeaways: firstly, % - Cost Reduction is applied after any flat cost reduction. This means that there is a diminishing return between the two. The more flat cost reduction you have (from jewelry glyphs for example), the less beneficial your % - cost reduction will be (your wind walker medium armor passive for example). Keep that in mind when you go for cost reduction. Secondly, there are cp passive that circumvent this, namely the Foresight and Unchained cp perks. They always apply to the base cost, making them very effective compared to the other cost reduction sources.

Also, stamina cost reduction applies to ALL things that use stamina, unless it is specified otherwise in the tooltip. So, it generally includes Block / Dodge / Sprint / Break Free as well. Also note that stamina skills in ESO have a 15% lower cost. Weapon lines have passives that reduce the cost by 15%, and class skills have that built into their kit by default.

In summary, there is a few things that we can infer from the sustain analysis so far:

• Recovery is most effective when you do not block or sprint much, or when there are breaks in between fights where you can recover.
• Investing heavily into cost reduction through flat and %-sources yields high diminishing returns.
• Cost reduction is best used when you know that you will keep casting skills without noticeable breaks, or when you use a lot of actions that drain resources in between fights as well.
4.3 Heavy Attacks

Heavy Attacks in ESO also restore resource when they are fully charged. Note that some of the weapons do not require you to fully wait until the animation is finished to grant the resource restore, meaning that you can loosen that button earlier. They deal damage and provide sustain, so they are a quite important tool for sustain that you can use.
The formula for the heavy attack resource restoration looks as follows:

HA Resource Restoration = (Base Value * (1 + %-Restoration Amplifiers) + Flat Bonuses) * (Block Reduction)

The base value is weapon-specific and varies depending on the duration of a fully-charged heavy attack. The following base values are all taken on fully leveled characters.

Bow – 2724 ; Dual Wield – 1667 ; Twohander – 2426 ; One-Hand and Shield – 2024 ; Inferno / Ice Staff – 2823 ; Lightning Staff – 3633 ; Restoration Staff – 3219 ; Werewolf – 1617

On top of that base value, % amplifiers are added as usual. Prominent examples are the tenacity CP star, the heavy armor passive revitalize or the Ulfnor’s Favor set. Attacking an enemy that is currently off-balance with a fully charged heavy attack adds another 100% to this variable So when you need resources, attacking an off-balance enemy is the best way to get them, especially since the heavy attack will do another 70% damage. Added on top of the post-amplified restoration are flat buffs, such as the Maelstrom 1H&S set (Rampaging Slash) or the Arch-Mage set.
Lastly, it is important to note that enemies can halve your restoration by blocking the heavy attack. So if you see an enemy heavy attacking you, blocking it (if you cannot dodge it) is another feasible way of reducing the effectiveness further.

4.4 Flat Restorations

Besides the threeabovementioned mechanics, ESO has a lot of other factors that grant resources back. I will not go through all of them here, but will mention some of them that are most commonly used, such as Minor Magickasteal, Undaunted Command and the Combustion / Shards Synergy and Class-Specific Sources.

Minor Magickasteal is very important due to its strength. Magicka skills in ESO have a 15% higher cost compared to stamina skills (as mentioned above), and minor magickasteal can be used to cancel that. The 15% cost reduction on stamina skills is also why there is no minor staminasteal in ESO. Minor Magickasteal restores 300 Magicka whenever you deal damage to a target inflicted with the debuff, which is one of the most powerful sustain tools in the game, in both pve and pvp. Also interesting in that regard is the undaunted command passive. It restores 4 % of your resource pools to you whenever you use a synergy. In group content, this can be very useful and significant, as long as there are enough synergies around to use.
Paired with the combustion synergy that comes from the necrotic orb and its morphs or spear shards and its morphs, this is a very potent sustain tool. The synergy from these abilites restores 3960 magicka or stamina, whichever resource pool is higher. With scalebreaker, the necrotic orb skill was changed to allow any ally to activate it, instead of one per orb cast. In any group, may it be pve or pvp, this skill is mandatory to have because of the large sustain improvement it grants to the whole team.

Every Class in eso has different flat sources of sustain, and i will list the main sources of classes on here:

Sorcerer - Dark Conversion and Morphs ; Rebate Passive ; Endless Fury Morph
Dragonknight - Battle Roar Passive ; Combustion Passive ; Helping Hands Passive
Warden - Betty Netch and Morphs ; Nature's Gift ; Crystallized Shield and Morphs
Necromancer - Death Gleaming Passive ; Mystic Siphon Morph ; Expunge and Modify Morph
Nightblade - Siphoning Strikes Morphs ; Executioner Passive
Templar - Rune Focus and Morphs ; Repentance


Big shoutout to @Reorx_Holybeard and the UESP crew. The Build Editor where you can find all these formulae as well and play around with builds can be accessed here:

http://en.uesp.net/wiki/Special:EsoBuildData



Hello everyone! A long overdue update to this thread has now been made. Many changes were made, lots of values got changes since I last updated this and the new champion point system changed a lot as well. But lets get into it.

CALCULATIONS:

We will start off with the base calculations with only your own mitigation. There are two main ways that mitigation works, BEFORE or AFTER a damage shield has been hit. This means that some sources of mitigation will reduce the damage taken before a damage shield takes damage from the attack and others will reduce the damage that overflows from a potentially depleted shield. However, if there is no damage shield then all sources count as being on the same level. The only known sources of mitigation AFTER a damage shield is the base blocking mitigation and any source that says "increases the amount of damage you can block by x%" or similar, all other sources of mitigation is applied BEFORE a damage shield.

Now with the change of the champion point system there are some sources of damage mitigation that stack additive together before being multiplied in. Hardy/Elemental Aegis+Preparation+Duelist Rebuff/Unassailable/Enduring Resolve. These stack together. Hardy and Elemental Aegis obviously can't be used at the same time cause of the different damage types, however the 3 damage forms work differently depending on how many are used. Enduring Resolve can work at the same time as Duelist Rebuff or Unassailable however only one of them can stack additive with the rest at any given time, the other one gets multiplied in as a separate source. They stack additive with the one that has the largest value if their values differ. Juggernaut is the only non block related Champion skill that does not stack additive with the rest, it acts like a unique source.

The other two Champion skills are both related to blocking, "Fortification" and "On Guard", they both stack additive together with all other sources of extra block mitigation. They can all work at the same time, and stacking multiple sources can give you quite a lot of mitigation. With the addition of the advanced stats screen its really easy to keep track of how much block mitigation you got, it will even do the calculations for you. One thing to note though is that "On Guard" will only be added to that stat if you are currently CC immune, and skills like Bound Aegis and Immovable will only appear while the skill is active. Deflect bolts however, being situational to only ranged and projectile will not appear at all, so has to be taken into account by yourself. Now something else fairly important for some to know is that blocking mitigation is capped at 90% this is cause it was possible to achieve mitigation past 100% making you immortal. Had that not been implemented, with this update, it would have been even easier to pull off, I got 107.5% without really trying. Oh and the current advanced stat screen will still show values past 90% for some reason, should probably be looked at.

The heavy armor bonus that grants extra blocking mitigation, behaves in a way I was not expecting. Instead of being additive with all the other sources like previously mentioned it is added into the blocking mitigation after the extra blocking mitigation has been multiplied with the base blocking. This prevents some of the diminishing returns on the bonus, making it much stronger than one might first see. The light and heavy armor bonuses for magical or martial mitigation is applied additive to the base mitigation making them slightly stronger as well. Lastly before showing and example of the formula I will mention that we now have a 10% base mitigation applied to us at all times and battlespirit for PvP has been reduced to 44% instead of 50%.

    Total Mitigation=100-100*(1-Battlespirit/100)*(1-Base Mitigation+Light Armor or Heavy Armor/100)*(1-Mitigation #1/100)*(1-Mitigation #2/100)*(1-(Resistance/660)/100)*((1-Blocking/100)*(1-(Extra blocking #1+Extra blocking #2)/100)-Heavy Block/100)

    Damage Taken=Base Damage*(1-Battlespirit/100)*(1-Base Mitigation+Light Armor or Heavy Armor/100)*(1-Mitigation #1/100)*(1-Mitigation #2/100)*(1-(Resistance/660)/100)*((1-Blocking/100)*(1-(Extra blocking #1+Extra blocking #2)/100)-Heavy Block/100)


The way you would use this template is to replace the place holders with the percentage numbers that is show in the tool-tips in the game and obviously the resistance should be the number of which ever resistance you want to test with. If you have more sources then just add more to fill your needs in the same way that is shown. Now something you might notice is that this way of calculating will result in diminishing returns, what that means is that for each added mitigation source the usefulness of each individual source gets reduced. As an example, having 2 sources that give 50% mitigation will give you a total of 75% mitigation. This now again has an exception with extra blocking mitigation and certain CP as they stack additive with one another, to add in the additive CP into the form just copy the way that extra blocking is done.

Lets do some examples using things the average tank would use. Lets make it a Dragonknight, for obvious reasons. So they would have 50% from blocking, lets say 40% from resistance, 5% from minor maim, 10% from the Iron Skin Passive and 20% from the Sword and Board Passive and 10% from base mitigation. The calculations would look like this:

    100-(100*(1-5/100)*(1-10/100)*(1-(26400/660)/100)*(1-50/100)*(1-(10+20)/100))=82.045


So with all of those sources added together we ended up with a total of 82.045% of the damage we take being mitigated. Now if we want to apply these calculations to see how much damage we would be taking from a hit we would just change it to be like this:

    150,000*(1-5/100)*(1-10/100)*(1-(26400/660)/100)*(1-50/100)*(1-(10+20)/100))=26,932


As you can see, even though the base damage we would have taken without mitigation was really high, just a few sources can drastically reduce the damage taken. Now I want to show you guys how this type of calculations would work if a damage shield was involved, cause as I previously explained blocking only mitigates damage that overflows from a depleted damage shield, while everything else will mitigate damage before the shield gets hit. If we use our previous example as our base but then add in a damage shield with the strength of 5000 it would look like this:

    (150,000*(1-5/100)*(1-10/100)*(1-(26400/660)/100)-5000)*(1-50/100)*(1-(10+20)/100))=25,182


In this case Minor Maim will hit first, as it applies to the attacker rather than the caster, secondly we have the base mitigation, and third resistance which was previously grouped with blocking but has since Murkmire been moved to be BEFORE the damage shield takes damage. Everything else mitigates damage AFTER the damage shield. Now on to the next bit in terms of calculations:

VULNERABILITIES:

Now since last I updated this thread vulnerabilities have gotten a big change. For those that don't know, vulnerabilities are effects that increases the damage that you take. With the changes to Light and Heavy armor we got 2 new sources of vulnerability, as wearing light armor makes you take 1% extra martial damage per piece and heavy does the same for magical damage. Now the way that vulnerability used to work is that they used to be additive together and then the first few mitigation sources would subtract them, this has changed slightly. What happens now is that vulnerability affects the base mitigation that you have. So for example if you have your 10% base mitigation with 5% from say Minor Vulnerability then you get only 5% base mitigation. Whats interesting here though is of course that the light and heavy armor bonuses also works upon the base mitigation that you have. So if you have your 10% base and get attacked with magic damage while under Minor Vulnerability but you have 5 pieces of light armor then you get to keep your base 10% as the 5% from light armor removes the 5% from Minor Vulnerability.

Now when the vulnerability outweighs the base mitigation then you obviously start taking a bit more damage. Something like Stage 3 or 4 Vampire against fire damage would do the trick on that. Now let me show you two examples. One with 7 Light bonus against Minor Vulnerability and then 5 Light Penalty working with Stage 4 Vampire

    Total Mitigation=100-100*(1-(10+7-5)/100)=12%

    Total Mitigation=100-100*(1-(10-7-20)/100)=-17%


Last one would show that you would take 17% extra damage. Any extra vulnerability would be added on just like in example 2. Now lets show how this would work from the last example we used with Damage Shields. We will add Stage 4 Vampire and Heavy armor Penalty.

    (150,000*(1-5/100)*(1-(10-7-20)/100)*(1-(26400/660)/100)-5000)*(1-50/100)*(1-(10+20)/100))=33,262


RESISTANCE:

So there are two main types of resistance which are Spell and Physical, but each of them also have sub categories. Spell resistance has Flame, Frost and Shock resistance and Physical has Poison and Disease resistance. Now one important thing to know about resistance is that there is a Hard Cap, that means that after you reach a certain point it won't give you anything extra. For Champion point 160+ characters the hard cap for resistance is 33,000, or 660 resistance per 1% mitigated, which then tops it of at 50%. You can have more resistance than what the hard cap allows but it won't give you more mitigation, however, in PvP if someone debuffs you then having resistance above the hard cap can sometimes allow you to stay at hard cap if the debuff is to weak or your buffed resistance is strong enough.

Another thing we need to address now is how those sub categories work with the main resistance types. Sub categories adds to their main type whenever the attack element is of the same element. As an example, if I have 15000 spell resistance and 5000 flame resistance then if I get attack with a fire spell then I will have 20000 spell resistance against that attack. One thing to note here is that if your Spell or Physical resistance is already at hard cap then your sub categories will not add anything, since they are just temporary increases to the main type if attacked by the right element. But again if you get debuffed then anything above hard cap will help you stay up. Last thing to note about the sub categories is that since they are in its base form just adding to their main type then if someone penetrates your Spell or Physical resistance then they will penetrate your sub categories too.

One last thing to remember is that even though players no longer has a base 100 penetration the mobs in PvE still do. So when trying to calculate your resistance in a PvE scenario one should always account for that. Penetration is of course a subtraction of your resistance so for example if you have 15000 resistance then against someone with 5000 penetration you only have 10000 resistance and then in PvE if you have 33000 resistance you will still not be at the proper cap as against PvE mobs you only have 32900. But now on to the next part of this thread and last form of resistance.

CRITICAL RESISTANCE:

Now critical resistance works very differently from the other forms of resistance. What it does is it lowers the enemy players critical hit damage modifier. A characters base modifier is 1.5 which means that if you land a critical hit then you deal 50% more damage. There are ways to improve this, such as minor and major force. What we are gonna be looking at of course is how we can reduce that modifier. This one is yet another subtraction one. Your critical resistance will lower the attackers critical modifier by a rate of 1% for every 68 critical resistance. This means that to remove an attackers base critical modifier you need 3400 critical resistance. It looks like this:

    CRITICAL MODIFIER=1.5+(Critical Damage Buff #1/100)+(Critical Damage Buff #2/100)-(Critical Resistance/68/100)
    Damage Taken=15000*(1.5-(1700/68/100))=18750


As this is the final calculation I will add this into our previous example and see how it all works in its entirety.

    (150,000*(1.5-(1700/68/100))*(1-5/100)*(1-(10-7-20)/100)*(1-(26400/660)/100)-5000)*(1-50/100)*(1-(10+20)/100))=42,015


I will add here though that 150,000 base damage is PvE numbers and PvE mobs cannot critically hit, but it goes to show that even just 25% extra critical damage can deal a lot more damage if your mitigation against it is not enough.

As a final note, I probably have a bit more to test to double check all possible combinations but I wanted to get this update out there, if you see anything wrong in the thread that I need to edit then let me know, and obviously if I messed up big times or forgot to test a specific scenario let me know. 