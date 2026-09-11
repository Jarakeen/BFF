# ESO Mechanics Field Notes

Plain-English notes on odd, useful, counterintuitive, or mathematically interesting Elder Scrolls Online mechanics discovered while building and validating BFF / FoundryDock.

## Standing rule

Whenever development, testing, real-build validation, encounter research, or data reconciliation reveals something mechanically odd or noteworthy, add a short layman's note here.

Prefer notes that answer:

- **What did we notice?**
- **Why is it surprising?**
- **What does it mean in actual play?**
- **What does it mean for BFF?**

Keep equations secondary. The point of this file is to preserve the useful idea even if nobody wants to reread the implementation archaeology later.

---

## 2026-09-06 — Healer sustain and heavy attacks are path-dependent

### A higher recovery threshold does not necessarily leave you with more Magicka

During a 60-second real-build audit of **Magrat / DF Healer**, we tested several deliberately noncanonical recovery-heavy trigger thresholds using the same caller-supplied 4200 Magicka test restore.

| Recovery trigger | Stable heavy schedule | Ending Magicka |
| --- | --- | ---: |
| 35% | none | 21,853 |
| 50% | none | 21,853 |
| 65% | 57s back bar | 26,053 |
| 75% | 18s and 57s back bar | 29,977 |
| 80% | 18s and 33s back bar | 29,178 |

The interesting part is that **75% ended with 799 more Magicka than 80%**, even though both schedules contained two recovery heavies of the same test amount.

**Layman's version:** when you heavy matters, not just how many times you heavy. An earlier heavy changes which skills get pushed later, when those skills spend Magicka, and when passive recovery ticks happen. Two rotations can restore the same total amount and still end in different places.

**For BFF:** sustain cannot be optimized by simply adding up total costs and total restores. The exact event order matters.

---

## 2026-09-06 — Falling below a threshold does not automatically mean "heavy now"

In the same DF Healer audit, Magrat's lowest Magicka point was **14,361 / 31,109**, or about **46.2%**, at roughly 40 seconds.

That means she clearly fell below a 50% recovery threshold. Yet the stable 50% schedule contained **no heavy attacks**.

This was not a bug.

By the time a legal front-bar Restoration Staff heavy window appeared at 52 seconds, Magicka had already recovered to **15,831 / 31,109**, or about **50.9%**. The moment of low resource and the moment of legal heavy opportunity did not line up.

**Layman's version:** being low on Magicka is only one condition. You also need to be on the right bar, have enough uninterrupted time to channel the heavy, and not be about to miss a more important refresh.

**For BFF:** recovery-heavy scheduling is a constrained timing problem, not a simple "if Magicka < X, heavy attack" rule.

---

## 2026-09-06 — Ending Magicka can hide a dangerous mid-rotation dip

Without recovery heavies, DF Healer ended the 60-second audit at **21,853 Magicka**, which looks comfortable.

But the same timeline dropped as low as **14,361 Magicka** around 40 seconds before recovering again.

That is a rebound of **7,492 Magicka** between the minimum point and the end of the sample.

**Layman's version:** a rotation can finish looking healthy even though it had a much shakier moment in the middle. Looking only at the final blue-bar number can hide the part where you were actually at risk of being unable to cast what you needed.

**For BFF:** minimum resource over time matters at least as much as ending resource. Later reserve logic should care about whether enough resource exists at the moment an important heal or mechanic response is needed.

---

## 2026-09-06 — Locally sensible heavy attacks can become unnecessary after replay

At an aggressive 80% recovery threshold, a raw decision trace found four legal recovery-heavy opportunities for DF Healer:

- 18s back bar
- 21s back bar
- 33s back bar
- 57s back bar

After BFF replayed the resource gained from those heavies and regenerated the rotation, the stable schedule settled on only:

- 18s back bar
- 33s back bar

**Layman's version:** the first heavy can solve some of the resource problem that made a later heavy look necessary. If you judge every opportunity independently, you can easily prescribe too many heavies.

**For BFF:** recovery decisions need iterative replay. A heavy should not stay in the schedule merely because it looked useful before earlier recovery actions changed the future resource curve.

---

## 2026-09-06 — Two bars can restore the same resource but offer very different heavy opportunities

BFF's heavy-restoration model correctly recognizes that fully charged Fire, Frost, Shock, and Restoration Staff heavies restore **Magicka**.

During the DF Healer trace, however, legal opportunities were very different between the bars.

Examples from the 80% diagnostic trace:

- **16s front bar:** Magicka pressure existed, but only a 1.0-second safe window was available. A 1.8-second heavy could not fit.
- **18s back bar:** Magicka pressure existed and a 2.0-second safe window was available. The Frost Staff heavy was legal.
- **52s front bar:** pressure existed again, but the safe window was only 1.0 second.
- **57s back bar:** pressure existed and another 2.0-second legal window was available.

**Layman's version:** two weapons can recover the same blue resource, but the rotation around them can make one bar much better for fitting a heavy attack.

**For BFF:** bar layout itself can affect sustain quality. In the future, optimizing where long-duration skills live may create better heavy-attack windows without changing the character's total stats at all.

