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



---

## 2026-09-11 — A triggered heal can be credited to someone other than its trigger

Reviewed Minor Lifesteal evidence exposes two different kinds of ownership. In the
focused Lokkestiiz runtime review, observed heal alias **86304** was logged under an
effect-provider source while the heal targets varied across the raid. Each displayed
recipient heal correlated with that recipient's immediately preceding damage, while
the provider did not need a matching damage event. Per-recipient streams clustered
near the tooltip's one-second limit.

**Layman's version:** the player whose name owns the heal in the log may not be the
player whose attack caused it. The combat log can hand the healer the receipt while
a damage dealer pressed the button that made the heal happen.

**What it means in actual play:** Minor Lifesteal is triggered independently by each
attacker damaging the affected enemy; that attacker receives the heal, while ESO Logs
may credit the resulting healing to the player who supplied the effect.

**For BFF:** provider, recipient, and triggering actor remain separate identities.
The rotation builder may project 600 Health per active attacker per covered second
only when strategy input explicitly supplies the number of continuously active
attackers. It does not assume all raid members attack and does not create fake
automatic HoT ticks.

---

## 2026-09-11 — A weapon trait can matter to the rotation without changing its healing number

The **Charged** weapon trait increases status-effect application. That can be very
important for damage, debuffs, and support effects, but it does not directly change
the raw magnitude of the direct, periodic, delayed, or Minor Lifesteal healing being
measured by the healer demand-output objective.

**Layman's version:** Charged can help the healer do more support work without making
the green healing numbers themselves larger.

**For BFF:** an unresolved Charged status-chance calculation remains visible as an
ambient diagnostic in healer-output audits, while support and damage objectives may
still treat it as a required blocker. Role relevance does not rewrite the shared
weapon mechanic.

---

## 2026-09-11 — A rotation snapshot must carry the transient state it is claiming to evaluate

The static build calculator can represent temporary combat facts such as active named
buffs, Emperor state, and update-version semantics through `CombatState`. The
Rotation Builder's canonical candidate bridge previously resolved front/back static
contexts without a way for its caller to supply that state, so any transient combat
scenario silently collapsed back to the empty default state.

**Layman's version:** if we ask "what does this rotation look like while this buff is
actually active?", the buff has to make it all the way into the calculator. Owning a
skill or wearing a set that *can* create the buff is not the same thing as proving it
is active at that moment.

**For BFF:** canonical rotation candidate evaluation now accepts explicit
`CombatState` and sends the exact same state through both bar snapshots. Runtime
conditions remain caller-owned evidence and are never inferred merely from the build.
---

## 2026-09-12 — A buff is not proof of the specific skill that supplied it

The default raid coverage watch list names **War Horn**, but its current canonical
mapping points to the general `force` effect. Static evidence for an effect can
come from a source other than the specific ultimate the raid lead meant to assign.

**Layman's version:** seeing a Force buff in a saved build does not tell us that
someone actually slotted, can cast, or was assigned War Horn.

**For BFF:** the Main-page War Horn check stays unverified until an exact
War Horn source and its responsibility are established. Static availability
never proves that the buff will be active during the pull.

---

## 2026-09-13 — A Champion Point formula can still have a simple hard ceiling

**Enlivening Overflow** describes Recovery as a percentage of Max Magicka, but the same tooltip explicitly caps the granted Recovery at **150**. For a maximum-record search, the percentage tells BFF what input is needed to reach the cap; it does not permit the result to grow beyond 150.

**Peace of Mind** exposes a different trap: “40 per stage” is not “40 per point.” Its Champion Point jump metadata has five unlock thresholds, so its complete ceiling is **5 × 40 = 200** while Crowd Control Immunity is active.

**Layman’s version:** one tooltip has a speedometer with a hard stop; the other has five actual steps even though it accepts 50 points. Reading only the largest number on the record gives the wrong answer in both cases.

**For BFF:** explicit caps outrank uncapped formula projection, and per-stage mechanics use canonical jump thresholds. These are individual-star ceilings only; Champion Bar slot legality must still prove which stars can coexist.

---

## 2026-09-13 — Champion Point slots are four per discipline, not four total

A Champion Bar has a separate four-slot budget for each discipline. Two useful stars in different disciplines do not compete for the same slot, while a fifth useful star in one discipline must displace one of that discipline’s other four.

**Layman’s version:** the Champion Bar is three small shelves, not one shared shelf. A full red shelf does not prevent using an available blue slot.

**For BFF:** CP loadout dominance groups candidates by canonical discipline identity and takes only the strongest four additive candidates in each group. Conditional stars keep their runtime requirements; fitting on the bar does not prove their conditions are active.

---

## 2026-09-13 — Maximum stored Ultimate and maximum Ultimate-spend recovery pull in opposite directions

The pure-Dragonknight Health Recovery route uses **Booming Voice** at its maximum **250-Ultimate spend**, while **Strategic Reserve** reaches its own maximum only at **500 stored Ultimate**. Casting the Ultimate leaves 250 stored, and Booming Voice does not start its recovery window until 15 seconds later.

Even an optimistic currently modeled timeline—continuous base combat generation plus both Minor and Major Heroism through the end of Booming Voice’s window—restores **136 Ultimate**, reaching **386**. That leaves a **114-Ultimate proof gap** before Strategic Reserve can honestly claim its 1,500 ceiling at the same moment.

**Layman’s version:** one bonus wants you to spend a very full Ultimate bar, while the other wants the bar full again almost immediately afterward. We cannot award both gold medals just because each wins alone.

**For BFF:** this is unresolved, not proven impossible. Additional legal Ultimate sources may close the 114 gap, but they must be catalogued, timed, and checked against the same class/gear state before the two component maxima are combined.

---

## 2026-09-13 — “Ultimate generation” is not one interchangeable bucket

The U50 calculator snapshot exposes sources from Class Masteries, class and racial passives, active skills, Vampire state, named gear, weapon traits, base combat generation, and Heroism. Similar displayed rates can still have completely different triggers, recipients, cooldowns, proc chances, and build costs.

The snapshot also notes that Minor and Major Heroism share the same 1.5-second event cadence for **Decisive**: their values can stack, but Decisive receives one proc opportunity from that merged event rather than two independent rolls.

**Layman’s version:** “four Ultimate per second” is not a universal Lego brick. One version may require a monster set, another becoming a Vampire, and another may give the Ultimate to everybody except you.

**For BFF:** the calculator discovers the denominator. Every surviving source must still earn canonical timing, self-targeting, and legal-build evidence before it can fill Strategic Reserve’s 114-Ultimate gap.


---

## 2026-09-13 — Ultimate recipient and cast clauses outrank headline generation

**Pillager's Profit** grants its Ultimate to other group members, so the caster cannot
use it to refill their own **Strategic Reserve**. **Cryptcanon Vestments** prevents
the normal Ultimate cast required by the Booming Voice route. Neither source belongs
in the self-refill sum merely because its tooltip contains the word “Ultimate.”

**Blessing at the Peak** is legal on the pure Dragonknight route, but its one Ultimate
per six seconds yields only four witnessed post-cast triggers before the 24.999-second
score. It reduces the reviewed deficit from **114 to 110**; it does not close it.

**For BFF:** recipient identity, cast legality, and an explicit trigger timeline are
canonical gates. The remaining Vampire, gear, skill, and weapon-trait sources stay as
separate whole-build search states.


---

## 2026-09-13 — A source ceiling is not a free build bonus

Five named gear sources can now be bounded inside the 24.999-second Strategic
Reserve window. Their individual ceilings are **Baron Zaudrus 96**, **Bloodspawn
65**, **Arkasis's Genius 44**, **Arkay's Charity 39**, and **Hide of the Werewolf
30** Ultimate. None individually fills the remaining 110-point gap.

Bloodspawn's number is especially slippery: 65 is the result if every eligible
six-percent proc succeeds. It is a hard maximum-proc ceiling, not a deterministic
promise that five procs occur.

**For BFF:** a window ceiling only permits a candidate to remain in the search.
Equipment slots, mutually exclusive monster sets, proc evidence, and lost Health
Recovery still decide whether that candidate improves the actual record.


---

## 2026-09-13 — Mutually exclusive source ceilings must not be summed

The first Ultimate-source window report correctly bounded five named gear branches,
then incorrectly added every branch together. That imaginary character simultaneously
wore competing five-piece and monster-set states and appeared to erase the Strategic
Reserve gap with 278 Ultimate.

The corrected shared-route increment remains **Blessing at the Peak's 4 Ultimate**.
Each equipment, Vampire, and weapon-trait ceiling stays separate until a legal combined
build witness equips it. Rank-four **Exhilarating Drain** can reach a 115-Ultimate
window ceiling only by occupying nearly the entire post-cast timeline, while
**Decisive's** 40-point all-procs ceiling remains stochastic.

**For BFF:** candidate ceilings are comparison bounds, not additive bonuses. Only
sources proven compatible in one physical build and one action timeline may be summed.


---

## 2026-09-13 — Filling Strategic Reserve can still lower Health Recovery

Rank-four **Exhilarating Drain** can theoretically generate enough Ultimate to refill
Strategic Reserve before Booming Voice ends. Becoming even a stage-one Vampire,
however, applies **−10% Health Recovery** to the whole result.

Using only the already-proven base, Khajiit, Dragonknight, Steed, and jewelry values,
the non-Strategic shared subtotal is **3,549.806**. Moving Strategic Reserve from
1,170 at 390 Ultimate to its 1,500 cap adds 330, but the Vampire multiplier reduces
the conservative candidate to **4,544.825**, below the non-Vampire incumbent's
**4,719.806**. Food, gear, and other positive sources only widen that loss.

**Layman's version:** Drain fills the Ultimate bar and still makes the green number
smaller. A fuller bar is not automatically a better Health Recovery build.

**For BFF:** Exhilarating Drain is pruned from this record route by a conservative
dominance proof. It remains a valid Ultimate-generation mechanic in other objectives.

---

## 2026-09-13 — `5+5+2` arithmetic does not prove a real equipment loadout

An Ultimate-source combination can fit the familiar twelve set-count units and still be impossible to equip. Bloodspawn and Baron Zaudrus both need the same Head/Shoulders monster-set slots, so their combined four set-count units are numerically small but physically incompatible. Conversely, a legal `5+5+2` route still needs an exact named-set slot witness.

**Layman's version:** adding the piece counts tells us whether the suitcase is too heavy; it does not prove every item actually fits in the suitcase.

**For BFF:** Ultimate-source combinations now call the canonical named-set realization service instead of trusting piece-count sums. That closes set-slot coexistence only. Seven-Heavy armor compatibility and the Health Recovery lost by equipping Ultimate-generation gear are still separate proof gates.

---

## 2026-09-13 — A provider skill name is not enough when the assignment is bar-specific

A provider assignment can require an exact source skill on an exact bar. During the assignment-to-workload bridge, BFF could correctly identify only the front-bar casts, then the downstream workload matcher rediscovered every same-named cast without remembering the bar.

**Layman's version:** if the raid plan says “this front-bar cast is the provider action,” a same-named back-bar cast is not automatically another copy of the assigned job.

**What it means in actual play:** bar ownership can change the true refresh count, GCD burden, resource cost, and timing of a support responsibility even when the skill name is identical.

**For BFF:** provider action bindings now preserve optional front/back bar identity end to end. Bar-agnostic assignments still match either bar, but an explicit bar requirement survives candidate generation instead of being broadened downstream.

