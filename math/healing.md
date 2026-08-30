ve been looking around to find a Healing Formula for ESO but for the most part there is not much information out there for it other than a post from 5 years ago talking about it and only have bits and pieces of the formula talked about but never combined for anyone to see how to calculate their raw healing. I will be trying to update and clarify from this thread https://forums.elderscrollsonline.com/en/discussion/456919/healing-formula of what I have found and believe to be the formula ESO uses to calculate healing if not very close to it.

I will be showing the Raw Healing Formula in pieces since it is a very long formula. I will also combine and show the entire formula in the end for those who want to see the entire thing. To start I will be showing what I call the "Baseline Skill Formula" since this formula is at the core of everything we will be looking at. The formula starts out as below:

Baseline Skill Formula = (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient)

Max Resource = Your max resource which is either Stamina or Magicka (whichever is higher)
Resource Coefficient = The scale factor that the developers use for the amount of max resource effecting the skill
Max Damage = Your max damage which is either Spell or Weapon (whichever is higher)
Damage Coefficient = The scale factor that the developers use for the amount of max damage effecting the skill

The Coefficients are mainly used in this game so that every skill is unique in scaling for your healing, hence why some skills heal more than others. In order to find Coefficients in this game you have to add spell or weapon damage to your character and chart how much spell or weapon damage you did along with the healing output or damage output you saw without critical damage or healing. Then you graph your results with spell or weapon damage as the x axis with healing or damage as the y-axis, put in a trendline and formula, then verify your formula R^2 value equals 1 for a reliable coefficient for that skill (the same is applied to max resources to find resource coefficient). This has already been done for majority of the skill in the game and can be found here: https://en.uesp.net/wiki/Special:EsoSkills

The next formula is the Skill Formula which is added onto the Baseline Formula with only the Skill Modifier added. The Skill Modifier is a number the developers use in order to increase the amount of healing that will happen if you level up your skill from level 1 to level 4 in the game. Not all skills have a Skill Modifier in this game meaning they do not increase healing output as they level up from level 1 to level 4. All Skill Modifiers for Healing in this game that I am aware of are .033 or 3.3%. When we add in the Skill Modifier we get the following formula below:

