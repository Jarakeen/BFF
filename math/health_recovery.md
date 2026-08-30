
I've been looking around to find a Healing Formula for ESO but for the most part there is not much information out there for it other than a post from 5 years ago talking about it and only have bits and pieces of the formula talked about but never combined for anyone to see how to calculate their raw healing. I will be trying to update and clarify from this thread https://forums.elderscrollsonline.com/en/discussion/456919/healing-formula of what I have found and believe to be the formula ESO uses to calculate healing if not very close to it.

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

---------------------



 In-Depth Resource Management Analysis + Calculator for Elder Scrolls Online – Morrowind

1. Introduction
With the Introduction of the Morrowind Expansion, Resource Management became an integral part of the game by having less resource management tools and making the ones that are available less powerful. This guide is aimed to help newer players understand the resource management in ESO and give more experienced players a tool to theorycraft with a focus on sustain. I will go through the steps of the calculator in detail in this extract. I am currently doing my PhD in financial analysis, so you’ll notice a mathematically oriented approach to theorycrafting. I didn’t choose a more complex software, as most people have access to excel in some sort of way and are more likely to understand the calculator faster. I try to keep it as simple as possible and enhance it with graphs and diagrams to make it more interesting. Let’s do some number crunching!

Modelling to this extent is of course only possible under restrictions and certain assumptions on specific variables. This is an experimental simulator, but it matches actual ingame sustain with a very good accuracy. The guide is mainly focused on Magicka Characters right now, but I will include the Stamina Based Graphs and Tables wihin the next days.

2. Factors of Resource Management

There are multiple ways to approach resource management by yourself in the Elder Scrolls Online, notably: Cost Reduction, Recovery and Heavy Attacking. On either one of those, you’ll want to add as much additional resource restoration abilities and mechanisms as possible. But to begin with, we need to determine how the combat system and resource drain from skillcasting works.
2.1. Average Base Cost of Rotation

To assess how much resource return you need, we need to calculate the cost that your full rotation has and divide it by the length of it to arrive at the Average Base Cost per Second (referred to as AvCost from now on). All calculations in this text are done on a per second basis. This way you can immediately compare different setups by calculating the net resource gain (if it is positive) or net resource drain (if it is negative). Simply put, you know whether you’ll lose resources while executing your rotation or not and also, how fast you’re going to lose them. The formula is as follows:

Netresourcelevel=AvCost+CostRedu+Recovery+AddSustain

With CostRedu being the Resource gain per second granted by all your cost reduction buffs, Recovery being the Resource gain per second granted by recovery, and AddSustain being all additional sustain sources that apply after Cost Reduction and Recovery.

AvCost is a drain, so it is a negative variable. This negative drain gets reduced by CostRedu, leading to the Total Drain per Second. That Drain is then countered by recovery and flat resource restoration mechanisms. The respective points will be explained later on.
2.2. Cost of Skills

In order to determine the Average Cost of Skills, we need to list all the abilities in the rotation, their Base cost (without any reduction) and how often we use them in the rotation. Then multiply the number of casts with the Base cost and divide it by the duration of the rotation in seconds to arrive at AvCost. Formula is as follows:

AvCost=(Skill1Cost*n1+Skill2Cost*n2+…+SkilltCost*nt)/DurRota

So for example, 2x Force Pulse and one Elemental Blockade would lead to

AvCost=(-2700*2-3510*1)/3=2970

Important is that you use 1 skill per second, assuming perfect timing. I’ll introduce a variable that simulates imperfect weaving and skill casting in the next section as getting off 1 skill and weave every one second as basically impossible.

2.3. Global Cooldowns


As I already stated above, perfect weaving on the one second cooldown is impossible and we therefore need another term delivering realistic results. In order to achieve that, I simply used a Basic 0 to 1 variable that is multiplied with AvCost, namely SkillSpeed. 0 would mean you fire off 0 skills and light attack weaves per second, and 1 would indicate perfect weaving and skillcasting. This is the term you want to modify if the simulated drain is not matching your ingame drain. I mostly found a value between 0.8 and 0.9 adequate, but that depends on your capability to execute rotations.