## 2026-09-15 — Weapon/Spell Damage scaling is not sheet power

When a tooltip says an attack, heal, or proc “scales off” Weapon or Spell Damage,
that stat is an input to the effect; the effect does not raise the character's
Weapon or Spell Damage. Extreme power searches may discard that proc for the
literal sheet-stat objective while still retaining any separate line that grants
Weapon/Spell Damage directly.

---

## 2026-09-15 — A parsed set line does not bound an unmapped proc

A set can have an ordinary parsed bonus such as **129 Weapon and Spell Damage**
and a separate conditional five-piece bonus that grants hundreds more. The parsed
line proves only its own 129-point contribution; it says nothing about the ceiling
of the additional proc.

**Layman's version:** reading one line on the set does not put a cap on every other
line. A small known bonus cannot stand in for a larger conditional one.

**For BFF:** Extreme proof audits bound every active power-granting bonus
independently, then add those ceilings. An unresolved proc remains a blocker unless
its own description supplies a finite conservative bound.

---

## 2026-09-16 — A proc can consume a skill slot even when it is not the scored action

**Burning Spellweave** grants its 490 Weapon/Spell Damage only after a Flame-damage
ability hits an enemy. For an H1 heal snapshot, that Flame action is setup work: it
must be a legal skill, occupy a real slot, trigger the proc, and leave the heal inside
the eight-second power window.

**Layman's version:** the set bonus is not a free 490 just because the character can
wear the set. Somebody still has to light the match.

**For BFF:** Burning Spellweave candidates materialize a reviewed Flame-damage action
on the inactive bar, then swap back to the scored heal. Unknown or missing Flame
witnesses remain unresolved rather than receiving the proc.

---

## 2026-09-16 — “You and nearby group members” includes the set wearer

**Crusader** applies Minor Courage to the wearer as well as nearby group members, but
only after direct damage from a Blink, Charge, Leap, Teleport, or Pull ability creates
its consecrated area. The named buff is self-eligible; the trigger action is not free.

**Layman's version:** standing in your own shiny circle counts. You still have to spend
a real skill slot making the circle first.

**For BFF:** Crusader candidates materialize a reviewed direct-mobility damage action
on the inactive bar, swap back to the scored heal, and enter the ordinary canonical
Minor Courage state. Existing Minor Courage does not stack with it.

### Basalt-Blooded Warrior bar identity matters for healing

Basalt-Blooded Warrior does not grant its healing bonus merely because an Earthen Heart skill was cast. The cast starts a 10-second stance window. Its current primary/front Molten Stance grants Major Heroism, while the +14% Healing Done branch is Obsidian Stance on the secondary/back weapon. For an Extreme H1 heal witness, the setup therefore has to cast an Earthen Heart ability from the primary/front bar, swap bars, and score the heal from the secondary/back bar before the stance expires.

### Class route IDs and skill-line display names are the same identity

Extreme routes store class lines as stable snake-case IDs such as `earthen_heart` and `winters_embrace`, while the skill database exposes display labels such as `Earthen Heart` and `Winter's Embrace`. Candidate legality must normalize both forms before comparing them. A literal comparison can make every active skill from an otherwise legal subclass line disappear, even though the route itself is valid.

### Armor Master needs the Armor ability on the scored bar

Armor Master's 5% Max Health bonus is a slotted condition, not a short proc window. A legal Light, Medium, or Heavy Armor active must remain on the same bar used for the scored event, and it must match an armor weight the build actually wears. Casting an Armor ability additionally grants resistance for 10 seconds, but that resistance branch does not increase the H1 heal.

### Beacon of Oblivion is a chosen pet state, not a bar-slot rule

Beacon of Oblivion has mutually exclusive five-piece branches. An active permanent
pet grants Health and Armor; having no permanent pet active grants 15% Damage Done
and Healing Done in PvE, reduced to 7% while Battle Spirit is active.

**Layman's version:** a pet skill can stay on the bar, but the pet must be dismissed
or never summoned when the heal is measured. PvP's Battle Spirit also changes the
number.

**For BFF:** H1 admits the 15% branch only through an explicit no-permanent-pet,
Battle-Spirit-inactive witness. Equipping the set alone never activates the bonus,
and the 7% PvP value cannot leak into the PvE maximum.


## Jorvuld's Guidance is provider-local
- Jorvuld's Guidance extends eligible Major/Minor buffs and damage shields applied by the wearer.
- It is not a generic group-wide duration extender.
- Comp Maker / Coverage / Rotation must preserve provider identity when evaluating Jorvuld: the relevant question is which effects that wearer applies, not merely whether the group contains the set.
- Static set presence can prove the modifier is available to that wearer; it does not by itself prove uptime or that another player's buffs are extended.


## Phase 14 Comp/Raid Plan provenance
- A brand-new Comp Maker plan has a small identity chicken-and-egg problem: the Comp Build needs a BuildId before the Raid Plan can point to it, while the build cannot record its source Raid Plan id until that plan exists. The save path now performs one safe second metadata pass after first binding. It updates the same stable Comp Build instead of creating another one, so Builds, Coverage, and Readiness all carry the same identity.


## 2026-09-20 — Execute damage depends on the Health created by earlier simulated actions

Target-Health-conditioned damage cannot be evaluated from one static boss Health value when the same simulated rotation is changing that Health over time. An earlier hit can push the target below an execute threshold, which can change the damage consequence of the very next skill. Actions at the same timestamp still have a deterministic sequence, so sequence 0 can change the Health seen by sequence 1.

**Layman's version:** the second hit has to look at the boss *after* the first hit landed. If the first hit pushes the boss into execute, the second hit may legitimately become stronger or activate a conditional component.

**For BFF:** Phase 14 Combat Simulation now maintains an execution-local target Health ledger and exposes that evolving Health through the existing canonical `CombatStateSnapshot` contract. Execute thresholds and reviewed target-Health amplification remain owned by the existing Rotation DD mechanics; the simulator only supplies the changing Health evidence and never invents an execute rule.


## 2026-09-20 — A DoT's total damage cannot be dropped onto the target at cast time

The Rotation DD scorer can correctly store a periodic skill's full within-horizon damage under the cast that created it, because its job is to total the rotation. Combat Simulation has a stricter timing requirement: those same points of damage have to arrive on their actual tick timestamps.

**Layman's version:** if a 10-second DoT will eventually do 20,000 damage, the boss does not lose all 20,000 Health the instant the skill is cast. Doing that would push execute thresholds and death earlier than they really happen.

**For BFF:** whole-plan periodic totals are now blocked from the live target-Health ledger. Direct hits may affect Health immediately; periodic skills stay unresolved in Combat Simulation until the existing reviewed tick schedule can also supply occurrence-level damage magnitude.


### Follow-up — periodic damage now lands on its reviewed occurrence timestamps

The simulator now carries canonical periodic damage as individual occurrences rather than one parent-cast total. Mixed skills can therefore deal an immediate hit at cast time and separate DoT ticks later. Reviewed snapshot-at-cast magnitude keeps the source-side magnitude frozen while exact-time recipient state can still vary at each tick; reviewed dynamic-at-tick magnitude can recalculate from an exact runtime build context when the caller supplies one.

**Layman's version:** the first hit happens when you press the skill, and the DoT keeps hitting later. The boss Health bar now changes on those later hits instead of pretending the entire DoT happened up front.

**For BFF:** execute thresholds, death timing, and later actions can now react to the Health produced by earlier periodic ticks. Missing runtime context or unreviewed periodic semantics remain unresolved instead of being guessed.


## 2026-09-20 — Same-timestamp DoT ticks and actions need an explicit ordering rule

A periodic tick and a scheduled skill can share the exact same clock timestamp. If either result depends on target Health, the order can change execute eligibility, overkill, or which event actually kills the target. No reviewed repository rule currently proves a universal cross-source ordering for that collision.

**Layman's version:** if a DoT tick and your execute both happen at 10.0 seconds, we cannot assume which one lands first just because one happened to be earlier in a Python list.

**For BFF:** Combat Simulation now fails closed at that exact collision unless a reviewed ordering authority is supplied later. Damage that occurred strictly before the ambiguous timestamp remains valid; damage at and after the unresolved boundary is not treated as proven.


## 2026-09-20 — Same-instant Health changes need recipient-specific ordering evidence

Damage and healing can target the same combatant at the same clock time. If the simulator knows a sequence, that sequence is enough to replay the Health changes deterministically. If multiple Health consequences share the same timestamp, event priority, and sequence, their order can affect death attribution, overkill, overheal, and whether later healing is legal.

**Layman's version:** a hit and a heal both stamped 10.0 seconds are not safely ordered just because one event name sorts before the other in the alphabet.

**For BFF:** Phase 14 now blocks Health projection for that recipient from the ambiguous boundary onward unless timestamp/priority/sequence already proves the order. Earlier Health history remains valid. Exact-time snapshots can also request a sequence boundary so state at one timestamp can be inspected between ordered actions.


## 2026-09-20 — A simulator event stream needs cause before state change

Combat Simulation distinguishes an event that *causes* Health change from the derived Health transition itself. If both share the same ordering coordinate, a naive generic sort can place the derived state change before the damage/heal event that caused it.

**Layman's version:** the hit has to happen before the Health bar changes, and the Health bar has to reach zero before the death transition exists. Alphabetical sorting is not a combat mechanic.

**For BFF:** raw direct damage/healing now precedes derived Health changes through explicit event priority, death remains later, queue ordering never compares payload contents, and already-dead recipients do not receive synthetic 0-to-0 damage transitions. Exact-time sequence snapshots now apply the same boundary to bar, resources, Health, and active effect windows.


## 2026-09-20 — Simultaneous components from one hit should not invent component order

One skill can legitimately produce multiple direct damage components at the same timestamp and action sequence. Their combined Health effect is well-defined, but applying the components one at a time can make overkill depend on arbitrary component order.

**Layman's version:** if one skill hits for 2,000 magic plus 3,000 flame at the same instant, the boss took 5,000 from that skill. We should not let whichever component happens to be listed first decide how much overkill gets reported.

**For BFF:** raw component events stay separate for audit/source detail, while Health projection coalesces same-source same-kind components at one coordinate before applying Health, overkill, and death. Different sources or damage/healing collisions still require explicit ordering evidence.

## 2026-09-20 — Death at one action sequence ends later actions at the same timestamp

Combat Simulation can have more than one scheduled action at the same clock timestamp, distinguished by sequence. A lethal hit at sequence 0 is therefore earlier than a sequence-1 action at that same timestamp.

**Layman's version:** if the boss dies on the first thing that happens at 10.0 seconds, the second thing scheduled for 10.0 seconds does not still get to happen just because the clock display has not changed.

**For BFF:** fight termination now preserves the exact lethal time-and-sequence coordinate. Later same-timestamp action sequences and injected combat events are excluded from execution, preventing resource costs, healing, effects, or other consequences from firing after target death.

## 2026-09-20 — Periodic damage stops at the requested simulation horizon

A damage-over-time effect can have reviewed ticks scheduled after the requested simulation duration. Those later ticks are outside the modeled fight window and must not alter Health, death timing, or fight termination inside that run.

**Layman's version:** if we simulate only the first 5 seconds, a DoT tick scheduled for second 6 does not get to reach backward and kill the boss in the 5-second result.

**For BFF:** sequential DD projection now discards periodic occurrences beyond the plan duration before they can change the target Health ledger or create a terminal fight coordinate.