---

## 2026-09-06 — Cycle of Life is a bonus, not the reason staff heavies restore Magicka

A real-build trace exposed a modeling mistake in BFF's discovery layer.

The underlying heavy-restoration model already knew that all recognized staff heavies restore Magicka. But healer heavy-attack discovery only created a recovery incentive when a Restoration Staff had **Cycle of Life**.

That meant DF Healer's Frost Staff back bar had legal 2.0-second Magicka-recovery windows that the scheduler refused to use because it thought there was "no matching recovery incentive."

The discovery logic was corrected so that:

- any recognized staff can provide base Magicka-recovery heavy value;
- Restoration Staff can additionally provide Cycle of Life evidence.

**Layman's version:** Cycle of Life improves Restoration Staff heavy recovery. It is not what gives staff heavies resource recovery in the first place.

**For BFF:** base weapon behavior and passive bonuses need to remain separate concepts. Otherwise a passive can accidentally become a permission gate for a mechanic that exists without it.

---

## 2026-09-06 — The best healer rotation probably should not maximize ending Magicka

The threshold sweep hints at a larger optimization issue.

A healer rotation that ends with the fullest Magicka bar is not automatically the best rotation. Conserving resources by skipping useful heals, buffs, or support actions would technically score well on ending Magicka while being terrible gameplay.

A more realistic objective eventually needs to balance things such as:

- required buff and debuff uptime;
- healing coverage;
- mechanic-response reserve;
- resource risk;
- heavy-attack opportunity cost;
- required set effects such as Roaring Opportunist;
- encounter safety.

**Layman's version:** "finish with the most Magicka" is the wrong goal. The goal is closer to "do everything important, stay safe, and do not run out when it matters."

**For BFF:** whole-schedule quality should eventually be scored under constraints rather than optimized around one final resource number.

---

## 2026-09-06 — Recovery-heavy scheduling behaves like a small feedback system

The recovery stabilizer now follows a loop:

1. Generate a rotation.
2. See where resource pressure occurs.
3. Add legal heavies.
4. Replay the Magicka restored by those heavies.
5. Generate the rotation again.
6. Repeat until the heavy schedule stops changing or the safety limit is reached.

**Layman's version:** BFF asks, "If I actually follow my own advice, does that advice still make sense afterward?"

That is why an initial list of four possible recovery heavies can shrink to two once the first two have already fixed the later problem.

**For BFF:** this fixed-point style of reasoning may turn out to be useful beyond sustain, especially anywhere one rotation choice changes the conditions that produced later choices.

---

## 2026-09-07 — Health-triggered mechanics do not live at one fixed clock time

Encounter research stores some mechanics as boss-health thresholds, such as a phase change at **70% health**, while other mechanics may eventually have explicit seconds from pull.

Those are not interchangeable kinds of timing.

A mechanic at 70% happens earlier for a high-damage group and later for a lower-damage group. There is no honest conversion from "70%" to "24 seconds" unless we also model how quickly that specific group is damaging the boss.

**Layman's version:** "this happens at 70%" tells you where the boss is in the fight, not what the stopwatch says. Faster groups reach that mechanic sooner.

**For BFF:** encounter timing needs two lanes. Explicit clock events can feed rotation scheduling directly. Health-triggered events need a fight-duration or damage-trajectory projection before BFF can place them on the same seconds-based rotation timeline.

---

## 2026-09-07 — Some mechanic timing belongs to the group, not just the boss

Using Xalvakka hardmode's persisted health of **214,233,024**, we projected the reviewed **70%** and **40%** thresholds under two different caller-supplied raid DPS assumptions.

| Raid DPS | 70% threshold | 40% threshold |
| ---: | ---: | ---: |
| 1,500,000 | 42.85s | 85.69s |
| 2,000,000 | 32.13s | 64.27s |

Increasing raid DPS from 1.5 million to 2.0 million is a **33.3% increase in damage rate**, but the practical effect is that the same boss mechanics arrive about **10.72 seconds earlier at 70%** and **21.42 seconds earlier at 40%**.

The later threshold moves more in absolute seconds because the faster group has been gaining time for longer before reaching it.

**Layman's version:** some boss mechanics do not have a universal timestamp. The group partly creates the timing by how fast it burns the boss. Two teams fighting the same boss can experience the same health-based mechanic at very different moments on the clock.

**What it means in actual play:** a rotation, cooldown plan, or healer-prep callout learned from one group can be mistimed in another group even when both are mechanically correct. Faster groups can push a health-triggered mechanic into a completely different part of a buff, Ultimate, potion, or sustain cycle.

**For BFF:** health-triggered encounter planning should use the selected team's projected or observed damage trajectory. A fixed global timestamp would be wrong by construction. This also means team composition and rotation planning are mathematically coupled: changing raid damage can move encounter mechanics, and moved mechanics can in turn change the best rotation.

---

## 2026-09-07 — Preparing a heal earlier can improve sustain, not just readiness

