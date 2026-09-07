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
| --- | ---: | ---: | ---: |
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