## 2026-09-20 — Attempted damage is not the same thing as proven applied damage

Combat Simulation can know that an outgoing hit attempted a specific amount while still lacking the target Health state needed to prove how much damage actually landed, whether there was overkill, or whether the hit killed the target.

**Layman's version:** knowing a skill tried to hit for 2,500 does not prove the boss actually lost 2,500 Health if we do not know the boss's Health state.

**For BFF:** outgoing DD damage without explicit target Health now remains damage-unresolved. Modeled DPS is withheld instead of reporting zero applied DPS as if that were a proven result. Incoming/environmental damage gaps remain general simulation issues and do not incorrectly poison DD completeness.

## 2026-09-20 — A DD fight simulation must start with a living target

The sequential DD Health ledger is intended to model damage progression during an active fight. Starting it with the target already at zero Health leaves no valid combat progression to simulate and can otherwise make every later action look like a harmless resolved zero.

**Layman's version:** if the boss is already dead before the clock starts, that is not a zero-DPS fight. It is no fight at all.

**For BFF:** saved-build DD simulation now rejects a target that starts at zero Health instead of treating the full plan as a valid completed zero-damage run.

## 2026-09-20 — Ambiguous outgoing damage ordering also makes DPS incomplete

Two different outgoing damage sources can share the same timestamp, priority, and sequence. When that happens, Combat Simulation already refuses to invent an order for their Health consequences. That ambiguity must also count as damage-specific unresolved evidence.

**Layman's version:** if two different hits are stamped at the exact same combat coordinate and we cannot prove which applies first, we cannot safely claim the resulting applied damage or DPS is complete.

**For BFF:** cross-source same-instant outgoing-damage collisions now populate damage_unresolved as well as general unresolved. Modeled DPS is withheld until an authoritative ordering rule exists. Same-source components of one hit remain safely coalesced for Health.

## 2026-09-21 — Same-timestamp resource ordering must preserve one Health-independent sustain truth

Combat Simulation reuses the established resource-timeline rule that action costs resolve before same-timestamp recovery/restoration. If a supplied resource timeline reverses that order, its before/after chain can disagree with the simulator's canonical event order and produce a different final resource value in snapshots.

**Layman's version:** if a skill costs Magicka at the same instant a recovery tick lands, BFF cannot let one subsystem say the tick happened first while another says the cost happened first. Otherwise two parts of the same simulation can report different ending Magicka.

**For BFF:** the Combat Simulation resource adapter now rejects noncanonical same-timestamp ordering instead of reordering contradictory before/after evidence. Final resource snapshots are regression-checked against the stored resource summary.

### 2026-09-21 — Sustained DPS comparisons need the same execution horizon

A modeled DPS number is not automatically comparable just because both values are expressed as damage per second. Saved rotations can cover different execution horizons, and ESO damage profiles can be heavily front-loaded, execute-weighted, or DoT-weighted. FoundryDock therefore withholds a sustained-DPS leader when candidate execution horizons differ, even when every individual simulation is mechanically complete. Non-DD saved builds are also informational exclusions only; they do not invalidate the DD search denominator.

### 2026-09-21 — Sixty-four attribute points create 2,145 legal splits before the build even starts

ESO's 64 attribute points can be distributed across Health, Magicka, and Stamina in **2,145** non-negative integer combinations. FoundryDock now treats every one of those splits as part of the structural Extreme denominator before race, legal class route, active bar, gear, skills, CP, or rotation are considered. In plain English: brute force gets ridiculous very early, which is why later generated sustained-DPS search needs pruning instead of one heroic nested loop.

### 2026-09-21 — A tie-capable upper bound cannot be safely pruned

For MOST Sustained DPS, a generated branch whose proof-safe optimistic ceiling exactly matches the current incumbent must stay alive. It may not be able to beat the incumbent, but it can still **tie** it, which changes whether FoundryDock may claim a unique leader. Only a ceiling that is strictly below the incumbent can be discarded. Missing or unproven ceilings stay open too. Optimization is apparently also a bureaucracy.

### 2026-09-21 — Static character-sheet maxima are not sustained-DPS ceilings

A build can have a larger Weapon/Spell Damage, crit, penetration, resource pool, or Mundus contribution and still fail to provide a proof-safe upper bound on **sustained DPS**. Skill coefficients, cast cadence, DoT timing, proc frequency, execute behavior, cooldowns, resource failure, and rotation composition can all change the final rate. FoundryDock therefore treats static dynamic-axis refinement as candidate evidence only. It will not prune a sustained-DPS branch until an optimistic action/rotation ceiling is proven separately.

### 2026-09-21 — A direct-hit ceiling is not a rotation ceiling

For sustained DPS, an optimistic bound on a cast's immediate hit is insufficient if that cast can also create a DoT, delayed hit, proc, or other triggered damage inside the comparison horizon. A proof-safe rotation ceiling must bound the **entire damage consequence owned by each scheduled action**, not merely the button-press hit. FoundryDock now withholds the whole-plan ceiling if even one damage action has only partial consequence coverage.

### 2026-09-21 — Exact damage is not automatically an optimistic ceiling

A fully resolved skill cast can have an exact canonical total for one concrete build and rotation witness, including its direct and periodic occurrences, without proving anything about stronger **future mutations** of that candidate. Gear, CP, passives, bar choices, or runtime states may still raise the result. FoundryDock now promotes exact action damage into a pruning ceiling only when every still-open mutation axis is explicitly covered by a dominance proof. Otherwise the candidate stays open.

### 2026-09-21 — Mundus and food cannot be safely optimized for DPS in isolation

For a sustained-DPS action, the best Mundus and the best food are not necessarily the choices with the largest independent character-sheet deltas. Their effects can interact through offensive power, resources, crit, penetration, Divines, and the skill's own scaling. FoundryDock therefore searches the finite Mundus × mapped-provisioning grid **jointly** for dominance evidence. If one combination cannot be evaluated exactly, the axis proof remains open instead of filling the gap with an independent-stat shortcut.

### 2026-09-21 — Max-resource armor reductions are not automatically DPS-safe

A trait/glyph reduction that is proof-safe for Max Health, Magicka, or Stamina can still be unsafe for sustained DPS. DPS depends on interactions such as crit, penetration, resource scaling, Divines amplification, sustain, and skill-specific coefficients. FoundryDock therefore preserves the full modeled armor trait/enchant denominator for sustained-DPS search and pages it lazily instead of borrowing a resource-objective reduction whose proof assumptions do not apply.

### 2026-09-21 — Weapon enchant identity is static; weapon enchant DPS is runtime

A weapon enchant can be selected as a build identity without knowing its sustained contribution. Its real DPS impact can depend on trigger events, cooldown, bar state, Infused, status effects, buff/debuff duration, and the rotation timeline. FoundryDock therefore enumerates weapon enchant families in the generated-search denominator but does not score them as static character-sheet bonuses. Their contribution remains owned by runtime combat evaluation.

### 2026-09-21 — Champion Point legality and Champion Point damage are separate proofs

A four-star-per-discipline Champion Bar can be structurally legal while still containing stars whose sustained-DPS contribution depends on event type, runtime conditions, target state, or rotation timing. FoundryDock now enumerates the complete canonical slottable CP legality denominator lazily, but it does not treat bar legality as proof that a dynamic star's damage is active.

### 2026-09-21 — A legal set-count partition is not yet a legal equipped build

A familiar count shape such as **5 + 5 + 2** proves only that twelve active-snapshot set-count units can be partitioned that way. It does not prove that the selected named sets can physically occupy the required armor, jewelry, and weapon slots, satisfy Mythic limits, or coexist across both bars. FoundryDock therefore keeps abstract gear topology, named-set physical realization, dual-bar compatibility, and runtime set behavior as separate proof layers.

### 2026-09-21 — An active-bar gear witness is not a complete two-bar build

A legal active-snapshot set arrangement does not prove that the same character can carry a compatible backup weapon state. Shared armor and jewelry must agree across both snapshots, weapon assignments may differ by bar, and one-bar rules such as Oakensoul can change which bar is actually activatable. FoundryDock therefore proves complete front/back coexistence before treating a named-gear witness as a generated-build candidate.

### 2026-09-21 — Knowing a set proc exists is not the same as proving it happened

A verified set mapping can tell FoundryDock that a bonus grants a specific proc, buff, debuff, passive, duration, cooldown, or trigger. That proves **mechanic identity**, not that the effect fired in a particular rotation. Sustained-DPS scoring still needs the actual trigger event, cooldown history, bar state, source persistence, target state, and timing before the effect contributes damage or power.

### 2026-09-21 — Named buffs fit CombatState; generic timed gear stats need another bridge

Canonical named buffs such as **Major Courage** can travel through the shared runtime `CombatState` and naturally change the exact calculation context used by sustained-DPS simulation. A verified timed effect such as a temporary raw Weapon/Spell Damage window is different: it is represented as a generic `EffectVariant`, not a named buff. Until that timed effect is explicitly applied when rebuilding the runtime calculation context, FoundryDock must fail closed rather than silently drop it or pretend its uptime is static.

### 2026-09-21 — A timed proc belongs in the exact stat snapshot, not the standing sheet

A temporary raw Weapon/Spell Damage proc is neither a permanent build stat nor merely a label saying the proc happened. Once the shared runtime timeline proves that its window is active, FoundryDock now projects the reviewed `weapon_spell_damage` identity into canonical Weapon Damage and Spell Damage inputs **for that exact runtime instant only**. When the window expires, the contribution disappears from later snapshots automatically.

### 2026-09-21 — Potion recipes can differ while the combat effect family is identical

Different reagent combinations can produce the same exact canonical Alchemy trait set. For sustained-DPS search, those recipes are mechanically equivalent selections, so FoundryDock now keeps one effect-family candidate instead of multiplying the search denominator by reagent permutations. The selected family still proves availability only; actual use, cooldown, duration, and **Medicinal Use** remain temporal runtime facts.

### 2026-09-21 — Passive rank search must not invent skill-line ownership

A passive having a useful max rank in the database does not prove a generated character can own that line. Native class lines come from the candidate class, while guild, weapon, armor, Alliance War, Vampire/Werewolf, and other shared lines require separate ownership evidence. FoundryDock therefore searches ranks only inside already-legal line ownership and leaves line acquisition to the appropriate structural axis.

### 2026-09-21 — A skill family is unique per bar; a bar position is not a DPS mechanic

ESO lets a character put the same ability family on both weapon bars, but one bar cannot simultaneously slot the base skill and one or both of its morphs as separate abilities. FoundryDock therefore treats `base_ability_id` as the per-bar family identity while preserving the base skill and morphs as separate selectable alternatives. The five ordinary slot positions themselves do not change the build's mechanics, so generated search keeps one canonical ordering instead of multiplying equivalent bars by slot permutations. The Ultimate remains a distinct sixth slot.

### 2026-09-21 — An empty skill slot is legal until dominance proves it unnecessary

A theoretical build denominator cannot assume all five normal slots and the Ultimate must be filled merely because optimized players usually fill them. Generated sustained-DPS search therefore retains empty and partial bar states. Later proof-safe dominance may discard them when a filled alternative is proven no worse, but legality and optimization remain separate questions.

### 2026-09-21 — Equipped, owned, and native skill lines are different facts