In the Xalvakka hardmode audit, the reviewed **70%** Phase 2 threshold projected to about **42.85 seconds** under a caller-supplied 1.5 million raid-DPS assumption. BFF opened an audit-only healer-preparation window from about **39.85s to 44.85s**.

With ordinary scheduling, **Combat Prayer** was cast at 40s and **Budding Seeds** did not return until 48s. When the encounter-aware rotation was explicitly allowed to refresh Budding Seeds up to three seconds early for that Phase 2 preparation window, Budding Seeds moved to **40s** instead.

The surprising part was the resource result:

| Metric | Base rotation | Xalvakka-aware rotation | Change |
| --- | ---: | ---: | |
| Minimum Magicka | 14,361 | 16,132 | +1,771 |
| Ending Magicka | 21,853 | 23,624 | +1,771 |
| Total shortfall | 0 | 0 | 0 |

WAIT count, refresh-claim count, and horizon displacement were unchanged.

**Layman's version:** casting the mechanic-prep heal earlier did not merely make the healer more prepared. Because that cast changed what happened later in the rotation, it also left Magrat with more Magicka overall. The same skill can therefore have a different sustain consequence depending on *where in the event sequence* it lands.

**What it means in actual play:** an intentional early refresh before a dangerous mechanic is not automatically a sustain penalty. In some rotation paths it can actually be resource-positive compared with letting the ordinary schedule play out, because the early cast displaces or removes a later cost at a more awkward point in the cycle.

**For BFF:** encounter preparation and sustain cannot be optimized independently. The planner needs to evaluate the resulting whole schedule after moving a prep cast, not assign a fixed "early refresh costs extra" penalty. This is another concrete example of ESO rotation sustain being path-dependent rather than a simple sum of casts.

---

## 2026-09-07 — More raid DPS can move a mechanic out of a useful prep opportunity

We ran the same Xalvakka hardmode Phase 2 healer-prep policy at two different raid-DPS assumptions.

At **1.5 million raid DPS**, the 70% threshold projected to about **42.85s**, putting the prep window around **39.85s–44.85s**. That lined up with Magrat's front-bar rotation, so BFF could intentionally pull **Budding Seeds** forward to 40s.

At **2.0 million raid DPS**, the exact same 70% threshold projected much earlier, around **32.13s**, moving the prep window to roughly **29.13s–34.13s**. That entire useful portion of the window landed while Magrat was on her back bar. Budding Seeds therefore stayed at its ordinary 36s cast and the encounter-aware schedule was identical to the base schedule.

**Layman's version:** making the group faster did not gradually make the same healer prep happen earlier. It moved the mechanic far enough that the prep opportunity vanished entirely because the healer was on the wrong bar at that moment.

**What it means in actual play:** health-triggered mechanics can cross invisible rotation boundaries as group damage changes. A small enough DPS change may only shift a callout by a second or two, but a larger change can move the mechanic across a bar swap, cooldown seam, heavy-attack window, Ultimate window, or resource dip. The practical effect can jump suddenly rather than changing smoothly.

**For BFF:** mechanic-response quality is not a smooth function of raid DPS. The planner should expect discrete opportunity bands where a given prep action is legal, followed by bands where it is not. Optimizing team damage may therefore change the best healer rotation in step-like jumps, not by simply sliding every action earlier on the clock.

---

## 2026-09-07 — Healer opportunity bands can be helpful, neutral, or actively harmful

A broader Xalvakka hardmode sweep projected the same reviewed **70%** threshold across raid-DPS assumptions from **1.2 million to 2.4 million**, using the same audit-only healer policy: begin preparation three seconds early and allow Budding Seeds up to three seconds of demand-specific early refresh.

The result did not form one simple "faster is better" or "faster is worse" curve. It formed distinct scheduling bands:

| Raid-DPS band | Observed effect |
| --- | --- |
| 1.2m–1.3m | Rotation changed, but minimum and ending Magicka got worse |
| 1.4m | No schedule effect |
| 1.5m–1.7m | Rotation changed and minimum/ending Magicka improved by 1,771 |
| 1.8m–2.0m | No schedule effect |
| 2.1m–2.4m | Rotation changed and minimum/ending Magicka improved by 1,771 |

At **1.2m DPS**, for example, the mechanic-aware plan moved Budding Seeds from 48s to 51s, reduced one WAIT, yet still lowered minimum Magicka by **523** and ending Magicka by **2,878**. By **1.5m DPS**, the same policy moved Budding Seeds from 48s to 40s and improved both minimum and ending Magicka by **1,771**. At **1.8m–2.0m**, the moving mechanic crossed into a part of the rotation where the policy could no longer alter the schedule at all.

**Layman's version:** the same healer prep rule can be good, useless, or bad depending only on when the boss reaches the health threshold. The rule itself did not change. The build did not change. The mechanic did not change. Only the group's damage rate moved that mechanic into a different part of the healer's rotation.

**What it means in actual play:** two groups with nearly identical strategies can get different value from the same pre-buff or pre-heal habit. A mechanic that lands near a convenient front-bar refresh seam may make early preparation cheap or even sustain-positive. Move the same mechanic a few seconds and the preparation can instead delay a skill, change later costs, or push the rotation into a worse resource path.