Skill Formula = (Skill Modifier*((Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))+ (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient)

The formula above is the healing formula you would use if you had no healing buffs or powered trait weapons. To add in healing buffs we do similar to what we did with how we added in the Skill Modifier getting the following formula below:

Buffed Formula = Skill Formula + (Skill Formula)*(Healing Done + Healing Taken + Healing Received)

Healing Done = All heals output by yourself increase by x%
Healing Taken = All heals your character takes are increased by x%
Healing Received = All Heals your character receive are increased by x%

Healing Taken and Healing Received act the same as in healing buffs but Healing Taken is a bonus gotten from sets while Healing Received seems to be more a buff you get from minor/major vitality in this game. To note is that if a character has more Healing Taken or Received you will see a difference in your healing if you heal them over other players that do not have that buff, meaning when calculating your raw output healing I personally would exclude the buffs Healing Taken and Healing Received because it is not guaranteed that everyone in the Trail/Dungeon/PvP zone will have these buffs while you are healing them.

The last thing added onto the raw healing formula would be the powered weapon trait which adds onto the formula similar as the rest giving us below:

Raw Heal = Buffed Formula + Buffed Formula*Powered Trait

For calculating all of the numbers in this formula you will need to convert everything from percent to decimal which means if you have a 4.5% increase healing done from the powered trait on your restoration staff you will use 0.045 as the number for powered trait in this formula (This applies to Healing Done/Taken/Received and Skill Modifier as well).

Now for skills that scale off of Max Health you will use this exact same formula format but the only thing you will change out is the Baseline Skill Formula, instead the Baseline Skill Formula will look like this:

Baseline Skill Formula: Max Health*Max Health Coefficient

The formula actually becomes a little simpler with only one thing they are scaling off of. You just replace this formula and plug it into the all the rest listed above to get your raw output heal.

For skills that scale healing based on the damage like Soul Tether it is explained in the tool tip that you heal from 50% of the damage you do to an enemy which is pretty easy to understand but hard to calculate due to in PvP people having different armor ratings than all mobs in PvE so I chose not to make a formula to explain how to calculate the amount of healing you will do for that since its easy to understand.

Now to show the entire formula without it broken up we get a Raw Healing Formula that looks as follows:

Raw Healing = (((Skill Modifier*((Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))+ (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient)) +
((Skill Modifier*((Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))+ (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))*(Healing Done + Healing Taken + Healing Received)) +
(((Skill Modifier*((Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))+ (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient)) +
((Skill Modifier*((Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))+ (Max Resource*Resource Coefficient) + (Max Damage*Damage Coefficient))*(Healing Done + Healing Taken + Healing Received))*Powered Trait

As you can see the formula gets ugly fast so I suggest cutting it up into parts like I showed above in order to calculate your raw healing.

Now onto Critical Healing in this game. Critical Healing in this game is fairly easy to calculate if you have your numbers. The formula looks like the following:

Critical Heal = Raw Healing*Critical Healing %

Critical Healing % = The percentage amount you have that increases a raw heal by x% (maxes out at 125%)

Critical Healing % is not easy to increase as far as I know in the game (compared to critical damage %) and the baseline critical healing % is 0.5 or 50%. Critical Healing by far is the best type of healing if you can keep it consistent, however when calculating your healing to see if you can heal someone in a tight spot I personally would not rely on critical healing numbers because it is not reliable. Critical Healing also gets a little weird when you throw in set bonuses for healing into the equation, I made a post about it awhile back but have yet to get a response or any traction on whether this is an intended thing in the game or something that was overlooked. The thread post: https://forums.elderscrollsonline.com/en/discussion/659311/set-bonuses-healing-done-healing-taken-not-scaling-for-critical-healing/p1?new=1

To make things easier though for calculating healing on skills I made a google spread sheet with every heal that I could calculate (practically) in the game with only you needing to add in values of your choosing to see what your output healing will look like if you had certain resources allocated in certain areas before you go out and make a build and realize the build was not as good as you thought or better than you thought. Keep in mind this may not be perfect since this is a personal spreadsheet that I use to help me understand as a Raid Lead and player what healing should look like in certain scenarios and what is possible whether if the healer in my group is not performing or is not practical for them to do something.

Link: https://docs.google.com/spreadsheets/d/1qSrCN0aioQgb9VF55SpBH-jqFSRWwb5vbdzBs7n9vLc/edit?gid=943729168#gid=943729168

Everyone with a link can go in and edit only the highlighted yellow areas and everything in that one sheet will update to give you a healing output number that is very close to what you will see in game. Please note that this is all unrounded calculations and ESO developers round off values during their calculations so my numbers will be slightly higher than theirs but very close, you will get a rough idea as to how much you will heal though with this spreadsheet. Make sure that you account for all healing buffs in this game such as mundus stone/passives/buffs/champion points when entering values in this spreadsheet and it should come out very close to what you will see in game. I suggest making a copy of this spreadsheet for yourself and if you want you could unlock the sheets once you have your own copy and you can do whatever you want with it, currently everything is locked so no one can edit outside the highlighted areas (the numbers at the top of every spreadsheet for baseline values/stats). The reason I suggest this is if multiple people use this spreadsheet at the same time you will likely conflict with each other if entering numbers in this spreadsheet.

As a note the baseline stats for a character currently are:
Magicka: 12000
Health: 16000
Stamina: 12000
Magicka Recovery: 514
Health Recovery: 309
Stamina Recovery: 514
Spell Damage: 1000
Spell Critical 10.0%
Spell Penetration: 0
Spell Resistance: 0
Physical Resistance: 0
Critical Healing: 50% (Base Game value)
Healing Taken: Flat = 0 Percent: 0%

If anyone finds anything wrong with what I have posted here and can prove it please post below/tell me in this thread so that way we can get correct formula's or get a better understanding on how healing in ESO works, since majority of what I see out there is that not many people really know how it works. 

https://forums.elderscrollsonline.com/en/discussion/661578/healing-formula