So we then have

Netresourcelevel=AvCost*SkillSpeed+CostRedu+Recovery+AddSustain

This is the basic formula that determines your resource level. We’re now going to take a look at cost reduction in detail.

3. Cost Reduction


Cost Reduction was decreased a lot with Morrowind: 16% from Champion Point Passives and 1% per Armor Piece of Light and Heavy Armor. Stamina Builds even got another 5% increase on top. So your skills will now cost a lot more than before, making it harder to sustain rotations that use a lot and expensive skills.

The Cost of your Skills is therefore very important, and trying to decrease that is a very effective way to sustain, leading us to Cost Reduction.

3.1. Base Calculation


There are two ways to decrease the Cost of your Skills: Flat Jewellery Glyphs and different %-Bonuses.

The Basic Formula for Cost Reduction is as follows:

CostRedu=(AvCost+Sumflatcost)*(1-Sum%Cost)

Where Sumflatcost is the Sum of Jewellery Glyphs you have and Sum%Cost is the Sum of percentages decreasing your ski cost.

Example from above with 1 Cost Reduction Glyph and 5 pieces of light armor:

CostRedu=(-2970+203)*(1-0.1)=-2767*0.9=-2492

And one more time with only 5 pieces of light armor:

CostRedu=-2970*0.9=-2673, which is a full 10% decrease from the original 2970.

You see that when Sumflatcost is applied, you get less return from the Sum%Cost variable. It is only a marginal decrease in effectiveness, but it is still interesting and worth noting for the further analysis.

As Cost Reduction is depending on AvCost, the effectiveness is also depending on the SkillSpeed variable. When you keep casting skills, you get more return on cost reduction.

3.2. Comparing three different setups via calculator


1.png

Looking at the example above, you see that worm cult gives you a return of 80 when applied without a flat reduction glyph. The glyph always gives a 203 return (here 175 as it’s multiplied by 0.9 due to skillspeed). When used after a flat glyph, you have a return of 246-175=71. So you lost 9 Magicka per second by applying a cost reduction glyph and applying worm cult. Of course the reduction from armor passives is also going to get decreased the same way, as all Elements of Sum%Cost.

4. Recovery


Recovery is the second aspect of sustain in Elder Scrolls Online. It ticks every two seconds in and out of combat and restores a flat value of the respective resource pool. Blocking stops recovery, namely the stamina recovery with all weapons but ice staffs.

4.1. Base Calculation


The basic concept works as all (or at least most) calculations in the game:

Recovery=(Base Value+SumFlatReco)*(1+Sum%Reco)

As we want the value per every 1 second, we simply divide the above formula by 2, leading to

RecoperSecond=((Base Value+SumFlatReco)*(1+Sum%Reco))/2

Now for cost reduction, the Base value was negative, making Flat and Percentage Bonuses work against each other. Recovery is positive and is thus giving them a proportional positive.

The Base Value for CP 160 characters is always 514. You can add flat recovery bonuses from glyphs (174 each), sets regular bonuses (129 per item) and special 5-piece bonuses with varying values. The Percentage increases come from a lot of different sources, notably Armor (4% per piece of light and medium armor), Champion Points Arcanist and Mooncalf (up to 15%), class passives, racial passives, vampirism et cetera. I will provide a full list of recovery sources (excluding regular 129 armor bonuses) in the next section.

4.2. Now it’s interesting to see how much sustain recovery can give you in an ingame environment.


2.png