**For BFF:** encounter-aware optimization needs to evaluate complete schedules across projected mechanic times, not attach one fixed value to a policy such as "refresh Budding Seeds before Phase 2." The useful object is an **opportunity band**: a range of fight trajectories where a policy has the same practical result. Team optimization should eventually know when increasing or decreasing raid damage crosses one of these discontinuous scheduling boundaries.

---

## 2026-09-07 — A complete character can have 64 attribute points that do not change the stat being maximized

While building the from-scratch Extreme Build Lab, a Spell Damage blueprint initially left all attribute points at zero because level-up Magicka points do not directly increase the literal **Spell Damage** character-sheet stat in BFF's static formula.

That is mathematically defensible and still a terrible character blueprint.

**Layman's version:** Max Magicka and Spell Damage are both offensive stats, but they are not the same number. Adding Magicka can make Magicka-scaled abilities stronger without making the Spell Damage line on the character sheet go up.

**What it means in actual play:** a build can be better at dealing damage even when the displayed Spell Damage stat does not move. Conversely, a stunt build whose only goal is the biggest possible Spell Damage number can make choices that are worse for real damage.

**For BFF:** from-scratch builds now allocate all 64 attribute points even when the requested sheet stat does not benefit directly. The tool must distinguish "maximize this literal stat" from future whole-damage optimization.

---

## 2026-09-07 — Both skill bars belong to the build, but only the active bar gets active-bar-only standing bonuses

The Extreme Build Lab now displays both skill bars, but its character-sheet snapshot still has one explicitly selected active bar.

**Layman's version:** putting a useful passive-granting skill on the back bar does not mean its bar-only bonus also exists while you are standing on the front bar. You own both bars; you only have one of them active at a time.

**What it means in actual play:** swapping bars can change a character-sheet stat even though no gear was changed. A deliberately absurd max-stat build may therefore have a "show-off bar" whose only job is to make one number larger.

**For BFF:** both bars should be presented in a generated build, while active-bar-only skill and weapon effects must be evaluated against the selected bar instead of being added together.

---

## 2026-09-07 — "Resting maximum" and "potion-active maximum" are different honest answers

The first Extreme Build Lab boundary excluded potion uptime entirely. That made the resting number clean, but it also hid a perfectly legitimate self-usable way to push a stat higher.

**Layman's version:** the number you have while standing around and the number you have immediately after drinking the right potion are both real character-sheet values. They are just different states.

**What it means in actual play:** Spell Power, Critical, recovery, and resistance potions can legitimately raise different requested stats without borrowing anything from another player. A Restore Health potion, however, improves Health Recovery rather than Max Health, so it does not magically win a "maximum Max Health" contest just because the word Health appears on the bottle.

**For BFF:** the scratch optimizer now keeps the resting/self-contained result and a separate objective-specific potion-active result. It must never quietly fold temporary potion state into the resting number.

---

## 2026-09-07 — Mechanic-entry Magicka is not monotonic with raid DPS

In the Xalvakka healer reserve sweep, Magrat entered the same projected Phase 2 preparation window with different Magicka depending on raid DPS:

| Raid DPS | Magicka immediately before prep window |
| ---: | ---: |
| 1,300,000 | 21,836 |
| 1,500,000 | 18,125 |
| 2,000,000 | 20,295 |

The middle damage rate produced the lowest entry reserve of the three. Faster raid damage did not simply mean more or less Magicka at the mechanic.

**Layman's version:** the boss reaching the mechanic sooner can land you in a completely different part of your cast-and-recovery cycle. A faster group can therefore hit the mechanic with either more or less Magicka depending on where that threshold intersects the rotation.

**What it means in actual play:** increasing group damage does not guarantee that a healer reaches health-triggered mechanics with a safer resource bar. A particular DPS level can accidentally line the mechanic up with a resource dip.

**For BFF:** mechanic-entry reserve must be evaluated on the projected resource timeline for that team's fight trajectory. It cannot be estimated from raid DPS with a simple increasing or decreasing formula.

---

## 2026-09-07 — A cast moved inside the mechanic window cannot repair a reserve deficit that already existed before the window

In the same Xalvakka reserve work, baseline and encounter-aware rotations had identical Magicka immediately before the prep window even when the encounter-aware plan changed casts inside the window and improved later sustain.

**Layman's version:** once you arrive at the mechanic under-resourced, a clever cast change that happens after the mechanic starts cannot travel backward in time and give you the Magicka you needed beforehand.

**What it means in actual play:** preparation has two separate questions: "Did I enter the mechanic with enough resource?" and "Did I spend that resource well once the mechanic began?" A rotation can improve the second without fixing the first.

**For BFF:** demand-entry reserve must be checked before demand-window actions are applied. Later schedule improvements can improve the aftermath, but they must never be allowed to retroactively satisfy a pre-mechanic reserve requirement.

---

## 2026-09-07 — Preserving the number of casts does not preserve uptime