A generated character may natively own class-route lines, explicitly own shared lines through progression, and temporarily have different weapon/armor lines made relevant by the equipment it is actually wearing. Those are not interchangeable facts. FoundryDock now carries them separately into skill-bar legality so an equipped Inferno Staff does not magically become Fighters Guild ownership, and a legal subclass line is not rejected merely because it belongs to a different base class.

### 2026-09-21 — Cross-axis optimization must assemble state, not swap whole candidate snapshots

Each generated frontier creates a convenient local snapshot while exploring its own axis. Combining the “best” snapshots wholesale can silently erase another axis's gear, class route, potion, CP, or skills. FoundryDock therefore assembles a final generated candidate by copying **only** the state owned by each selected axis onto one cross-axis-authoritative build.

### 2026-09-21 — The same skill bar can produce different finite-horizon rotations

A bar tells FoundryDock **which** skills are available, not the order in which they are cast. Over a finite fight, changing the ordinary-skill order or starting on the other weapon bar can move DoTs, buffs, executes, and proc windows earlier or later enough to change total damage before the target dies. Generated sustained-DPS search therefore preserves ordinary-skill order and legal starting-bar route as rotation coordinates rather than treating saved slot order as combat truth.

### 2026-09-21 — Light-Attack weaving is a rotation choice, not a bar-legality fact

A legal build can exist with or without weaving Light Attacks between skills. Endgame DPS normally weaves, but theoretical search must not erase the non-weaving state merely because it is usually worse. The generated rotation family therefore preserves both states until exact simulation or a proof-safe dominance rule removes one.

### 2026-09-21 — Potion cooldown does not uniquely determine first-use timing

Knowing that a potion can be reused every 45 seconds does not tell the optimizer when the first potion was used. A first use at 0 seconds and one at 8 seconds produce different buff/resource windows even though both obey the same cooldown afterward. FoundryDock therefore keeps first-use timing as policy evidence rather than equating “on cooldown” with “starts at zero.” The current generated frontier preserves a finite anchored family; arbitrary continuous first-use offsets remain explicitly open.

### 2026-09-21 — “Ultimate is affordable” and “cast Ultimate now” are different policies

Canonical Ultimate generation can prove the first times a slotted Ultimate becomes affordable, but a player may deliberately hold it for a burst window, execute, add phase, or mechanic. The current generated sustained-DPS policy frontier can evaluate explicit bar choice with the canonical as-soon-as-affordable scheduler. Deliberately delayed casts remain a separate policy axis rather than being silently erased.

### 2026-09-21 — Generic DD projection and dedicated Heavy Attack damage are different authorities

The generic scheduled DD action projector still marks Light and Heavy Attacks unresolved because it owns skill/Ultimate component projection, not weapon-attack formulas. Fully charged Heavy Attacks **do** have a separate canonical evaluator with reviewed UESP-translated weapon formulas, active-bar weapon reconstruction, completion/full-charge evidence, crit, mitigation, target Damage Taken, and relevant runtime state. Generated search must therefore route Heavy Attacks through that dedicated evaluator rather than reading the generic projector's unresolved result as “Heavy Attack damage is unknown everywhere.”

### 2026-09-21 — A Heavy Attack action is not proof of a fully charged Heavy Attack

FoundryDock only promotes a generated Heavy Attack to full-charge evidence when the plan carries an exact reviewed **1.8-second** reservation for that action and bar. Merely changing an action kind to `HEAVY_ATTACK` is insufficient. The channel must fit the plan timeline, avoid conflicting actions, and produce the canonical completion evidence consumed by Heavy Attack damage/restoration services.

### 2026-09-21 — A proven maximum does not require a unique winning build

If every remaining generated branch is either evaluated exactly or pruned by a proven-safe ceiling, FoundryDock can prove the maximum sustained DPS even when two or more candidates tie at that value. “Maximum proven” and “unique leader proven” are therefore separate search facts. Equal-to-incumbent upper bounds stay open until exact evaluation so a tied candidate can never be pruned away merely because another candidate reached the same score first.

### 2026-09-21 — Missing upper bounds make search slower, not permission to guess

Branch-and-bound remains correct when a branch has no pruning-safe optimistic ceiling: that branch is simply **forced open** and must be refined or exactly evaluated. FoundryDock never substitutes a heuristic estimate for a proof-safe bound just to improve search speed. Better bounds are an optimization feature; correctness does not depend on pretending they already exist.

### 2026-09-21 — Independent upper bounds intersect; they do not add

Two optimistic ceilings for the same partial build branch may overlap in what they already account for. Adding them can double-count the same future damage and produce nonsense. If each source independently proves that the branch cannot exceed its own ceiling, the safe combined ceiling is simply the **minimum** of those values. A child branch is a subset of its parent branch, so any proven parent ceiling remains valid after refinement and may be tightened by new child-specific evidence.

### 2026-09-21 — Action count can bound DPS without pretending to know the winning build

If a generated branch proves that no descendant can schedule more than **N** damage-bearing actions over a fixed horizon, and a separate authority proves that any one such action can contribute at most **D** total damage including its direct, periodic, and triggered consequences, then the whole branch cannot exceed **N × D / duration** sustained DPS. This is safe structural arithmetic. It does not require guessing the winning gear, skill, crit outcome, proc uptime, or action rate; those facts must already be covered by the two input proofs.

### 2026-09-21 — Missing pruning evidence is not missing damage evidence

An optimistic upper bound is a shortcut that lets the optimizer skip a branch proven unable to win. If that shortcut is unavailable, FoundryDock must open the branch—but once the candidate is fully simulated with complete damage evidence, the missing shortcut no longer makes the result uncertain.

**Layman's version:** not knowing the safe answer without doing the work means “do the work,” not “the answer can never be known.”

### 2026-09-21 — Skill order can change damage without changing the semi-static action count

Within FoundryDock's generated semi-static seed family, permuting the ordinary skills changes **which** ability lands on each skill step but not the repeating step-kind pattern itself. Over the same horizon and starting route, the number of skill steps is therefore invariant under ordinary-skill permutation. Light-Attack weaving changes the damage-action count, so the weave-on state is included when proving the family maximum. Later Ultimate insertion is different because it can add a new damage action rather than replace an existing skill step.

### 2026-09-21 — Ultimate affordability count is a capacity bound, not a cast schedule

For one selected Ultimate with a resolved cost and explicit generation timeline, the canonical Ultimate resource projector repeatedly reserves that cost whenever the shared pool can afford another activation. The resulting availability count therefore bounds how many Ultimate damage actions that policy could possibly add over the horizon. It does **not** prove every available cast is actually scheduled, tactically desirable, or damage-optimal; it is a safe capacity ceiling for search.

### 2026-09-21 — A local action maximum is only a ceiling for the denominator that proved it

If FoundryDock completely evaluates every descendant inside one partial branch and the largest total consequence of any one damage action is **X**, then **X** is a safe absolute per-action ceiling for that closed branch. It is not automatically a ceiling for its parent, sibling branches, or the global ESO search space. The proof travels downward to subsets, not outward to candidates that were never included in the denominator.

### 2026-09-21 — Lazy frontier traversal does not shrink the build denominator

A search does not need to create every possible build in memory at once to remain exhaustive. If each frontier reports its complete count and can materialize any indexed candidate, branch-and-bound can open one coordinate at a time while preserving the same legal denominator.

**Layman's version:** checking every drawer one at a time is still checking the whole cabinet; it simply avoids dumping the cabinet onto the floor.

### 2026-09-21 — Dominating an axis and bounding its damage are different proofs

Proving that a search branch has fully accounted for an axis such as Champion Points or Mundus does **not** by itself prove how much damage that axis can add. FoundryDock now tracks axis coverage separately from numeric optimistic damage. Coverage proofs may be unioned across independent authorities; the action-bound layer still requires its own safe multiplier or absolute ceiling before pruning can use that coverage.

### 2026-09-21 — Late search axes must meet before they alter one build

Champion Points, potion choice, passive ranks, and skill bars each arrive with a convenient candidate snapshot, but those snapshots were created from different baselines. Applying each whole snapshot in sequence can erase an earlier choice, so FoundryDock keeps the selections separate and assembles only their owned fields after all four coordinates are known.

**Layman's version:** four people can edit four sections of the same form, but passing around four complete photocopies means the last photocopy wins.

### 2026-09-21 — A coupled dominance proof should stay coupled when promoted

The reviewed Mundus × provisioning search proves a ceiling over the **joint pair**, not two unrelated one-axis optima. FoundryDock therefore promotes that result as one coupled proof covering both canonical axes together. If even one Mundus/food combination remains unresolved, neither axis is marked dominated and no numeric ceiling is promoted.

### 2026-09-21 — Trait search starts after the physical two-bar build exists

Armor, jewelry, and weapon traits or glyphs belong to actual equipped slots. FoundryDock therefore closes front/back set compatibility and materializes the physical gear state first, then searches those slot-level choices on the same evolving build.

**Layman's version:** choose which boots exist before arguing about the enchantment on the boots.

### 2026-09-21 — Wiring a finite policy family does not widen its proof

Connecting an anchored Ultimate/potion frontier to the generated branch-and-bound tree proves that every member of that **anchored family** can be reached and evaluated. It does not prove that arbitrary continuous potion offsets, deliberately delayed Ultimates, execute substitutions, or Heavy Attack windows were included. FoundryDock therefore carries the frontier's original proof boundary through the adapter instead of treating successful wiring as theoretical rotation closure.

**Layman's version:** putting every item from one shelf onto a checklist does not prove the whole warehouse was searched.

### 2026-09-21 — Enumerating every legal state does not tell us how much damage that axis can add

A complete dual-bar gear denominator, Champion Point denominator, or passive-rank denominator proves that FoundryDock has represented those legal choices. It does **not** automatically turn any one observed action into an upper bound across those choices. Structural coverage and numeric damage dominance remain separate proofs; a finite action search or another reviewed bound authority must still close the damage side.

### 2026-09-21 — A downstream policy denominator can depend on the upstream mutation

A reviewed Heavy Attack window names an exact scheduled ordinary-skill slot. An execute policy may first change the skill occupying that slot while preserving its time and sequence, and other policy mutations could make the window incompatible altogether. FoundryDock therefore rebuilds the Heavy Attack frontier for each selected execute candidate instead of counting one global Heavy Attack family and blindly multiplying it across every upstream plan.

**Layman's version:** after changing the schedule, recheck which appointment slots are still valid.

### 2026-09-21 — Axis lists compose only when their state transitions compose

Two generated frontiers may each expose a valid indexed axis, yet their axis tuples cannot be concatenated if the downstream frontier expects a different state type. The completed gear state must yield the cross-axis context, the completed late state must yield the assembled build, and the completed rotation state must yield the selected policy plan. FoundryDock now makes those transitions explicit and clears downstream selections whenever an upstream coordinate changes.

**Layman's version:** a relay team needs handoffs, not merely four runners listed on the same sheet.

### 2026-09-21 — Exact evaluation must use the last policy-mutated plan

The anchored Ultimate/potion plan is not necessarily the plan that reaches simulation. Execute policy may replace filler skills, and Heavy Attack policy may then replace exact scheduled skill slots and remove same-timestamp Light Attacks. FoundryDock therefore evaluates the final downstream generated candidate rather than accidentally scoring the earlier anchored plan while labeling it with later policy coordinates.

**Layman's version:** score the final edited schedule, not the draft from two edits ago.

### 2026-09-21 — Rematerializing set identity must not erase later weapon choices