This is a real setup simulation. You see that we have an 86% increase on recovery without the Altmer Passive and 95% with it (28% Light Armor, 10% Vampirism, 12% Warden Passive, 2% Mages Guild, 14% Arcanist CP, 20% Major Intellect, 9% Altmer Passive). That increase gets applied on the flat value of recovery. We see that a glyph is an 162 increase, with 162=(174*1.86)/2. Adding a 9% on the 514 Base recovery is 23, with 23=(514*0.09). Adding both leads to and overall increase of 193 instead of 185, as we have 193=(688*1.95)/2-(514*1.86)/2. So both increases positively influence each other. The overall contribution to sustain by recovery in traditional setups is a lot higher than the contribution of cost reduction, as it is easier to stack and easier to get.

5. Additional Sustain Sources


On top of recovery and cost reduction, there are additional flat bonuses that increase your sustain. Some of them are only available to certain classes, and some of them are only increasing your Magicka or Stamina. I’ll go through the ones that are available to all classes in this section and then look into all five classes in section 6. In the calculator you can simply choose whether you want a certain buff to be active or not by toggling it as “Yes” or “No” in the blue area next to the buff name.

5.1. Minor Magickasteal


Minor Magickasteal is a debuff applied on an enemy that restores 300 Magicka to allies damaging them with a 1 second cooldown. So this is equal to a 300 Magicka gain per second. There are three sources of minor Magickasteal in the game: Elemental Drain from the Destruction Staff Skill Line, Radiant Aura from the Templars Restoring Light Skill Line and Force Siphon from the Restoration Staff Skill Line. Now you might ask why there is no minor Staminasteal, and rightly so. Stamina Builds have an inherent 15% cost reduction on their skills. If they also had a minor Staminasteal, sustain on Stamina Builds would be a lot easier than on Magicka Builds. Minor Magickasteal basically covers the difference between the cost of Magicka and Stamina based skills.

5.2. Orbs and Shards


Orbs and Shards is a term for two different skills that do the same thing now. One is available to all classes (Necrotic Orb/Energy Orb) and one is available to Templars only(Luminous Shards/Blazing Spear). Both of them restore 3960 Magicka or Stamina to the player using their synergy with a 20 second cooldown. Which resource they restore is based on the highest maximum of your resources, so if you have a maximum Magicka of 44000 and a maximum Stamina of 8000, you’re always getting Magicka. The Formula for the Gain per second is therefore

OrbShards=3960/20=198

This is assuming you using the synergy on cooldown, which is not realistic, but the calculator uses all additional sustain sources on cooldown as it is very hard to simulate a delay with a certain standard deviation to one side only. I mostly plan a certain level above 0 for NetResourceLevel to include delays in cooldowns on those additional sources.

5.3. Potions


Potions are a very important source for buffs in ESO. They have a cooldown of 45 seconds and restore a good amount of resources and grant major intellect or major endurance, giving you 20% more recovery for a maximum of 47.6 seconds. I am assuming that we use crafted potions as the give a lot more flat Magicka and a longer duration of major recovery bonuses. The formula for the sustain per second coming from potions is as follows:

Potion=(FlatRestorePot+Resourceful)/45+(BaseReco+SumFlatReco)*0.2

The calculator only uses the first term as the major intellect is factored in prior to the AddSustain section.

Resourceful is the argonian passive which gives 4620 of all resources now on CP 160 characters whenever you use a Potion. The Sustain per second for argonians is therefore

Resourceful=4620/45=103

This is a very potent passive that gives more than any recovery or cost reduction Bonus in most regular setups, as the Base Recovery needs to reach a certain level to give more than a 103 recovery. I will get to that in detail in the racial section.

5.4. Drain Magicka/Stamina Poisons


Poisons are a good sourced of additional sustain. Drain Magicka/Stamina Poisons last 5.5 seconds and restore 238 Magicka each second when they proc. They proc with a 20% chance on light and heavy attacks and weapon abilities, but NOT class abilities. The last 0.5 seconds are not counting, so effectively, the maximum uptime is 50%. The calculator assumes a 30% uptime which was the average of what I got on different setups and classes. You can modify the uptime to match yours individually.You can use any two ingredients that give restore magicka or stamina to get the full 5.5 second duration. A third ingredient will not have any effect on the poison.

