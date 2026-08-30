 The game does

(Base scaling) x (%damage done) x (% damage take) x (crit modifier.)

Each of the "buckets" are multiplicative with each other. The factors within them are additive though.

So if your only two buffs/debuffs were major slayer and major berserk it would be

1x (1+(.1+.1)) or 1x1.2

because they are both %damage done

If your buffs/debuffs were major slayer and major vulnerability it would be

1 x 1.1 x 1.1 or 1.21

because slayer %damage done and vulnerability is% damage taken which are calculated separately

For two buffs it's not a huge difference, it's .21 vs .2. With more buffs/debuffs the difference between addadive and multiplicative becomes higher.

Crit is handled differently. you can calculate your average crit modifier as

(Crit chance * (1+crit damage) + (1-crit chance))

So 60% crit chance and 125% crit damage (the cap)

Is (.6*2.25+.4) =1.75

So on average crits will contribute 75% extra damage. It's Rng based though. At 60% crit chance some fights you'll have 70% crits and some fights 50%.

Over the long run, where law of large numbers kicks in, it averages to 60%.

Also there are a few sets that dont crit. Including some meta ones (rele, azureblight. I heard Pyrebrand is wonky) 

------------------

 There's also the scaling in general.

Skills typically scale off of the higher of WSD and ~(max stat÷10.5),

If they scale on something else like HP, resistances, max mag, it'll be listed in the tooltip

Proc sets scale off of WSD only (unless otherwise stated)

So at 6k weapon damage and 30k Stam your skills are scaling off of ~8857 and your procs 6k.

To make things even more fun you have the bloodthirsty jewelry trait which provides 0 at 100% health, then begins to scale linearly at 90%. At 0% it's another 1050 WSD.

On average bloodthirsty is 520WSD

There's also wrathful strikes which is 205 to offensive skills

So when your evaluating adding WSD youll do a % change formula using (8857+520+205) for skills and (6000+520+205) for procs.

There's two more factors that complicate this

A). Buffs that boost %WSD B). Some WSD buffs aren't boosted by A)

So for A), fighter guild abilities, medium armor, and some class passives and major/minor brutality/sorcery boost WSD by a percentage.

This is why barbed trap and dawnbreaker are on everyone's front bar and why trial/parse builds are in medium. So when you get a WSD buff (like powerful assault) it will be multiplied by the %WSD buff. Most classes get somewhere between x1.4-1.6 for their modifier in an optimized group.

With B) not every set seems to benefit. Conditional sets like Drozakar and Silks of the sun don't seem to get the buffs. Probably because it's targeting someone else instead of you.

To bring everything together-

The set Coral Riptide gives you 740 WSD. Let's say your modifier is x1.5.

740x1.5=1110.

So % change is

(New value-orignal value)÷ original value

If you have 6k WSD and 30k stam without riptide NV-OV will be riptides value

Riptides effect on skills is 1110÷ (8857+520+205)

+11.5%

For procs it's 1110÷(6000+520+205) = 16.5%

To determine if you want to use a set with WSD, crit or % damage done you need to predict which buffs/debuffs your expecting to see, then you can do % change formulas for each and see whichever is highest.

A good rule of thumb is if your already high in one stat, but low in another, you'll get more milage out of raising the low stat. 