The named-gear witness owns the selected weapon slots' set names and weapon types. Weapon trait, enchant, quality, tier, and level belong to later generated axes. Exact runtime setup may reapply the physical front/back set witness for activation evidence, so replacing the entire weapon slot at that point silently discards those later choices. FoundryDock now updates only the fields owned by named-gear materialization and preserves the downstream weapon refinement.

**Layman's version:** relabeling the weapon rack should not strip the enchantment off the weapon.

### 2026-09-21 — Finite-axis dominance only works when the compared action stays the same action

When FoundryDock varies CP, passive ranks, gear, or another finite axis to bound one scheduled action, every candidate must resolve the **same timestamp/sequence action coordinate**. If changing the axis changes which scheduled action is being measured, those numbers are not one comparable dominance grid. Coordinate drift therefore blocks both axis-coverage promotion and the numeric action ceiling.

### 2026-09-21 — A finite proof denominator does not have to be materialized all at once

A search space can be finite and fully indexed without building every candidate object in memory. FoundryDock's CP, passive-rank, and dual-bar gear dominance adapters now expose deterministic `choice_at(index)` access and evaluate one candidate at a time. This preserves denominator proof while avoiding an eager Cartesian allocation that would defeat the purpose of branch-and-bound.

### 2026-09-21 — Generated choices can reuse saved-build damage authority without becoming saved builds

A generated CP, passive-rank, or dual-bar gear candidate does not need its own damage formula stack. FoundryDock can adapt that explicit mutation onto a fixed build/progression witness and ask the canonical Combat Simulation DD provider for the exact scheduled action consequence. The generated candidate remains generated; only the already-reviewed damage authority is reused. If that provider cannot resolve runtime set behavior, periodic timing, weapon math, or another mechanic, the finite-axis dominance branch stays open.

### 2026-09-21 — A convenience search should not become a second mechanics authority

FoundryDock now has reusable CP, passive-rank, and dual-bar gear dominance searches, but those wrappers do not own any new ESO mechanics. The original frontier services still define legal choices, the canonical DD provider still owns action damage, and the finite-axis dominance engine still owns proof promotion. The wrapper only connects those authorities so callers cannot accidentally wire them differently.

### 2026-09-21 — A finite policy family can be closed while the timing continuum remains open

FoundryDock can completely enumerate the anchored potion policies generated from seed-plan timestamps and still **not** have proved every possible first-use offset between those timestamps. The same distinction applies to Ultimate use: canonical affordability can close the explicit bar-choice family without proving every deliberate post-affordability delay. Structural policy coverage therefore records finite-family closure separately from theoretical timing closure.

### 2026-09-21 — When the action changes, compare the whole plan instead of pretending the action did not change

Skill-bar, rotation-order, execute, and Heavy Attack policies can legitimately change which action occurs at a given timeline coordinate. Those variants should not be forced into an action-level dominance grid. If the finite family is closed, FoundryDock can instead compare complete modeled sustained DPS over the same exact horizon and use the largest whole-plan score as the family ceiling.

### 2026-09-21 — Dynamic plan comparisons should vary the plan, not quietly vary the build underneath it

When FoundryDock compares rotation-order, weave, execute, Ultimate, potion, or Heavy Attack policy variants, the build, explicit progression, dual-bar gear state, runtime history, target Health/resistance, and horizon must stay fixed unless those are intentionally part of the searched axis set. Otherwise a supposed rotation-policy ceiling is partly a build comparison and no longer proves what its label claims.

### 2026-09-21 — A dynamic family adapter must carry its omissions with it

Turning a rotation or policy frontier into a lazy indexed search source must not strip away what that frontier explicitly does **not** cover. Anchored potion timing still omits continuous first-use offsets, explicit Ultimate policy still omits arbitrary delayed casts, and reviewed Heavy Attack windows still omit unreviewed windows. FoundryDock carries those omissions alongside the finite denominator so branch-and-bound cannot mistake searchable scope for theoretical closure.

### 2026-09-21 — A closed runtime family is local proof, not proof that every runtime timeline has been imagined

A caller may be able to prove a finite runtime-state family complete for one branch, such as a reviewed set of proc/cooldown/condition states under fixed encounter assumptions. That can safely close the canonical `runtime_state` axis **for that branch**. It does not prove that ESO has no other legal runtime histories. FoundryDock therefore keeps omitted runtime scope attached to the family instead of silently upgrading local closure into a global runtime theorem.

### 2026-09-21 — A local ceiling is only a branch ceiling when the branch really is that local family

A maximum over a closed finite rotation/runtime family is safe only for that exact family. Before branch-and-bound can use it to prune, FoundryDock requires an explicit proof that the search branch contains exactly that denominator and that every omitted timing/encounter/runtime state is assigned outside the branch. This prevents a locally correct ceiling from becoming globally incorrect simply because the number is convenient.


### 2026-09-21 — Major Slayer support has two different raid-coverage patterns

War Machine and Master Architect provide Major Slayer to only part of a 12-player trial group at a time, so raid planning commonly uses **two providers total** in any combination of those two sets to cover the full group.

Roaring Opportunist behaves differently when paired with Jorvuld's Guidance: one player can maintain full-group Major Slayer coverage by performing the required Heavy Attacks on the set's cadence, so that pair replaces the two-provider War Machine / Master Architect route rather than supplementing it.

**Layman's version:** Major Slayer is not simply “covered” because one Slayer set exists. The raid either needs two partial-group providers, or one Roaring Opportunist + Jorvuld's provider doing the required Heavy Attacks.

**For BFF / Finch:** signup and comp tools should treat these as mutually exclusive coverage routes. Once RO + Jorvuld's is assigned, War Machine / Master Architect should no longer be offered for Slayer coverage; once the direct-set route is chosen, RO + Jorvuld's should no longer be offered as the alternate route.


## Potion restore timing and Phase 4 event priority

For canonical Phase 4 resource timelines, same-timestamp event ordering is:

1. resource maximum change
2. action cost
3. ordinary recovery tick
4. restoration event

This matters for Objective #32 potion timing. A potion's instant resource restore is a restoration event, so moving potion use across any resource-event timestamp can change shortfall, cap clipping, or wasted restoration even when the potion's named-buff state at damage events is unchanged. Continuous potion first-use timing therefore cannot be closed from DD observation times alone. The finite timing denominator must also include all modeled resource-timeline event timestamps, including ordinary 2-second recovery ticks, action coordinates, verified Heavy Attack completion restores, resource-maximum changes, and any other caller-proven restoration events.

**For BFF:** named-buff timing and resource-restoration timing share one continuous potion-use clock but have different state-change boundaries. A proof that closes only buff uptime is not a proof of the full potion timing axis.


## Heavy Attack channel reservation discovery

For the reviewed fully charged Heavy Attack model, the canonical channel reservation is **1.8 seconds**. A legal Heavy Attack start is not equivalent to finding an empty 1.8-second gap in the visible plan.

The soft-action duration scheduler may reserve a 1.8s channel over ordinary same-bar skill decisions. Those covered skills are displaced and cascade into later same-bar slots. First casts and due refresh obligations remain protected, and the channel may not cross the plan horizon or the next hard timeline boundary such as a bar swap or an action on another bar.

**For Objective #32:** complete Heavy Attack timing discovery must probe each scheduled ordinary skill slot through the canonical soft-action scheduler. A simplistic gap scan would incorrectly reject legal channels that displace same-bar skills. Encounter demand windows do not automatically mean “channel forbidden”; channel prohibitions require explicit reviewed channel-block evidence with a complete denominator proof.


## Runtime proc chance equivalence classes

For canonical runtime effect eligibility, a deterministic chance roll only matters when it crosses an EffectVariant's proc-chance threshold. For one fixed runtime event, every roll inside the same threshold interval produces the same chance eligibility decisions for all matching effects.

Example: if matching effects have proc chances 25% and 50%, the complete roll-state family does **not** require 101 samples from 0.00 to 1.00. The materially distinct representatives are:

- 0.00 for the region below 25%
- 0.25 for the region from 25% through just below 50%
- 0.50 for the region from 50% through just below 1.00

The eligibility rule treats `roll >= chance` as failure, so the exact threshold itself belongs to the failure side of that effect. A 100% effect does not introduce a breakpoint, and roll 1.0 is unnecessary.

**For Objective #32:** continuous numeric proc-roll evidence is therefore finite once the relevant canonical EffectVariant chance thresholds are known. This does not invent event timestamps, triggers, targets, or encounter conditions; those remain scenario evidence and need their own denominator proof.


## Expected-value critical damage is not a critical-hit event stream

The DD damage calculators can include critical chance/damage in an expected-value damage result without producing a concrete sampled combat history of which individual attacks critically hit.

That distinction matters for runtime proc triggers. A finalized damage occurrence may prove that `damage_dealt` happened at an exact time, but it does **not** prove that `critical_damage` happened unless a separate canonical mechanic records the actual crit outcome.

**For Objective #32:** runtime event skeleton generation may derive `damage_dealt` from exact occurrence evidence, but it must not manufacture critical-hit trigger events from expected-value crit math. Crit-triggered runtime effects remain scenario/event evidence until the damage model exposes deterministic crit outcomes or a separately proven finite crit-event family.


## 2026-09-22 — Weapon bars can contribute two set pieces in two different ways

While wiring Objective #32 runtime-effect discovery, BFF found that one saved-build capability path counted the main-hand weapon but ignored an explicit off-hand, and only recognized staves as two-piece weapons.

**Layman's version:** a five-piece set can become active because a two-handed weapon counts as two set pieces, or because two separate one-handed weapons each contribute one piece. A bow is also a two-piece set weapon. Looking only for “staff” misses real legal loadouts.

**What it means in actual play:** swapping to a dual-wield, sword-and-board, bow, or other two-handed bar can turn a set proc on or off just as decisively as swapping to a staff.

**For BFF:** runtime capability discovery now reuses the same canonical active-bar set counter as the static gear pipeline, including explicit off-hands, two-slot weapon families, and legacy Set/Set2 saves. This prevents Objective #32 from searching the wrong proc universe for a legal weapon bar.


## 2026-09-22 — Champion Points can be runtime procs, not just passive numbers

Objective #32’s effect-universe audit found that **From the Brink** is represented by a canonical triggered `EffectVariant`: healing a self or ally below 25% Health can create its damage shield, with its own duration and per-target cooldown.

**Layman's version:** not every Champion Point is a number that can be baked into the character sheet before combat starts. Some CP choices behave like proc mechanics and only exist when their trigger actually happens.

**What it means in actual play:** two otherwise identical rotations can have different runtime state because a CP trigger occurred in one scenario and not the other.

**For BFF:** generated CP choices must participate in runtime-effect discovery whenever their canonical CP resolver produces a triggered effect. Treating all CP as static would let the theoretical search silently omit legal runtime mechanics.


## 2026-09-22 — A real proc does not automatically belong in a DPS search

While closing Objective #32 runtime state, BFF hit an important distinction: **From the Brink** is a real triggered Champion Point proc, but its canonical result is a damage shield. The proc matters mechanically, yet the shield does not change the current sustained-DPS calculation.

**Layman's version:** “this thing can proc” and “this thing can change my damage” are two different questions. If the optimizer treats every combat proc as a DPS branch, defensive mechanics can multiply the search tree without changing the score at all.

**What it means in actual play:** a defensive shield proc can be very important for surviving a fight while still being irrelevant to the narrow question “what is the maximum sustained damage this build can produce?”