5.5. Constitution Passive


This passive is from the heavy armor skill line. It was recently nerfed again to weaken Heavy Armor Sustain in PvP. It gives you 108 Magicka And Stamina per Heavy Armor Piece every 4 seconds whenever you take damage. On a 5/1/1 Setup you therefore get a 27 Stamina and Magicka per second from this if it procs on cooldown. In a dummy fight this obviously won’t help you at all. Formula is as follows:

Constitution=(108*HeavyPieces)/4

This is a major contributor to heavy armor sustain, but not enough to function as a full substitute for light and medium armor pieces, mainly due to the lacking cost reduction of skills.

Looking at an example:
3.png
Obviously, 7 light armor pieces give the best sustain, followed by 6 light and 1 heavy piece, 5 light 2 heavy and 5 light 1 medium 1 heavy. So we have a tradeoff between higher sustain with 7 light and higher damage through higher pools with 5/1/1. The other two setups are compromises in between that also work. This conclusion is exactly the same when looking at medium armor.

A 7 light/medium armor setup is more effective when you have a relatively high skill cost (AvCost) and a high flat recovery value. Here’s the difference between 7 light and 5/1/1 depending on AvCost and (BaseValueReco+SumFlatReco):



5.6. Heavy Attacks


A unique mechanic in ESO is that heavy attacks restore a flat amount of resources when successfully executed to the full duration. The six different weapons restore different amounts of resources, and while Dual Wield, Two-handed, Bow and One Handed & Shield restore stamina, destruction staffs and restoration staffs restore magicka. Here’s a table with the base resources restored of fully charged heavy attacks:
4.png
Dual Wield and One Handed & Shield take the least time to charge, while lightning staffs take the longest, since bows and inferno/ice staffs got their charge time sped up.

Since Morrowind, heavy attacks became a lot more frequent in combat, and they therefore make a good part of damage and rotations and can make the difference between a sustainable rotation and a draining one that runs out within 1 minute of fighting.

Those are the bonuses that all classes have access to, now we’re going to take a look at class-specific sustain sources in detail.

6. Sustain Options per Class


Every Class in ESO has a different way to sustain and different bonuses, favouring certain sets and skills in particular. I'm going to use examples of typical rotations on every class so we can see how high their skill cost usually is and whether there is any imbalance in sustain right now. We’re going to start with the Nightblades. At the end, I’m going to post a table with an overall comparison of passives and skills on different classes.

6.1. Nightblade


Nightblades are a high recovery class. Their skill cost is relatively cheap and with Strife and it’s morphs and surprise attack, they have good spammable skills for both stamina and magicka. They have a 15% recovery bonus on all three attributes, which makes recovery based builds more effective on them. Strife is the cheapest spammable skill in the game, enabling Magicka Nightblades to retain a good level of sustain through the morrowind changes.
6.1.1. Force Pulse vs. Funnel Health


This is going to become clear when looking at a nightblade example of Force Pulse versus Funnel Health:

5.png

This is an example nightblade rotation using force pulse as a spammable. When we now take a look at Funnel Health as a spammable:

6.png

You can see that Funnel Health is about 800 Magicka cheaper than Force Pulse. In terms of AvCost, it leads to 2567 for the Force Pulse Rotation and 2163 for the Funnel Health Rotation. That is 400+ Magicka per second we save just by using a different spammable skill.

6.1.2. Siphoning Attacks/Leeching Strikes


The second unique sustain aspect of nightblades is Siphoning Attacks/Leeching Strikes. The formula for the resource gain per second from siphoning attacks/leeching strikes is as follows:

SiphoReturn=((-InitialCost+SumFlatCost)*(1-Sum%Cost)+4290)/20+106*SkillSpeed

