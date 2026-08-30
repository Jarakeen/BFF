------------------
##

I do most of my testing on the PTS, I don't have to pay for anything then. It also makes for a cleaner environment to work with as you can remove and add whatever you want without having to worry about the cost. Swapping passives on and off and checking their interactions with each other than the other sources. For example it took me a while to realize that the Block mitigation you gain from the new heavy armor bonus work completely different from everything else. Normal block mitigation works like this. Say we got Sword and Shield passive with Iron Skin from DK. Thats 20% and 10%, blocking is 50% so its.

100-(100*0.5*0.8*0.9)=64% mitigation.

add 5% for 5 pieces of heavy armor and you would think it would be like this

100-(100*0.5*0.8*0.9*0.95)=65.8%

However its actually like this

100-((100*0.5*0.8*0.9)-5)=69%

Meaning you get the full 5%, it does not get diminished by other sources of block mitigation nor block itself. Its added on top after blocking and extra block mitigation has been calculated. Which makes it a lot more powerful than one might think, especially when you go 7 heavy. 100-((100*0.5*0.8*0.9)-7)=71%. 71% mitigation from 3 passives while blocking, not bad at all, and that obviously does not account for any resistance or other buffs or CP.


-----------------
##
Total value = ((base stats + attribute points*value + gear)*CP%increase)*skill increase

 CP%increase = 1+1,00006*(total CP/3)^0,56432/100        

------------
##
✭✭
Last time I tested in 2.1.0 attributes calculated like this:

((Base Attributes + Attributes point + Trait + Enchant + Set+Mundus+Food+Battle Spirit+Emperor)+(Base Attributes + Attributes point + Trait + Enchant + Set)*(0.01*Related champion point^0.563)*(1+%set+%racial+%passive skill+%active skill)

Not every attributes "base value" scale with champion point.

Regeneration is confusing because each regeneration have their own formula and stacking order. Also changed a lot in some last patch.

For example magicka regen in 2.0 calculated like this:
(Base Regen + Enchant + Set+Mundus+Drink)*(1+(Light Armor's Recovery+Magicka Aid+%Set Bonus))*(1+Arcanist)*(1+Racial+Class Passive+Magicka Controller+Major Minor Intellect)

While stamina regen in 2.0:
(Base Regen + Enchant + Set+Mundus+Drink)*(1+%Set Bonus)*(1+Mooncalf)*(1+Other Passive)


-----------------
##
In The Elder Scrolls Online (ESO), buff and debuff stacking follows a strict rule where identical effects do not stack, but different tiers or unique sources do. The order in which you cast your abilities does not matter.

Core Stacking Rules

Same Name/Tier: Two identical buffs or debuffs with the exact same name (from the same or different players) do not stack. Recasting simply refreshes the timer.

Major and Minor: A Major buff and a Minor buff of the same type (e.g., Major Resolve and Minor Resolve) do stack together.

Different Names: Buffs or debuffs with completely different names or from separate passive/gear categories stack fully.4

Cast Order: There is no modifier or stacking order requirement for casting; you get the full effect regardless of which sequence you use your skills

----------------
##