**For BFF:** Objective #32 now removes a runtime effect only when canonical semantics prove it cannot affect the DPS objective. Unknown effects are not discarded. Enemy-side damage modifiers such as Vulnerability also remain open until the target-side runtime projection is modeled, because being obviously damage-related is not the same as being correctly wired into the evaluator.


## 2026-09-22 — Vulnerability belongs to the target, not the attacker

Objective #32 already had the correct static damage-stage ordering: attacker Damage Done is resolved first, then mitigation, then target Damage Taken. Major and Minor Vulnerability therefore must enter through the enemy's runtime combat state rather than being flattened into the DD's own buffs or sheet stats.

**Layman's version:** Berserk says “I hit harder.” Vulnerability says “that target takes more damage.” Those sound similar on a dummy parse, but they are not the same math bucket.

**For BFF:** runtime-state witnesses now retain their canonical EffectVariant metadata. At each exact damage timestamp, ENEMY-target Vulnerability windows are replayed against the named target and projected into the existing target Damage Taken router. The target identity must match and the effect must still be active at that instant; a debuff on an add cannot leak onto the boss, and an expired window contributes nothing.


## 2026-09-22 — Breach belongs in resistance, not Damage Taken

Major Breach reduces the target's Physical and Spell Resistance by 5948; Minor Breach reduces them by 2974. These are additive resistance reductions, not generic Damage Taken modifiers.

**For BFF:** Objective #32 now replays active ENEMY-target Breach windows at the exact damage timestamp and lowers the explicit target resistance before mitigation. Major and Minor Breach may both contribute; the resulting resistance is clamped at zero so over-reduction never becomes bonus damage. Vulnerability remains a later, separate Damage Taken bucket.


## 2026-09-22 — Brittle joins Critical Damage before the cap

Minor Brittle increases the target's Critical Damage Taken by 10 percentage points; Major Brittle increases it by 20. The project's U50 critical-damage references group Brittle with the other Critical Damage modifiers that contribute toward the 125% hard cap.

**For BFF:** Objective #32 now adds exact-time ENEMY-target Brittle to the attacker's raw Critical Damage, caps the combined value at 125%, and only then applies target Critical Resistance. Brittle therefore has no extra value once the combined critical bonus is already capped, and it remains separate from generic Damage Taken and target resistance.


## 2026-09-22 — Fixed target reductions and scaling target reductions are different evidence classes

A runtime debuff with an explicitly resolved numeric resistance reduction can be applied directly to exact-time target resistance. A tooltip or known-effect record that says a value scales "up to" a maximum does not prove the runtime magnitude is that maximum.

**For BFF:** EffectVariant now preserves explicit target mechanic metadata. Objective #32 admits fixed ENEMY resistance reductions only when the numeric value is resolved and no unresolved scaling formula remains. Scaling effects such as Roar of Alkosh stay fail-closed until their actual magnitude resolver is authoritative. This prevents maximum tooltip values from being silently treated as permanent combat truth.


## 2026-09-22 — Unique Damage Taken can share the bucket without sharing the name

A target can have named Vulnerability and a separate unique damage-amplification debuff at the same time. Those effects belong to the same additive target Damage Taken stage even though only one is a named Major/Minor effect.

**For BFF:** exact-time CombatState now carries explicit numeric Damage Taken in addition to canonical named buffs. Fixed ENEMY-target amplification can therefore stack with Vulnerability through the existing Damage Taken router. A named effect that also carries matching numeric metadata is counted only once, while any amplification with unresolved scaling remains fail-closed.


## 2026-09-22 — Crusher magnitude and Crusher uptime are separate proofs

The weapon-enchantment repository and rule engine can resolve Crusher's target resistance reduction, duration, and trait-adjusted magnitude. That does not by itself prove the trigger/cooldown timeline needed to model exact combat uptime.

**For BFF:** saved-build capability resolution now exposes Crusher as a bar-owned ENEMY resistance-reduction EffectVariant using canonical enchantment data. Objective #32 still treats its runtime effect timing as deferred, so the effect is visible in capability audits but cannot silently enter sustained-DPS runtime search until application cadence is authoritative.


## 2026-09-22 — Cooldown modifiers do not prove a base cooldown

The repo has canonical rules that can modify a weapon enchantment cooldown once a base cooldown is supplied. That is not evidence for what the base cooldown is, what event triggers the enchantment, or how source/bar persistence behaves.

**For BFF:** weapon-enchantment runtime cadence is now a dedicated decision-critical mechanics gap for Rotation Maker and Optimizer. Crusher magnitude/duration may be audited from canonical enchantment data, but Objective #32 must not schedule it until trigger semantics, base proc cooldown, source persistence, and relevant lockout/shared-cooldown behavior are authoritative.


## 2026-09-22 — Missing evidence and missing math are different blockers

A runtime effect can fail sustained-DPS closure because the game evidence is incomplete (for example target classification or scaling) or because the identity is known but BFF lacks a reviewed objective-specific math disposition. Those are different engineering jobs.

**For BFF:** Objective #32 runtime relevance now reports source-data blockers separately from math/review blockers while retaining the same fail-closed unresolved output. This makes closure audits actionable without weakening correctness.


## 2026-09-22 — A complete search tree is not a complete combat model

Proving the maximum over every branch in a generated finite tree proves only that tree. If a relevant combat mechanic is missing, partially modeled, or lacks source/math review, the theoretical ESO-wide objective is still open even when every represented mutation axis is covered.

**For BFF:** Objective #32 now carries a closure inventory that separates runtime source-data debt, runtime math/review debt, critical mechanics gaps, and partial mechanics coverage. The theoretical maximum gate can consume that inventory, and the canonical blocker report explains the same debt rather than allowing finite-search completion to masquerade as a fully closed combat model.


## 2026-09-22 — Master Architect duration belongs to the Ultimate spend

Master Architect's Major Slayer duration is not a fixed one-second proc. The reviewed set semantics are one second of Major Slayer per 10 Ultimate spent, so the runtime duration is candidate-specific.

**For BFF:** Objective #32 now resolves that duration from canonical Ultimate spend before runtime relevance and event enumeration. A 250-cost Ultimate produces 25 seconds. A branch with no scheduled Ultimate has no operative duration requirement, while mixed or unresolved Ultimate-cost evidence fails closed rather than silently using the registry's one-second base unit.


---

## 2026-09-22 — Weapon enchantments remember identity across bars

Weapon-enchantment cooldown research exposes a topology that is easy to model incorrectly. Community tests consistently report that two copies of the **same enchantment identity** share a cooldown even when they are on different bars, while different enchantment identities can keep independent timers. Ground weapon DoTs such as Wall of Elements or Volley can continue triggering the enchantment belonging to the weapon that created the ground effect after the player swaps bars.

The same evidence converges on a roughly **4-second base cooldown for direct-damage enchantments** and **10 seconds for buff/debuff enchantments** before modifiers such as Infused. Those values remain provisional in BFF until current-version authoritative evidence is available.

**Layman's version:** swapping weapons does not erase where an existing ground weapon effect came from, and putting the same glyph on both bars does not give you two independent copies of its timer.

**For BFF:** weapon-enchantment cadence needs source-weapon ownership and enchantment identity, not merely the currently active bar. The optimizer must also keep provisional cadence evidence out of exact simulation until the evidence authority gate is satisfied.


## 2026-09-22 — Update 35 standardized heavy-attack resource returns

**Evidence:** Official ESO Update 35 / Lost Depths patch notes standardized fully charged heavy-attack restoration by weapon family. Canonical bases now include Bow 2772 Stamina, Dual Wield 2095 Stamina, Two Handed 2425 Stamina, One Hand and Shield 2293 Stamina, Inferno/Frost Staff 2838 Magicka, Lightning Staff 2970 Magicka, Restoration Staff 2970 Magicka, and Unarmed 2095 Stamina. Werewolf remains fail-closed pending separate current evidence.

**Mechanical boundary:** A scheduled heavy is not automatically a resource event. ESO's official combat history explicitly ties restoration to a fully charged heavy that successfully lands; blocked or dodged fully charged heavies do not restore resources. BFF therefore keeps completion and hit-state evidence separate from the weapon's base restore value.

**Layman summary:** Knowing the weapon tells us how much a successful full heavy can restore. It does not prove the heavy actually earned the restore. ESO has, naturally, supplied both a number and paperwork.

**BFF implication:** The optimizer can now use authoritative base restoration for every standard weapon family instead of failing closed on most weapons, while still refusing to invent Werewolf values or successful-completion state.

## 2026-09-22 — Heavy completion and landed-hit evidence are separate facts

ESO Logs can provide a positive damage observation for a reviewed Heavy Attack alias. BFF now treats that row as evidence that the attack landed only when it correlates one-to-one with the reviewed completion timestamp after explicit replay-clock alignment. ESO Logs event timestamps are millisecond report/fight timestamps while RotationPlan completion timestamps are replay-relative seconds. A completed channel alone does not prove a hit, and absence of a matching damage row does not prove a miss because log/alias evidence can be incomplete. Ambiguous multiple matches remain unresolved.

**BFF implication:** Heavy Attack damage and resource restoration share the same explicit landed-state evidence. Scheduler reservations establish completion; encounter/log evidence establishes a successful hit. The optimizer fails closed when those facts cannot be joined unambiguously.

## 2026-09-22 — Heavy Attack modifiers need patch-era provenance

Official ESO forum patch-note history confirms that Heavy Armor Revitalize changed from a flat 12/25% model to 2/4% per equipped Heavy Armor piece. Historical official discussion also records Restoration Staff Cycle of Life at 15/30% additional Magicka from completed heavy attacks. These values are already represented by the current progression modifier service, but the evidence spans different patch eras and therefore must not be treated as proof that every current modifier is unchanged.

**BFF implication:** keep Revitalize and Cycle of Life behind explicit saved progression ranks and retain the remaining closure gap for current modifier completeness. Historical evidence can validate provenance, not silently certify the entire 2026 modifier catalog.


## 2026-09-22 — Restoration Staff base versus observed 4247 return

The reviewed heavy-attack reference table groups Lightning and Restoration Staff at a 2970 Magicka base. Existing ESO Logs evidence also contains an observed unclipped Restoration Staff return of 4247. That observation does **not** justify changing the canonical base to 3267: 2970 × the reviewed 30% Cycle of Life modifier is 3861, so the remaining difference proves that additional actor/runtime modifier evidence is present or still unidentified. The engine therefore keeps the canonical weapon base at 2970 and treats the 4247 observation as modifier-discovery evidence rather than a base-value oracle.


## 2026-09-22 — Historical heavy-restoration formula exposes unresolved runtime axes

The repository's older ESO math reference gives the heavy-resource formula as `(Base × (1 + restoration amplifiers) + flat bonuses) × block reduction`. It names Tenacity, Revitalize, Ulfnor's Favor, Off Balance, Rampaging Slash, and Arch-Mage as examples, and records a 50% restoration reduction when the target blocks. Its weapon bases are from an older ruleset and differ from the reviewed Update 35 table, so these modifier statements are discovery evidence rather than current executable constants. This explains why an observed 4247 Restoration Staff return can exceed the current 2970 base plus Cycle of Life without requiring a fake weapon base. The Extreme Engine must resolve current ownership/values for these axes before theoretical closure.

## 2026-09-23 — Shared Heavy Attack uncertainty is still uncertainty