The initial cost and thus the net return depends on your cost reduction bonuses, so we need to include that in the equation. Initial cost for siphoning attacks is 1120, for leeching strikes it is 952. The return from light attacks depends on your weaving accuracy and can happen once per second, so we need to multiply it with sskillspeed. The return of this skill has been reduced a lot with Morrowind, so it’s interesting to see how much sustain it actually provides after the reduction. The following table shows the return of siphoning strikes on three different setups:
7.png
You see that the difference is nearly non-existent, because the initial cost is so low. This holds for stamina even more due to the lower initial cost. This is assuming a SkillSpeed variable of 1, so perfect weaving and an immediate activation after the final return. With a coefficient of 0.9, we have about 10 less net return.

6.1.3. Executioner


This passive returns 1876 Magicka over 6 seconds whenever you kill an enemy with an assassination ability. Therefore, using impale or the assassin’s will proc to kill enemies will restore 1876 Magicka over 6 seconds. This does not stack, so you can keep impaling enemies in a few seconds, but it will only refresh the 6 second duration return. So calculating the total return from this reliably is basically impossible, as it completely depends on the number of enemies killed. Also, the net return depends on the skill you used to kill the enemy. So I do not include this passive in the calculator. In solo play, this is a very important part, and it is the reason why you should use impale and the assassin’s will to kill enemies.

6.2. Templar


Templars have a 4% cost reduction on all abilities, including ultimates. They also have a relatively high skill cost in general, making them favour cost reduction more than nightblades. Here’s a typical magplar rotation and the AvCost of it.
8.png
You can see that a magplar has relatively high cost, especially when compared to a nightblade using funnel health. This gets offset a little by the cast time of 1.1 seconds from puncturing sweeps and biting jabs that slows down the weaving speed in general. Also, magplars often use dual wield and can’t restore resources on their main bar and can’t use drain magicka poisons.

6.2.1. Channeled Focus


Channeled Focus (Morph of Rune Focus) is a skill that grants you both Major Resistance Buffs and Restores 120 Magicka per 0.5 seconds for 18 seconds. To calculate the return per second we need to take into account the initial cost of 1080, which gets reduced by Cost Reduction bonuses just as siphoning attacks did:

Cfpersecond=(-1080+SumFlatCost)*(1-Sum%Cost)/26+120*2
9.png
You cane see here that as with siphoning attacks, the cost reduction barely affects the overall sustain bonus. Also, Siphoning Attacks gives about a 60-70 return per second more than channeled focus. This is again assuming a recast on expiration, so ideal conditions.

6.2.2. Repentance


This skill returns Stamina and Health for every dead body (in other terms, enemies killed) in a 28m radius. For a stamplar, this is a very strong tool to sustain, as they can recast this in trash mobs and sustain infinitely as long as you keep getting bodies to use, and a very useful tool in veteran maelstrom arena and add-heavy boss fights. With morrowind, this skill was changed to keep.the heal to allies, but the Stamina restoration is now restricted to the casting templar to make the skill not overpowered in endgame content. The negative side of it is that if you have another templar using this, may it be a healer or a stamplar, you most likely do not get any sustain in a lot of situations. The Stamina return from this skill is very hard to simulate. You can count the number of adds in a boss fight, use the usual duration of the fight and then calculate the stamina return by

Repentance1=2970*Bodies/Duration

So for example on a 240 second Rakkhat Fight with three Hulks, we get

Repentance1=2970*3/240=37,125

It also grants you minor endurance while slotted, so it is

Repentance2=2970*Bodies/Duration+(BaseReco+SumFlatReco)*0.1/2

On the same Rakkhat fight with one recovery glyph it is

Repentance2=37.13+(514+174)*0.05=37.13+34.4=71.53

This skill is largely depending on the number of adds that you have. Taking for example a Zhaj’Hassa fight with 14 Panthers and a 240 second duration, we have

Repentance2=2970*14/240+34.4=207,7

6.3. Sorcerer