In the 60-second Xalvakka healer bar-access audit, the diagnostic rescue kept all five casts of **Winter's Revenge**. Even so, its active coverage changed from **51 seconds (85.00%)** to **50 seconds (83.33%)**. The repaired schedule added one second of total gap and one second of premature overlap.

**Layman's version:** "I cast it five times either way" does not mean the skill covered the fight equally well. Moving one cast can leave a hole before it and waste duration by overlapping the previous cast.

**What it means in actual play:** protecting the cast count is not enough when a mechanic forces a bar swap or rearranges support skills. The same five casts can provide less useful coverage if their spacing gets worse.

**For BFF:** schedule repair must measure the actual active timeline. Required support uptime must be checked as an explicit hard obligation before a rotation can win on better Magicka or another softer benefit.

---

## 2026-09-08 — A class-line slot passive can boost heals from a completely different skill line

While extending MOST Actual Heal, BFF reviewed Nightblade **Soul Siphoner** separately from Warden **Emerald Moss**. Both care about what is slotted on the active bar, but they do not boost the same thing.

At reviewed max rank, Soul Siphoner increases **generic Healing Done by 3% for each Siphoning ability slotted**. That means adding Siphoning carrier skills can increase the size of a Restoration Staff heal such as Combat Prayer even though Combat Prayer itself is not a Siphoning ability. Emerald Moss is narrower: Green Balance slots only increase healing from Green Balance abilities.

**Layman's version:** sometimes a skill on your bar is helping another heal simply by being there. It does not have to be the heal you are casting, and it does not even have to come from the same skill line as that heal.

**What it means in actual play:** two bars with identical gear and the same heal can produce different heal numbers because one bar has more Siphoning abilities slotted. A healer can therefore trade utility slots for raw heal size without changing weapons or armor.

**For BFF:** slot-count passives need their exact scope preserved. Soul Siphoner belongs in a generic active-bar Healing Done layer, while Emerald Moss remains an ability-family modifier. Treating both as the same kind of bonus would either undercount Soul Siphoner or incorrectly let Emerald Moss buff unrelated heals.

---

## 2026-09-08 — Two low-health healing passives can care about completely different things

MOST Emergency Heal now models Templar **Mending** separately from Restoration Staff **Restoration Expert**. Both become relevant when an ally is badly hurt, but their permission rules are different.

At reviewed max rank, Mending scales Restoring Light healing continuously with the target's missing health, up to a 12% bonus at the theoretical zero-health endpoint. Restoration Expert instead gives a fixed 15% bonus only when the target is at or below 30% health, and only to Restoration Staff heals while the correct weapon/passive conditions are satisfied.

**Layman's version:** "the target is almost dead" is not one universal healer bonus. Breath of Life and Combat Prayer can react differently to the exact same injured target because different passives own their bonuses.

**What it means in actual play:** changing the heal you press can change which emergency passive helps you even if your gear, target, and target health are identical. A subclass route carrying Restoring Light and Restoration Staff may have access to both mechanics, but each heal still has to qualify for its own one.

**For BFF:** target health is an input, not a shortcut. Emergency-heal scoring must resolve the ability family, weapon/passive legality, and the exact health rule separately rather than collapsing everything into one generic low-health multiplier.

---

## 2026-09-08 — "Current tooltip" can accidentally mean next patch

While reviewing Templar **Mending**, a current third-party skill page showed a 13% max-rank value even though BFF's live U50 evidence and current canonical implementation use 12%. Update 51 is still a separate version boundary, so copying the newest visible number without proving which game update it belongs to would silently mix PTS/future mechanics into live math.

**Layman's version:** a website can be up to date and still be too up to date for the version of ESO you are actually playing.

**What it means in actual play:** a build calculator can disagree with the live game even when both numbers came from reputable-looking current sources, simply because one source has already moved to the next patch's data.

**For BFF:** every mechanic whose value can change across updates needs version-aware evidence. U50 remains U50 until the live version changes; future/PTS values must not overwrite historical or live definitions just because they are newer.

---

## 2026-09-08 — A damage-stat buff can improve healing without being a healing buff

While validating Templar **Illuminate**, BFF confirmed that the passive's reviewed U50 effect belongs in the ordinary named-buff stat path: after a qualifying Dawn's Wrath cast, Illuminate supplies **Minor Sorcery**, which raises Spell Damage by 10%. It does not grant Healing Done.

The mechanically odd part is that this can still make a heal larger. Heal coefficients consume the resolved offensive power state, so increasing Spell Damage before coefficient evaluation may raise the resulting heal even though no healing-specific modifier changed.

**Layman's version:** a buff can make your heal bigger without ever saying "healing" anywhere on it. It improves one of the numbers the heal formula reads first.

**What it means in actual play:** Minor Sorcery is not equivalent to "10% stronger heals." If Spell Damage is not the power value actually controlling the resolved heal, the benefit can be smaller or absent. Illuminate rank I and II also change the buff duration rather than the Minor Sorcery magnitude, so a learned rank-I window is real math rather than an unknown partial-value case.