A ranking comparison can give every candidate the same unresolved Heavy Attack restoration or hit-state evidence. That does not make the resource timeline trustworthy; it only makes the uncertainty common to every candidate.

**Layman's version:** if every build is missing the same receipt, none of them suddenly has proof. A Heavy Attack that may or may not have completed, landed, or restored resources can change sustain and therefore change which rotation is actually viable.

**For BFF:** shared Heavy Attack completion, landed-hit state, and restoration uncertainty now blocks candidate eligibility just like shared potion timeline uncertainty. Cosmetic Heavy Attack metadata remains advisory.



## 2026-09-23 — Weapon passive ownership is not enough; subtype matters

Several weapon-line passives are standing effects, but their math still depends on the exact weapon subtype on the active bar. The reviewed U50 data gives **Twin Blade and Blunt** +64 Weapon/Spell Damage for each equipped sword and **Heavy Weapons** +129 Weapon/Spell Damage for a greatsword. Other Twin Blade / Heavy Weapons branches use different mechanics, and Ambidextrous derives power from the off-hand weapon rather than adding the same flat number.

**Layman's version:** owning the passive does not mean “add weapon damage.” A sword, dagger, axe, mace, greatsword, battle axe, and maul can send the same passive down different math paths. ESO has once again chosen a dropdown menu where a number would have been less theatrical.

**For BFF:** Phase 5 now applies only the reviewed sword/greatsword standing branches when exact passive ownership and weapon subtype are known. Ambidextrous is now resolved at max rank as 6% of verified off-hand weapon damage; dagger/mace standing branches are also modeled from current-live rank-2 values, while axe Critical Damage branches remain unresolved pending refreshed proof.


## 2026-09-23 — Ambidextrous uses the off-hand weapon's own damage

The corrected max-rank **Ambidextrous** evidence is 6% of the off-hand weapon's damage. The earlier 3% value is Rank 1, not Rank 2. The existing weapon-passive audit already treats that as a derived flat sheet-power contribution, separate from Twin Blade and Blunt and separate from Nirnhoned's own item-power contribution.

**Layman's version:** Ambidextrous is not “+3% Weapon Damage.” It asks what the off-hand weapon itself is worth, then takes 3% of that number. Naturally, the wording contains just enough similarity to a global percentage bonus to make careless code look plausible.

**For BFF:** Phase 5 resolves Ambidextrous only when the active bar is explicit Dual Wield and the off-hand has verified CP160 Gold weapon power. Unknown level/quality or unknown off-hand power remains unresolved and blocks Objective #32 closure.

## 2026-09-23 — Bow Accuracy is active-bar Critical Chance rating

Current ESO-Hub and UESP build-data records agree that max-rank **Accuracy** grants **1314 Critical Chance rating** while a Bow is equipped.

**Layman's version:** owning Accuracy does not give permanent crit just because a Bow exists somewhere on the character. The Bow must be the weapon currently in use.

**For BFF:** Accuracy is routed through the same critical-rating conversion used by other canonical rating sources and is applied only when the active bar is a Bow. This keeps front/back static snapshots mechanically distinct.


## 2026-09-23 — Max rank can be mislabeled when rank evidence is stale

During Objective #32 weapon-passive closure, the existing audit selected the highest skill_rank row but still surfaced **Rank 1 magnitudes** for several passives: Twin Blade and Blunt sword 64, Heavy Weapons sword 129, and Ambidextrous 3%. Official Update 39 rank pairs and UESP rank-specific build records show those are the lower-rank values; the corresponding Rank 2 values are 129, 258, and 6%.

**Layman's version:** “highest row” and “highest-rank tooltip” are not automatically the same fact if imported rank text is stale or misjoined. Databases, in their eternal quest for drama, can be structurally tidy and semantically wrong at the same time.

**For BFF:** weapon-passive audits now reject those Rank 1 values when claiming max-rank proof. More broadly, passive mechanics that depend on skill_rank.raw_description need rank-integrity checks before Objective #32 treats them as authoritative.


## 2026-09-23 — Two rank tooltips are not one proof

The skill data can carry both a rank-level raw description and an ability-level description for the same passive rank. If those two texts disagree, choosing whichever column happens to be first in a SQL COALESCE is not mechanics resolution; it is database roulette.

**Layman's version:** two labels saying different things about the same Rank 2 passive means we do not know which one is trustworthy yet. The fact that one of them parses beautifully does not make the argument disappear.

**For BFF:** exact-rank passive evidence now fails closed when raw rank text and the matching ability tooltip disagree. The global Extreme passive universe preserves that conflict, and static passive projection cannot score through it.


## 2026-09-23 — Shared missing action costs are not neutral

Rotation sustain can fail to resolve an ability base cost or a build-owned cost modifier. If baseline and candidate both inherit that gap, their resource timelines are still not trustworthy; equal ignorance does not turn an unknown spend into zero spend.

**Layman's version:** if we do not know what a skill costs, comparing two rotations that both cast it does not magically make the missing Magicka or Stamina irrelevant.

**For BFF:** shared unresolved action-cost rows and explicitly tagged action-cost-modifier evidence now block candidate eligibility. Display-only cost metadata remains advisory.


## 2026-09-23 — Axe passive history is contradictory enough to fail closed

Official Update 29 notes set Twin Blade and Blunt axes to 2/4% Critical Damage and Healing Done per axe and Heavy Weapons axes to 4/8%. Official Update 30 notes then stated that Twin Blade axes were changing to 3/6% Critical Damage per axe, while contemporaneous live reports disputed whether the new value actually took effect. Later Update 39 notes adjusted swords, daggers and maces but did not settle the axe implementation history.

**Layman's version:** the patch notes and observed live behavior argued with each other. That is not a license to pick the larger number because it looks modern.

**For BFF:** Dual Wield axe and Two Handed battle-axe Critical Damage branches remain unresolved for Objective #32 until current-live U50 evidence establishes the actual rank values and behavior cleanly.


---

## 2026-09-23 — Alkosh cares about Weapon Damage when the synergy fires

Roar of Alkosh does not simply carry one fixed resistance-reduction number baked into the set. Its current tooltip says the debuff reduces enemy Physical and Spell Resistance by the amount of the user's **Weapon Damage**, capped at **6000**, when the synergy proc is activated.

**Layman's version:** two people wearing Alkosh can produce different debuff strengths, and the same character can theoretically produce a different value if their Weapon Damage is different at the moment the synergy fires.

**What it means in actual play:** temporary Weapon Damage buffs can matter to the debuff magnitude at activation time. A resting character-sheet value is not automatically the correct number for every proc.

**For BFF:** Alkosh must not be resolved from static build state alone. Extreme Engine needs activation-time Weapon Damage evidence, or it must leave the proc scaling unresolved. The runtime-scaling layer now fails closed on any triggered EffectVariant scaling rule that has not been explicitly reviewed.


---

## 2026-09-23 — Weapon enchantments care about damage events, not merely button presses

ZOS's Update 20 patch notes explicitly state that weapon enchantments proc 100% of the time when they are off cooldown when a **Light Attack, Heavy Attack, or weapon ability deals damage**. For Dual Wield weapon abilities, either weapon can supply the enchantment and the game favors one whose enchantment is not cooling down.

**Layman's version:** casting a weapon skill is not, by itself, the proc event. The damage event is the important part. Dual Wield also has a source-selection rule instead of simply firing whichever hand a planner feels like assigning.

**What it means in actual play:** a missed, dodged, immune, or otherwise non-damaging attack cannot be treated as equivalent to a landed damaging event for enchant scheduling. Dual Wield cadence also needs both weapon cooldown states.

**For BFF:** the activation-cause family is now primary-source evidence and can be modeled independently from the still-open base-cooldown and off-bar persistence questions. Objective #32 should therefore keep cooldown math fail-closed without throwing away the activation topology we actually know.


---

## 2026-09-23 — Weapon enchant evidence is not one all-or-nothing rule

Two additional ZOS patch-note facts can be separated cleanly from the still-messy weapon-enchant cadence questions:

- ZOS used a **4-second normal cooldown** for a direct-damage weapon enchantment in its Update 21 one-handed enchant balance example.
- When a weapon set has a **poison equipped**, the weapon enchantment on that set is **suppressed**.

**Layman's version:** we can know exactly how one part works without pretending we know every part. Damage enchants have primary-source 4-second cooldown evidence; that does **not** prove Crusher's buff/debuff cooldown. And poisons do not politely take turns with a weapon glyph; they replace/suppress the enchantment for that weapon set.

**For BFF:** weapon-enchantment cadence evidence is now tracked field by field. Direct-damage cooldown, activation causes, and poison suppression can be authoritative while off-bar ownership, shared-cooldown identity, and buff/debuff cooldown remain unresolved. Objective #32 must use only the proven fields and keep the rest fail-closed.


---

## 2026-09-23 — One hit cannot fire two weapon enchantments

ZOS fixed a Dual Wield bug where both weapon enchantments could proc from one isolated damage instance. Their clarification matters: a multi-hit ability can still proc different enchantments on different hits, but **one individual damage occurrence gets at most one weapon enchantment**.

**Layman's version:** one smack, one glyph proc. If a skill hits several times, later hits can create new opportunities, but BFF must not let the same hit independently activate every eligible enchantment.

**For BFF:** the generic runtime system evaluates EffectVariants independently, so multiple weapon-enchantment variants sharing one activation event require an explicit source-selection layer. Until that exists, Objective #32 now fails closed instead of double-proccing enchantments.


---

## 2026-09-23 — Weapon enchantments remember which weapon launched the ability

ZOS clarified in Update 19 that an enchantment follows the **weapon that fired the activating ability**, even if the player swaps bars before the damage lands.

**Layman's version:** swapping bars does not magically reassign an in-flight bow shot or other weapon ability to the new weapon's glyph. The game remembers where the attack came from.

**What it means in actual play:** back-bar weapon abilities can carry their source weapon's enchantment logic forward after a swap. Runtime modeling therefore needs source-weapon provenance, not just “which bar is active when damage lands.”

**For BFF:** off-bar/source-weapon persistence is now primary-source proven. The remaining enchant cadence blockers are narrower: exact buff/debuff cooldown, cooldown-scope/shared-identity behavior, and explicit per-opportunity source selection.


---

## 2026-09-23 — Weapon-skill DoTs split into two enchantment behaviors

Weapon-enchantment activation cannot treat every damage tick from a weapon ability the same way. Reviewed component shape matters: **single-target Damage over Time ticks are excluded**, while direct weapon-skill hits and area Damage over Time occurrences remain eligible activation opportunities when the rest of the enchantment rules are satisfied.

**Layman's version:** “it dealt damage” is necessary, but not sufficient. A lingering single-target DoT tick does not get the same glyph-proc privilege as the direct hit or an eligible ground/AoE weapon effect. Naturally, ESO found room for a taxonomy lesson inside a weapon glyph.

**What it means in actual play:** two ticks owned by the same cast can have different enchantment eligibility depending on the coefficient/component that produced them.

**For BFF:** Objective #32 now classifies each exact damage occurrence from canonical per-coefficient DoT/AoE identity. Missing coefficient identity or incomplete component classification fails closed instead of guessing from timing, cast count, or skill name.


## 2026-09-23 — “No proc” is a real resolved outcome

A valid weapon-enchantment activation opportunity does not guarantee that an enchantment fires. Once source ownership is known, the cooldown-ready subset can be empty, which means the hit produces no weapon-enchantment proc even though the damage event itself was eligible to try.