Sorcerers have similar skill cost to templars, but they have a 5% cost reduction and a 10% magicka and 20% stamina recovery buff. So compared to templars, they have 1% more cost reduction and a recovery bonus that is even stronger than the 15% nightblade bonus on a stamina Sorcerer, but it is bound to the condition to have a certain skill line slotted. Let’s take a look at a classic force pulse sorcerer rotation:
10.png
The cost is comparable to a templar, but a sorcerer does not have a sustain skill without a cast time. Dark Deal/Conversion has a 1.2 second cast time and therefore takes out a good time of your rotation and a skill slot to use frequently within a fight. But Sorcerers have access to a third bar, through overload. So they can use more skills than other classes between fights and rounds.

6.3.1. Dark Deal/Dark Conversion


This skill exchanges either magicka for stamina on a stamina sorcerer (Dark Deal) or stamina for magicka on a magicka sorcerer (Dark Conversion). It gives 4696 magicka/stamina on cast, so to simulate it, we have

Dark1=4696*CastPerRotation/Duration

So if we cast it once every 20 seconds and our rotation is 10 seconds long, we get

Dark1=4696*0.5/10=234.8

As Dark deal doesn’t deal damage and sorcerers synergise greatly with heavy destruction staff attacks, we will take another look at them in the heavy attack section.

6.4. Dragonknight


Dragonknights have a lower skill cost than sorcerers, wardens and templars, higher skill costs than nightblades with funnel health and lower skill costs than nightblades with force pulse. They have more strong damage over time skills than all other classes, but they are cheaper than the other classes' DoTs.

The difference between then and other classes is that they do not have a recovery bonus or a cost reduction bonus, but they have different ways to sustain.
11.png

6.4.1. Battle Roar


Battle Roar is a passive that returns all three resources whenever you cast an ultimate, 46 per point of cost of the ultimate. So their sustain depends to a certain level on their ultimate generation. Their ultimate generation mostly ranks between 3 and 4 (depending on synergies used), so assuming an ultimate generation of 4, we get a resource gain per second of

Battle Roar=(46*CostofUltimate)/(CostofUltimate/UltiGen)

So using Standard of Might we have

BattleRoar=(46*250)/(250/4)

Simplified we get

BattleRoar=46*4=184

So BattleRoar=46*UltiGen

So the return from Battle Roar is always 46*UltiGen per second per resource when you cast the ultimate as soon as it’s ready. In many fights, timing ultimates right is an important aspect and you will not cast them when ready, so this will mostly be less than that.

The span of Battle Roar is usually between 128 and 184, depending on your ultimate generation.

6.4.2. Flame Lash


Flame Lash is a skill that turns into Power Lash, a much stronger version of whip against off-balance enemies and that is free to cast. Most trial groups are set up to have as much off-balance uptime through lightning damage and blockade of storms as possible. Let’s see how much cost we can spare when assuming a 100% off-balance uptime:

12.png

As Molten Whip was responsible for half our skill cost, using Flame Lash halves AvCost. So if you have a coordinated group providing you with off-balance, you can use flame lash to sustain. You can also use a lightning staff and a charged staff with a shock enchantment. I can sustain a regular target dummy without elemental drain by myself using that.


6.5. Warden


Wardens were introduced with the Morrowind expansion, and they have two sustain passives: one for 12% stamina and Magicka recovery when ab Animal Companion agility is slotted, and one that restores 250 Magicka or stamina whenever you heal an ally with a Green Balance Ability. The first one is comparably weak, as it is only 12% that also comes with a condition that forces you to have two abilities slotted to get the full benefit. The second one is very hard to predict, as it requires you to have a target to heal. Also depending on the skill used and the amount of healing ticks per second you dish out, the passive will become more effective. On top of those, wardens have the Betty Netch that gives a major spell or weapon damage buff and grants a flat amount of resources over 25 seconds. Let’s take a look at a typical Warden rotation:
13.png
You could squeeze out a little less cost of skill when you used one more cliffracer and ditched one scorch, but you will most likely want to use scorch at least twice as it has a higher tooltip in single target and is an AoE ability. The skill cost is higher on a Warden than on Dragonknights and Magicka Nightblades, but lower than on Sorcerers and templars. It is exactly in between those.