**For BFF:** conditional power buffs must enter the canonical stat context before tooltip/heal coefficient evaluation. They must not be bolted on afterward as Healing Done multipliers, and duration/rank legality must remain separate from the named buff's stat magnitude.

---

## 2026-09-09 — The same buff coverage can have very different raid costs

While adding provider-workload comparison, BFF reached an important distinction:
two plans can both cover the same named buff for the right people at the right time
without being equally expensive to execute.

One plan might use several ordinary skill refreshes and spend Magicka plus multiple
global cooldowns. Another might use fewer casts but consume Ultimate, occupy a
different bar slot, require a heavy attack, or pull a healer, tank, or damage dealer
away from their primary job at a worse moment.

**Layman's version:** "the buff was covered" tells us the job got done. It does not
tell us how annoying or expensive the job was, or which player had to stop doing
something else to maintain it.

**What it means in actual play:** two raid compositions with identical buff uptime
can still feel and perform differently. The better assignment may depend on whether
the group can more easily spare Magicka, Ultimate, bar space, refresh casts, recovery
heavies, or attention from a particular role.

**For BFF:** provider coverage remains a hard gate, but viable plans must retain
separate workload evidence. BFF must not hide those tradeoffs inside one arbitrary
score that pretends a bar slot, a heavy attack, a GCD, and 200 Ultimate are naturally
interchangeable.

---

## 2026-09-09 — An instant skill is not proof of a free rotation slot

While connecting provider workload to canonical skill timing, BFF could prove when
a skill had a cast time or channel time. An instant skill usually had zero in both
database fields. That still did **not** prove that the action consumed zero general
combat cadence or could be squeezed between two other abilities for free.

**Layman's version:** "instant" means the character does not stand there casting or
channeling it. It does not mean the button press takes no place in the rotation.

**What it means in actual play:** an instant support skill can still replace another
skill cast, delay a heal or damage action, and make a rotation busier even though its
tooltip does not show a cast time.

**For BFF:** imported cast/channel time and the general global cooldown are separate
facts. Zero cast/channel time must not silently become zero workload. Until BFF has
versioned canonical GCD evidence, the planning GCD remains an explicit input and a
missing value blocks workload comparison.

---

## 2026-09-09 — The skill's base price is not always what the build pays

The canonical ability row stores a skill's base resource cost, but a real saved build
may pay less because of verified racial passives, armor passives, or jewelry cost
glyphs. Compound skills can also charge more than one resource pool at once.

**Layman's version:** the database price tag is the starting price. Your character's
actual receipt can be different.

**What it means in actual play:** assigning the same support skill to two players can
create different sustain pressure even when they cast it the same number of times.
A Breton healer wearing Light Armor, for example, may not pay the same Magicka cost
as another character carrying the identical skill.

**For BFF:** provider workload must use the existing final-action-cost engine after
class/racial, armor, and jewelry evidence is resolved. If a selected modifier is not
verified, BFF blocks the comparison rather than quietly falling back to base cost.

---

## 2026-09-09 — A zero-cost Ultimate can still spend Ultimate after it is summoned

While closing the provider-workload Ultimate gap, BFF confirmed that persistent
Ultimates need a different cost shape from ordinary one-button Ultimates. Eternal
Guardian's slotted summon has no positive base cost in the canonical ability row,
but its description explicitly says that the later Guardian's Wrath activation
costs 75 Ultimate.

**Layman's version:** the bear can be free to keep around while its special mauling
button still charges Ultimate. Zero on the summon is not proof that every later
activation is free.

**What it means in actual play:** a persistent Ultimate can occupy a slot and remain
active while repeated paid activations consume the shared Ultimate pool. Its rotation
burden therefore cannot be modeled like either a normal skill or a single ordinary
Ultimate cast.

**For BFF:** only an explicit secondary-activation contract from canonical ability
text may replace the missing positive base cost. Unsupported zero-cost Ultimates
remain unresolved; BFF does not hunt for a nearby number and declare it the price.

---

## 2026-09-09 — A blocked provider plan is not the same thing as an expensive one

While connecting provider workload candidates to frontier comparison, BFF had to keep three outcomes separate: a plan that cannot be projected, a projected plan that fails required coverage or contains unresolved mechanics, and a viable plan that is simply more expensive than another viable plan.

**Layman's version:** failing to do the job is not the same as doing the job badly. If a support setup misses required recipients or uptime, it should not enter the same cost contest as setups that actually satisfy the assignment.

**What it means in actual play:** a plan with fewer casts or lower resource cost can still be unusable if it drops the required buff or cannot be modeled honestly. Only after the hard job requirements are met does it make sense to ask whether another legal plan needs fewer casts, less Magicka, less bar space, less Ultimate, or less role displacement.

**For BFF:** candidate evaluation now treats projection rejection and workload blockers as hard gates before Pareto-style dominance. Frontier comparison only happens among candidates for the same effect and comparison horizon, and surviving frontier plans remain policy choices rather than being collapsed into a fake universal winner.


---

## 2026-09-09 — Critical Healing can exist in data and still vanish before calculation