**Layman's version:** an eligible hit is permission to check the glyph, not a promise that the glyph is ready. If both Dual Wield enchants are cooling down, nothing fires. ESO has graciously distinguished “you may knock” from “someone answers.”

**For BFF:** Objective #32 now represents exact source, finite source alternatives, and resolved no-proc as different states. Missing cooldown truth remains unresolved rather than being confused with a proven empty ready set.


## 2026-09-23 — Source ownership and cooldown readiness are separate facts

A weapon-enchantment damage event can have one unambiguous source weapon while the actual proc result is still unknown because that source's cooldown state has not been proven. Source selection answers **which glyph would be checked**; cooldown readiness answers **whether that glyph can fire now**.

**Layman's version:** knowing which door to knock on does not prove anyone is home. A single owned enchantment is not automatically an active proc if its timer is unknown.

**For BFF:** Objective #32 now keeps source ownership, cooldown-state proof, and proc occurrence distinct. The shared runtime attempt model also supports binding one activation attempt to one exact EffectVariant source so a resolved one-hit enchant selection cannot leak into every matching enchantment.
---

## 2026-09-23 — Knowing an enchant cooldown number is not enough to simulate its timer

The cooldown-policy resolver exposed a useful distinction: a trustworthy **4-second** direct-damage enchant cooldown still does not tell BFF whether two copies share one timer, whether different enchant identities use independent timers, or what exact identity owns that cooldown state.

**Layman's version:** knowing that a timer lasts four seconds is not the same thing as knowing which things are sharing that timer.

**For BFF:** cooldown duration and cooldown topology stay separate proof requirements. `EffectVariant.name` can become the timer identity only after the game rule saying same identities share that timer is authoritative.
---

## 2026-09-23 — One enchant proc can have more than one consequence

Some weapon enchantments produce more than one gameplay consequence from the same proc. A useful example is **Absorb Health**, whose imported canonical effect rows include both damage and Health restoration.

**Layman's version:** one glyph firing can do two things; that does not mean two glyphs fired.

**For BFF:** weapon-enchantment source selection and cooldown state are keyed by the shared enchant provenance, not by the number of consequence rows. One bound proc attempt may feed multiple consequence variants belonging to that one source.
---

## 2026-09-23 — One proc family can have several consequences

Weapon enchantments are easier to classify for cadence from the **source proc**, not from each output row. A glyph that deals damage and also restores Health is still one direct-damage enchant source; the restoration is another consequence of that same proc.

**Layman's version:** classify the thing that fired, not every thing it did afterward.

**For BFF:** cadence-family classification happens at the enchant-source level. Consequence rows stay separate for later damage/healing/resource/debuff projection, and family classification alone never proves cooldown duration or shared-timer behavior.

## 2026-09-23 — Ambidextrous can contribute a decimal internally even though Weapon Damage finishes as an integer

A CP160 Gold one-handed sword has reviewed base weapon power of **1335**. Max-rank Dual Wield **Ambidextrous** contributes **6% of the off-hand weapon's damage**, which is **80.1** in this case.

BFF therefore keeps the exact pre-rounding value in the calculation trace. If the rest of the build produces 1000 Weapon Damage before Ambidextrous, the raw result is **1080.1**. ESO's integer-facing derived-stat rounding then ceilings that to a final **1081**. In the full dual-sword Phase 5 example, **1909.1** similarly becomes **1910**.

**Layman's version:** a passive can add a fractional amount behind the scenes even though the character-sheet-style result is a whole number.

**For BFF:** preserve the decimal in `raw_value` for math/audit provenance, but use the rounded `final_value` anywhere the resolved integer-facing Weapon/Spell Damage stat is required.
---

## 2026-09-23 — Oblivion weapon-enchant damage is a documented crit exception

ZOS explicitly documented the Damage Health (Oblivion) weapon enchant as unable to critically strike. That gives BFF one authoritative crit rule for weapon-enchant damage, but it does **not** prove the opposite rule for every ordinary elemental or absorb glyph.

**Layman's version:** we know one glyph family definitely cannot crit; that does not automatically tell us how all the others crit.

**For BFF:** the direct-damage consequence bridge may use the existing Oblivion non-crit policy when the canonical damage type is Oblivion. Ordinary glyph critical eligibility and which critical-stat family applies remain separate proof requirements.



## 2026-09-23 — “Same glyphs share” and “different glyphs are independent” are different facts

Cooldown topology has two separate questions: whether duplicate enchant identities share one timer, and whether different enchant identities keep independent timers. Community testing strongly supports both, but one does not logically prove the other.

**Layman's version:** proving that two copies of Flame share a stopwatch does not automatically prove that Flame and Poison each get their own stopwatch. ESO mechanics, naturally, require us to audit the stopwatches.

**For BFF:** Objective #32 now gates these as separate authority fields. Exact weapon-enchantment sequence simulation cannot close until both duplicate-identity sharing and distinct-identity independence are authoritative.


## 2026-09-23 — A weapon glyph is not automatically a normal skill for critical-hit rules

The selected-proc bridge now reaches the point where a glyph's damage consequence can be handed to damage policy. ZOS gives us an explicit special rule for Damage Health (Oblivion): that weapon-enchantment damage cannot critically strike. We still do not have equivalent authority proving the ordinary elemental and absorb glyph families should simply inherit normal skill critical behavior.

**Layman's version:** a Flame glyph doing damage does not magically become a little fire skill just because both numbers hurt the boss.

**For BFF:** selected Oblivion glyph damage may resolve `can_crit=False`. Ordinary glyph damage keeps `can_crit=None` until its own authoritative rule is established, so final sustained-DPS application remains fail-closed instead of borrowing skill semantics.


## 2026-09-23 — Infused has two different enchantment jobs

Weapon **Infused** changes two separate things: enchantment **magnitude** and enchantment **cooldown**. FoundryDock's older rule path correctly found the quality-dependent magnitude row, but cooldown math was handed that same row; the cooldown calculator intentionally ignores magnitude rules, so an Infused weapon could keep the unmodified base cooldown.

**Layman's version:** making the glyph hit harder and making it fire sooner are two different switches. We had the first switch wired to both labels, which looked tidy and did absolutely nothing for the timer.

**For BFF:** weapon-enchantment runtime now uses the quality-aware Infused magnitude rule plus the separate canonical `enchantment_cooldown_reduction` rule. Gold/Legendary quality aliases are normalized before the magnitude lookup, and cooldown policy remains fail-closed if the canonical cooldown rule is missing or ambiguous.


## 2026-09-23 — A glyph firing is not the same as its consequence being scored

The runtime sequence can prove exactly which weapon enchantment fired and when, but that only resolves the **proc source**. The selected glyph may still deal damage, restore a resource or Health, apply a shield, or apply a buff/debuff, and each of those consequences needs its own runtime consumer.

**Layman's version:** proving the glyph fired does not prove its damage, restore, or debuff reached the score. A perfectly scheduled proc can still be missing from DPS, sustain, or uptime if its consequence never reaches the relevant engine.

**For BFF:** exact sustained-DPS leaves now audit every consequence row attached to selected glyph procs. Any selected consequence without an explicit consumer remains unresolved and blocks mechanic completeness rather than being treated as zero.


## 2026-09-23 — Trait math must not erase enchant scaling metadata

The weapon-enchantment parser and repository correctly preserve special runtime metadata such as Oblivion's `target_max_health` scaling. The trait-adjustment service rebuilt each `CombatEffect` after applying Infused/Jade-style value rules, but did not copy `scaling_type` or `condition`, so applying a weapon trait could silently turn a scaling enchant into an apparently flat one.

**Layman's version:** the trait calculator changed the number and accidentally threw away the instruction card explaining what the number meant.

**For BFF:** trait-adjusted enchant effects now preserve scaling and condition provenance. Runtime damage must still resolve those semantics explicitly; preservation prevents downstream code from mistaking a scaled effect for flat damage.


## 2026-09-23 — Selected Crusher now changes exact-time target resistance

Once the runtime branch proves that a Crushing glyph actually fired, its canonical resistance-reduction magnitude and duration are enough to affect the target during that exact window. Source selection alone was previously not enough; the consequence still had to be routed into mitigation math.

**Layman's version:** knowing Crusher fired is finally connected to the boss actually having less armor while Crusher is active. Very ambitious concept, apparently.

**For BFF:** selected non-overlapping Crusher windows now subtract their canonical magnitude through the shared exact-time target-resistance path. Missing target/duration/magnitude or overlapping windows remain unresolved rather than assuming stacking or overwrite behavior.


## 2026-09-23 — Weapon Damage glyphs are timed stat state, not bonus damage events

A selected Weapon/Spell Damage glyph proc does not directly contribute a separate damage hit. It opens a timed character-stat window that changes subsequent Weapon Damage and Spell Damage calculations.

**Layman's version:** this glyph makes later attacks stronger; it is not itself another attack. Adding its number directly to DPS would be spectacularly wrong in a very efficient way.

**For BFF:** selected Weapon/Spell Damage glyph windows now reuse the canonical timed `weapon_spell_damage` runtime-effect projection. The exact build context is rebuilt while the window is active, and strict overlapping windows remain fail-closed pending reviewed refresh/stacking semantics.


## 2026-09-23 — Gold weapon quality is not proof of a Gold glyph

Weapon-enchantment runtime needs two different quality facts. The weapon's own quality controls trait math such as Infused, while Decrease Health's target-Max-Health percentage and damage ceiling are defined from the **enchantment's** level and quality. A Gold sword with an unknown-quality glyph does not prove a Legendary Decrease Health glyph.

**Layman's version:** a fancy sword does not automatically make the rune glued to it fancy too. They are two different objects with two different quality knobs.

**For BFF:** saved gear now carries `EnchantQuality` separately from item `Quality`; weapon-enchantment runtime preserves glyph quality, glyph tier, and item level as separate provenance. Exact Decrease Health damage stays unresolved when glyph quality is missing instead of borrowing the weapon's quality.

## 2026-09-23 — Infused should not inflate Decrease Health's Oblivion damage

ZOS Update 23 states that player-sourced Oblivion Damage bypasses positive and negative bonuses, while Decrease Health's Max-Health percentage and maximum damage scale from the enchantment's own quality/level. That makes ordinary enchant-strength bonuses the wrong layer for its damage magnitude even though Infused can still alter weapon-enchantment cooldown.

**Layman's version:** Infused can make the glyph fire more often, but it does not get to sneak a normal “make the enchant stronger” multiplier into Oblivion damage that explicitly ignores those bonuses.

**For BFF:** weapon-enchantment trait adjustment now leaves Oblivion damage magnitude unboosted while preserving the separate cooldown-reduction rule. Exact target-Max-Health scaling is resolved downstream from glyph provenance and target Health.


## 2026-09-23 — Proc damage has to enter the Health timeline before execute math

An exact weapon-glyph damage number is not enough if it is added only after rotation damage has already been evaluated. A Decrease Health proc between two skills changes the boss's current Health before the second skill, which can change execute scaling, kill timing, later action legality, and overkill attribution.

**Layman's version:** damage that happens at 1.5 seconds has to hurt the boss before a 2-second execute checks how hurt the boss is. Adding it to the total at the end is mathematically neat and mechanically wrong.

**For BFF:** exact supplemental damage now runs through the same sequential target-Health ledger as action and periodic damage. Cross-source events sharing an exact timestamp remain fail-closed until ESO ordering for that instant is proven.