6.5.1. Betty Netch (Blue Betty/Bull Netch)


This skill returns 4099 Magicka or Stamina over 25 seconds and has 0 cost. So the per second calculation is fairly easy here:

Betty=4099/25=163,96

This is less than channeled focus and siphoning attacks, but it is unconditional as the netch can not die, follows you and can not be interrupted.

6.5.2. Nature’s Gift


This passive returns 250 Stamina or Magicka to the Warden whenever you heal yourself or an ally with a green balance ability. In a trial, this will help you a lot. Thus is not implemented in the calculator, as it requires to much input and is largely depending on the group and how many allies you heal with how many skills ticking per second. So if we wanted to predict the return of this passive, we’d have

NatureGift=250*(LivingTrellisTick*LTActive+Lotusblossom*SkillSpeed+SoothingSporesCastpersecond*SStargetshit+NatureEmbrace)

We’d also need to insert another IF-Conditional function to check whether the stamina or magicka is higher. So it’s very hard to predict. In trials, this is a very potent sustain tool (especially in combination with the warden’s healing ultimate), and in solo, it gives you back a good portion of skill cost when you keep taking damage.

6.6. Summary Tables of Classes


This section is aimed at providing a summary of the before mentioned findings as well as additional data examples.

14.png

The following table presents a detailed class comparison as it would occur on the calculator. I used dunmer to rule out dilution from racial passives which will be regarded in the next section. I activated all buffs and one recovery glyph to reach positive numbers on the NetResourceLevel numbers. The rotations used are the ones from the examples in the prior class paragraphs as they represent typical light attack rotations that would be used on the respective class.

15.png

Starting above with the average Base cost, we can see the average Base cost from highest to lowest, in descending order: Sorcerer, Templar (very close to each other), Warden, Dragonknight, Nightblade. To that Average Base cost, skill speed is applied to simulate the usual delay on global 1 second cooldowns. The flat and percentage cost reduction ate then reducing that value to determine the actual resource drain per second. This is the value you need to counter with recovery and flat resource return in order to have a fully sustainable rotation and build.

16.png

So when applying the respective cost reduction bonuses on top of the basic 18% (14% Light Armor + 4% Worm Cult), the overall drain per second is similarly high on wardens, templars and sorcerers, followed by dragonknights and nightblades as the lowest.

When looking at the resource gain from the recovery class passives and comparing them to the impact on cost reduction passives, it is visible that in a regular PvE build, recovery covers a similar part of sustain as cost reduction does, but buffs are affecting it a lot less, so in order to effectively maximise the recovery return, you need to stack a lot of buffs. This is due to the Base value being very low, and to achieve a higher Base value, you need to sacrifice a lot of damage. The maximum difference of sustain per second in the above table is observed between a nightblade and a templar/dragonknight with a value of 52. Of course this is based on a flat recovery value of 688. With more, the difference is going to increase. But even with 3 recovery glyphs we have a flat value of 1036=514+174*3, so the difference in sustain per second from recovery is 78 between a nightblade and a templar.

This leads us to a source of imbalance between wardens the classes: their skills are relatively expensive, but they do not have a cost reduction passive and the Betty Netch does not restore as much resources as channeled focus and siphoning attacks.

But overall, all classes seem to be in pretty balanced sustain field. Only Nightblades stand out due to the cheap Funnel Health.


7. Comparison of Racials and their Impact on Sustain


Another source of additional sustain (and damage) are racials. So you will have different sustain depending which rate you choose. But how much of an impact on sustain do racials actually have?

I’ll try to determine that in the following section by going through races that affect sustain and doing a comparison afterwards.

We basically have five categories of races giving sustain: Redguard, Argonian, Breton, Recovery Races and Races without a Bonus. Until the examples, I’m going to treat races in those categories and test the recovery Races individually afterwards.