The Shadow correctly carried an **11% Critical Healing** effect in the Mundus data, and the core stat calculator already knew how to calculate Critical Healing. The bonus was still missing from Extreme healing results because the static build-input router did not include `critical_healing` in its core-field and ratio-point mappings.

**Layman’s version:** having the right number in the database is not enough. Every layer between the database and the final heal has to know how to carry that number forward. One missing routing entry can make a valid bonus quietly disappear.

**For BFF:** static combat stats need end-to-end regression tests that prove a mechanic survives repository resolution, input routing, and calculation.


---

## 2026-09-09 — Supported named buffs still need optimizer scenario plumbing

The general combat-state calculator already knew how to apply named buffs such as **Major Sorcery** to raw coefficient inputs like Spell Damage. The conditional MOST Actual Heal optimizer could still miss that bonus because it only constructed combat state from its own trigger-specific services and had no explicit named-buff scenario input.

**Layman’s version:** a mechanic can be perfectly implemented in the calculator and still disappear if the optimizer never carries the active-buff evidence into that calculator. “Supported” and “actually reachable by this optimizer” are separate questions.

**For BFF:** conditional named buffs are now explicit scenario evidence. They are never granted automatically, and they share the same canonical `CombatState` path as trigger-proven buffs such as Essence Drain Major Mending.


---

## 2026-09-09 — A selected potion is availability, not an active combat buff

A saved potion selection proves that the build has access to that consumable. It does **not** prove that a potion-derived named buff is active at the heal snapshot. The active state depends on an explicit use event, elapsed time, the potion trait duration, and the character's recorded **Medicinal Use** rank.

**Layman’s version:** equipping a spell-power potion does not mean Major Sorcery is permanently switched on. Extreme MOST Actual Heal now requires an explicit potion-use window and checks whether the buff is still alive at that exact timestamp.

**For BFF:** potion-derived named buffs now enter the same canonical `CombatState` path as other proven transient buffs, and missing Medicinal Use progression remains an explicit blocker rather than an invented rank.


---

## 2026-09-09 — Extreme may discover potion families only inside an explicit potion-use scenario

The Extreme MOST Actual Heal search may compare canonical potion families when, and only when, the caller has explicitly requested a potion-use snapshot. Candidate generation proves potion-family availability; the existing potion event/cadence layer still proves whether each named buff is actually active at the requested elapsed time.

**Layman’s version:** the optimizer is allowed to shop the potion shelf, but only after the scenario says a potion was actually used. It still cannot treat a selected bottle as a permanent character stat.

**For BFF:** standing heal optimization remains unchanged. Conditional potion-window optimization can now discover a stronger legal potion source instead of requiring the caller to preselect the winning potion.


---

## 2026-09-09 — Skill-buff discovery requires an explicit pre-cast snapshot

Extreme MOST Actual Heal may discover a slottable skill as a named self-buff source only inside an explicit pre-cast timing scenario. The first reviewed slice admits only canonical CAST effects that target SELF, have a positive sourced duration, map to a supported named stat buff, and carry no extra condition or trigger.

**Layman’s version:** if the optimizer wants Major Sorcery from a skill, it must actually slot a legal skill that grants it and the buff must still be alive when the heal lands. Conditional or proc-based skill effects are not waved through just because their name looks useful.

**For BFF:** the scored heal's slot is protected during source discovery. Standing optimization is unchanged, and runtime/conditional skill effects remain outside this first automatic-discovery slice.


---

## 2026-09-09 — Triggered skill buffs require observed runtime-event proof

Extreme MOST Actual Heal may search triggered self-buff skills only when the caller supplies an observed canonical `RuntimeEvent` and an explicit heal snapshot time. The shared runtime eligibility layer remains authoritative for trigger matching, cooldown readiness, and deterministic proc chance. Free-form conditional effects are still excluded from automatic discovery.

**Layman’s version:** a skill proc does not exist because the build could theoretically proc it. Extreme needs the actual trigger scenario, checks proc chance/cooldown rules, and then verifies the buff has not expired before the heal lands.

**For BFF:** triggered skill-source candidates physically slot the skill without replacing the scored heal, and only an eligible, still-active named self-buff reaches canonical `CombatState`.


---

## 2026-09-09 — Gear-proc self application must be explicit, not inferred from ally/group targeting

Extreme MOST Actual Heal now evaluates verified gear-set proc effects against explicit runtime events, cooldown state, proc chance, and the exact heal snapshot. Existing Extreme gear candidates remain responsible for physically equipping sets; the runtime layer uses canonical `GearStatInputResolver.equipped_set_counts` and `GearSetEffectVariantResolver` to determine what the candidate can actually proc.

A proc recorded as `ALLY` or `GROUP` is **not** automatically treated as a buff on the wearer. This matters for records such as Spell Power Cure, whose verified trigger identity currently says `overheal_self_or_ally` while its target model is `ALLY`. Until the target model can explicitly prove wearer self-application, Extreme reports that ambiguity instead of adding Major Courage to the healer.

**Layman’s version:** wearing a proc set and successfully triggering it still does not prove the buff landed on *you*. Extreme now insists on that last piece of evidence before using the buff to inflate MOST Actual Heal.


---

## 2026-09-09 — Self-or-ally targeting is distinct from ally-only targeting

Canonical support targeting now includes `SELF_OR_ALLY` for effects that can explicitly land on either the source or another friendly target. This is intentionally distinct from `ALLY`: ally-only effects still do not prove wearer application. Spell Power Cure Major Courage is classified `SELF_OR_ALLY` because its verified trigger semantics are `overheal_self_or_ally`. Extreme MOST Actual Heal may therefore use SPC on the healer only when the proc runtime event, duration, and other eligibility checks also pass.


---

## 2026-09-09 — Runtime condition names require explicit evidence, not interpretation

Runtime proc eligibility now accepts the same opaque named `ConditionContext` used by the canonical effect-relationship layer. A conditional skill/set proc is not eligible merely because its trigger fired. If no runtime condition context is supplied, the result is `condition_context_required`; if a context is supplied but the required condition name is absent, it is `condition_unsatisfied`. Extreme MOST Actual Heal forwards independent skill and gear condition evidence into this shared gate.

**Layman's version:** seeing the event happen is not proof that every extra clause on the proc was true. The optimizer now needs explicit evidence for those clauses before it uses the buff.


---

## 2026-09-09 — Maximum-heal snapshots need ordered runtime history, not isolated proc events

The canonical runtime stream now carries each event attempt's deterministic chance roll and named condition evidence together. Extreme actual-heal skill and gear runtime services can evaluate ordered event histories and query the retained canonical active windows at one exact heal snapshot. This permits independently triggered buffs to overlap only when their real windows overlap, while cooldown, failed conditions, chance failures, refresh/stacking behavior, and exact end-time boundaries remain owned by the shared runtime engine. Missing stacking semantics remain an explicit blocker rather than being guessed.


---

## 2026-09-09 — Extreme snapshot optimization needs one runtime-history contract

Extreme role objectives should not maintain separate temporal truth for skill triggers, gear procs, and potion windows. The first unified runtime-snapshot contract carries one ordered `RuntimeEffectEventAttempt` history, one exact snapshot time, and potion elapsed timing while potion use remains outside the shared runtime stream. Skill and gear buffs are both resolved from that same ordered history before the candidate `CombatState` is built. Legacy single-trigger inputs remain supported only when the unified snapshot is absent; mixing the two paths is rejected to prevent double application. Class-specific emergency assumptions still layer into the same `CombatState` until their windows are represented by role-neutral canonical runtime evidence.


---

## 2026-09-09 — Extreme runtime snapshots need one role-neutral CombatState projector

The unified `ExtremeRuntimeSnapshot` contract is projected through one shared `ExtremeRuntimeSnapshotCombatStateService` before a role objective evaluates its own healing, tanking, or damage semantics. The projector owns ordered skill-history named buffs, gear-proc history, and explicit potion-window activation, deduplicates the resulting named buffs, and preserves runtime blockers. Healer-specific states such as Restoration Staff heavy completion or Sacred Ground still layer afterward until those mechanics are represented as role-neutral canonical runtime evidence. Tank and Damage Dealer Extreme objectives should consume this projector rather than recreate runtime truth.

---

## 2026-09-11 — An unresolved effect still has a time window

Overflowing Altar exposed a difference between an unresolved mechanic and a global
blocker. Its Minor Lifesteal trigger behavior is still unresolved, but the reviewed
30-second effect duration is enough to determine which encounter windows it could
possibly affect. A cast at 44 seconds cannot block a healing demand that ended at
34.13 seconds.

**Layman's version:** not knowing exactly how an effect works does not make it a
time traveler. An unresolved later cast cannot reach backward and spoil an earlier
healing window.

**What it means in actual play:** the 10-second Altar may matter during Xalvakka's
29.13–34.13-second healing-prep window because its effect is still active. The
44-second Altar cannot matter to that window. Neither cast contributes invented
healing until Minor Lifesteal's actual trigger behavior is proven.

**For BFF:** externally triggered healing is retained as structured, time-anchored
evidence. Demand evaluation scopes the unresolved trigger only to overlapping active
intervals, while numeric healing remains fail-closed.

---

## 2026-09-11 — “Every one second” may be a limit, not a timer

Minor Lifesteal's readable wording says that damaging an affected enemy heals an
attacker every one second. That wording alone does not prove whether the game runs
an automatic periodic tick or reacts to damage events with a per-actor lockout. It
also does not prove whether the Altar caster or each attacker owns the resulting
heal event.

**Layman's version:** “once a second” can mean a metronome or a speed limit. Those
look similar on a tooltip but produce different combat events.

**What it means in actual play:** twelve attackers hitting the same debuffed boss
may generate independently owned healing streams rather than one healer-owned HoT.
That must be demonstrated from current runtime evidence before BFF counts it.

**For BFF:** ESO Logs discovery now preserves heal ownership, preceding same-actor
damage, numeric aliases, and observed intervals as candidate evidence. No cadence,
cooldown, or caster-credit rule is promoted until those observations are reviewed.