7.1. Redguard


Redguards have strong passives for Stamina, with a 9% recovery, 10% additional Stamina and a flat Stamina restoration on inflicted melee damage. The 9% recovery is implemented in the Sum%Reco variable to additively increase your recovery. The flat restoration's maximum return can be calculated as

Redguard=792/5=158,4

This is just as strong as the warden’s Bull Netch, so this gives you quite a lot of Stamina sustain for free.

Useful for: Stamina Damage Dealers, Tanks

7.2. Argonian


Argonians have the resourceful passive, which grants you 4620 Stamina every 45 seconds when you drink a potion and 3% more maximum Magicka. So in order to assess the return, we can simply divide

Resourceful=4620/45=102.67

This is weaker than the redguard passive, but it affects all three resources.

Useful for: All Roles.
7.3. Breton


Bretons are the only race that gets a cost reduction, 3%. The Breton Passive only applies to Magicka Skills, so it doesn’t do anything for Stamina Specced Characters.

The effectiveness of the Breton Passive can be calculated as follows:

Breton=(AvCost-SumFlatCost)*0.03

Useful for: Healers, Tanks, Damage Dealers

7.4. Recovery Races


Recovery races are basically all that have a passive that boost recovery, namely Altmer (9% Magicka), Bosmer (21% Stamina), Khajiit (10% Stamina), and Redguard (9%). Redguard is a special example as it also has a flat restoration bonus.

Their effectiveness can be calculated by

RecoRace=(514+SumFlatReco)*RacialReco

With RacialReco being 0.09, 0.21, 0.10 and 0.09 for Altmer, Bosmer, Khajiit and Redguard, respectively.

Useful for: Damage Dealers, Healers

Now that we covered the Basic Sustain Passives from Races, I’m going to show tables of each racial sustain category so you see how much of a Difference it will make in practice.
17.png



7.5. Magicka Racial Sustain Comparison


18.png
When comparing the different racial categories, we see that Argonian gives the overall best sustain under the above conditions. The effectiveness of Breton is based on your drain, so as long as you have a certain drain level, you will get the most out of Breton and iif not, Argonian has the highest sustain. It is interesting to see where the break-even points between Argonians, Bretons and Altmers are.

To calculate the break-even point between Argonians and Bretons, we need to use the following formula, with X being your AvCost:

X*0.9*(1-0.21)=X*0.9*(1-0.18)+103 <=> X*0.79=X*0.82+103/0.9 <=> X*-0.03=114.4 <=> X=-3800

So you’d need a resource drain of 3800 (assuming SkillSpeed=0.9) to reach the same result on a Breton as on an Argonian. This is fairly unrealistic, so Argonian will most likely be the best race for sustain.

To calculate the break-even point between Argonians and Altmer, we need to use the following formula, with Y being your recovery:

103=X*0.09/2 <=> X=2289

So in order to make Altmer better than Argonian, you need a (BaseReco+SumFlatReco) of 2289 to equal the net return on sustain from Argonian on a per second basis.

There is no definite calculation method to determine the break-even point between Altmer and Breton, as both variables depend on different values that do not directly influence each other, AvCost and Skill Speed for Breton and (BaseReco+SumFlatReco) for Altmer. I will set Skillspeed to 0.85 for this example. The following graph shows the AvCost, and then the Recovery that is needed to break even with Breton as an Altmer Character.
19.png

7.6. Stamina Racial Sustain Comparison


To be included.



Feel free to post any constructive Feedback and help out if you discover errors or oversights. This is a work-in-progress thread and I will constantly update it.

To-do-List:

Include Food Buffs (even though they are easy to assess as they simpy, add in flat recovery)

Add the Net Imapct of Race and Class in the Calculator.

You can find the current version of the calculator free to download here:

https://forums.elderscrollsonline.com/en/discussion/351669/in-depth-resource-management-analysis-calculator-for-elder-scrolls-online-mw