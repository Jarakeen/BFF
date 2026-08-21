

Health =
(300 * Level + 1000 + 122 * Attribute.Health + Item.Health + Set.Health + Food.Health + Skill2.Health + Mundus.Health)*(1 + Skill.Health + Buff.Health)

Magicka =
(220 * Level + 1000 + 111 * Attribute.Magicka + Item.Magicka + Set.Magicka + Food.Magicka + Mundus.Magicka + Skill2.Magicka)*(1 + Skill.Magicka + Buff.Magicka)

Stamina =
(220 * Level + 1000 + 111 * Attribute.Stamina + Item.Stamina + Set.Stamina + Food.Stamina + Mundus.Stamina + Skill2.Stamina)*(1 + Skill.Stamina + Buff.Stamina)

HealthRegen =
(round(5.592 * Level + 29.4) + Item.HealthRegen + Set.HealthRegen + min(1320, floor(Set.HealthRegenResistFactor * (PhysicalResist + SpellResist))) + Mundus.HealthRegen + (Food.HealthRegen)*(1/(1 + Skill2.HealthRegen)))*(1 + CP.HealthRegen + Skill.HealthRegen + Buff.HealthRegen)*(1 + Skill2.HealthRegen)*(1 + Vampire.HealthRegen)

MagickaRegen =
(round(9.30612 * Level + 48.7) + Item.MagickaRegen + Set.MagickaRegen + Mundus.MagickaRegen + (Food.MagickaRegen)*(1/(1 + Skill2.MagickaRegen)))*(1 + CP.MagickaRegen + Skill.MagickaRegen + Buff.MagickaRegen)*(1 + Skill2.MagickaRegen)

StaminaRegen =
(round(9.30612 * Level + 48.7) + Item.StaminaRegen + Set.StaminaRegen + Mundus.StaminaRegen + (Food.StaminaRegen)*(1/(1 + Skill2.StaminaRegen)))*(1 + CP.StaminaRegen + Skill.StaminaRegen + Buff.StaminaRegen)*(1 + Skill2.StaminaRegen)

SpellDamage =
(20 * Level + Item.SpellDamage + Set.SpellDamage + Skill2.SpellDamage + Mundus.SpellDamage + CP.SpellDamage)*(1 + Skill.SpellDamage + Buff.SpellDamage) + BloodthirstySpellDamage

WeaponDamage =
(20 * Level + Item.WeaponDamage + Set.WeaponDamage + Skill2.WeaponDamage + Mundus.WeaponDamage + CP.WeaponDamage)*(1 + Skill.WeaponDamage + Buff.WeaponDamage) + BloodthirstyWeaponDamage

SpellCrit =
(Set.SpellCrit + Skill2.SpellCrit + Buff.SpellCrit + CP.SpellCrit + Mundus.SpellCrit)*(1/(2*EffectiveLevel*(100 + EffectiveLevel))) + 0.10 + Item.SpellCrit + Skill.SpellCrit

SpellCritDamage =
(CP.SpellCritDamage + Skill.CritDamage + CP.CritDamage + Mundus.CritDamage + Set.CritDamage + Item.CritDamage + Buff.CritDamage + 0.5)*(1 + Skill2.CritDamage)

WeaponCritDamage =
(CP.WeaponCritDamage + Skill.CritDamage + CP.CritDamage + Mundus.CritDamage + Set.CritDamage + Item.CritDamage + Buff.CritDamage + 0.5)*(1 + Skill2.CritDamage)

SpellCritHealing =
(CP.SpellCritHealing + Skill.CritHealing + CP.CritHealing + Mundus.CritHealing + Set.CritHealing + Item.CritHealing + Buff.CritHealing + 0.5)*(1 + Skill2.CritHealing)

WeaponCritHealing =
(CP.WeaponCritHealing + Skill.CritHealing + CP.CritHealing + Mundus.CritHealing + Set.CritHealing + Item.CritHealing + Buff.CritHealing + 0.5)*(1 + Skill2.CritHealing)

SpellResist =
(Item.SpellResist + Skill2.SpellResist + Mundus.SpellResist + Set.SpellResist + Skill.SpellResist + CP.SpellResist)*(1 + Buff.SpellResist)

PhysicalResist =
(Item.PhysicalResist + Skill2.PhysicalResist + Mundus.PhysicalResist + Set.PhysicalResist + Skill.PhysicalResist + CP.PhysicalResist)*(1 + Buff.PhysicalResist)

CritResist =
1320 + Item.CritResist + Set.CritResist + Skill.CritResist + CP.CritResist + Buff.CritResist + round(Skill2.CritResist * EffectiveLevel * 100)

SpellPenetration =
Item.SpellPenetration + Set.SpellPenetration + Skill.SpellPenetration + CP.SpellPenetration + Buff.SpellPenetration + Mundus.SpellPenetration

PhysicalPenetration =
Item.PhysicalPenetration + Set.PhysicalPenetration + Skill.PhysicalPenetration + CP.PhysicalPenetration + Buff.PhysicalPenetration + Mundus.PhysicalPenetration

EffectiveSpellPower =
(round(Magicka/10.5) + SpellDamage)*(1 + SpellCrit*AttackSpellCritDamage)*(1 + CP.MagicDamageDone)*(1 - AttackSpellMitigation)*(1 + Target.DamageTaken)*(1 + DamageDone)

EffectiveWeaponPower =
(round(Stamina/10.5) + WeaponDamage)*(1 + WeaponCrit*AttackWeaponCritDamage)*(1 + CP.PhysicalDamageDone)*(1 - AttackPhysicalMitigation)*(1 + Target.DamageTaken)*(1 + DamageDone)

EffectivePower =
(round(max(Magicka, Stamina)/10.5) + max(SpellDamage, WeaponDamage))*(1 + max(SpellCrit, WeaponCrit)*max(AttackSpellCritDamage, AttackWeaponCritDamage))*(1 + max(CP.MagicDamageDone, CP.PhysicalDamageDone))*(1 - max(AttackSpellMitigation, AttackPhysicalMitigation))*(1 + Target.DamageTaken)*(1 + DamageDone)

FrostResist =
Item.FrostResist + Skill.FrostResist

FlameResist =
Item.FlameResist + Skill.FlameResist

ShockResist =
Item.ShockResist + Skill.ShockResist

PoisonResist =
Item.PoisonResist + Skill.PoisonResist

DiseaseResist =
Item.DiseaseResist + Skill.DiseaseResist

HealingDone =
Item.HealingDone + Set.HealingDone + Skill.HealingDone + CP.HealingDone + Buff.HealingDone + Mundus.HealingDone

AOEHealingDone =
Skill.AOEHealingDone + Set.AOEHealingDone + CP.AOEHealingDone

DotHealingDone =
Skill.DotHealingDone + Set.DotHealingDone + CP.DotHealingDone

SingleTargetHealingDone =
Skill.SingleTargetHealingDone + Set.SingleTargetHealingDone + CP.SingleTargetHealingDone

HealingTaken =
Item.HealingTaken + Set.HealingTaken + Skill.HealingTaken + CP.HealingTaken + Buff.HealingTaken

HealingReceived =
(1 + Item.HealingReceived + Set.HealingReceived + Skill.HealingReceived + CP.HealingReceived + Buff.HealingReceived)*(1 + Skill2.HealingReceived) - 1

HealingTotal =
(1 + HealingDone)*(1 + HealingTaken)*(1 + HealingReceived)

ResurrectTime =
(7)*(1 - Set.ResurrectSpeed)*(1 - Skill.ResurrectSpeed)*(1 - Buff.ResurrectSpeed)*(1 - CP.ResurrectSpeed)*(1 - Item.ResurrectSpeed)

HealingReduction =
CP.HealingReduction

HealthRestore =
Item.HealthRestore + Skill.HealthRestore + Buff.HealthRestore + Set.HealthRestore

MagickaRestore =
Item.MagickaRestore + Skill.MagickaRestore + Buff.MagickaRestore + Set.MagickaRestore

StaminaRestore =
Item.StaminaRestore + Skill.StaminaRestore + Buff.StaminaRestore + Set.StaminaRestore

BashCost =
(765 + Item.BashCost)*(1 + CP.BashCost)*(1 + Skill.BashCost)*(1 + Set.BashCost)

BashDamage =
(max(SpellResist, PhysicalResist) * 0.011250 + 1 + CP.BashDamage + Skill2.BashDamage)*(1 + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone + Skill.BashDamage) + Set.ExtraBashDamage + Skill.ExtraBashDamage + Item.ExtraBashDamage

BlockCost =
(1750 + Item.BlockCost)*(1 - Item.Sturdy)*(1 + CP.BlockCost)*(1 + Set.BlockCost)*(1 + Skill.BlockCost)*(1 + Buff.BlockCost)*(1 + Skill2.BlockCost)

BlockCost =
(1750 + Item.BlockCost)*(1 - Item.Sturdy)*(1 + CP.BlockCost)*(1 + Set.BlockCost)*(1 + Skill.BlockCost)*(1 + Buff.BlockCost)*(1 + Skill2.BlockCost)

RollDodgeCost =
((4040 + Skill2.RollDodgeCost)*(1 + CP.RollDodgeCost))*(Skill.RollDodgeCost + Item.RollDodgeCost + Set.RollDodgeCost + Buff.RollDodgeCost + 1)

BreakFreeCost =
((5400 + Skill2.BreakFreeCost)*(1 + CP.BreakFreeCost))*(1 + Skill.BreakFreeCost + Buff.BreakFreeCost + Item.BreakFreeCost + Set.BreakFreeCost)

FearDuration =
(4)*(1 + CP.FearDuration)*(1 + Set.CrowdControlDuration)

DamageShield =
(1 + CP.DamageShield)*(1 + Buff.DamageShield)*(1 + Set.DamageShield)*(1 + Skill.DamageShield) + -1

DamageShieldCost =
CP.DamageShieldCost + Skill.DamageShieldCost

DotDamageDone =
CP.DotDamageDone + Skill.DotDamageDone + Set.DotDamageDone

DirectDamageDone =
CP.DirectDamageDone + Skill.DirectDamageDone + Set.DirectDamageDone

SingleTargetDamageDone =
Skill.SingleTargetDamageDone + CP.SingleTargetDamageDone

AOEDamageDone =
Set.AOEDamageDone + Skill.AOEDamageDone + CP.AOEDamageDone

MagicDamageDone =
CP.MagicDamageDone + Skill.MagicDamageDone + Buff.MagicDamageDone + Item.MagicDamageDone + Set.MagicDamageDone

PhysicalDamageDone =
CP.PhysicalDamageDone + Skill.PhysicalDamageDone + Buff.PhysicalDamageDone + Item.PhysicalDamageDone + Set.PhysicalDamageDone

ShockDamageDone =
CP.ShockDamageDone + Skill.ShockDamageDone + Buff.ShockDamageDone + Item.ShockDamageDone + Set.ShockDamageDone

FlameDamageDone =
CP.FlameDamageDone + Skill.FlameDamageDone + Buff.FlameDamageDone + Item.FlameDamageDone + Set.FlameDamageDone

FrostDamageDone =
CP.FrostDamageDone + Skill.FrostDamageDone + Buff.FrostDamageDone + Item.FrostDamageDone + Set.FrostDamageDone

PoisonDamageDone =
CP.PoisonDamageDone + Skill.PoisonDamageDone + Buff.PoisonDamageDone + Item.PoisonDamageDone + Set.PoisonDamageDone

PoisonDamageDone =
CP.PoisonDamageDone + Skill.PoisonDamageDone + Buff.PoisonDamageDone + Item.PoisonDamageDone + Set.PoisonDamageDone

DiseaseDamageDone =
CP.DiseaseDamageDone + Skill.DiseaseDamageDone + Buff.DiseaseDamageDone + Item.DiseaseDamageDone + Set.DiseaseDamageDone

BowDamageDone =
CP.BowDamageDone + Skill.BowDamageDone + Buff.BowDamageDone + Item.BowDamageDone + Set.BowDamageDone

BleedDamageDone =
Set.BleedDamageDone + Skill.BleedDamageDone

PetDamageDone =
Skill.PetDamageDone + Set.PetDamageDone

DamageDone =
CP.DamageDone + Skill.DamageDone + Buff.DamageDone + Item.DamageDone + Set.DamageDone

StatusFlameSpellDamage =
SpellDamage + (SkillBonusSpellDmg.X)*(1 + Buff.SpellDamage + Skill.SpellDamage)

StatusFlameSpellDamage =
SpellDamage + (SkillBonusSpellDmg.X)*(1 + Buff.SpellDamage + Skill.SpellDamage)
X = type of damage (ie flame, shock, disease)


BurningDamage =
(floor(fround(0.016)*max(Magicka, Stamina)) + floor(fround(0.168)*max(StatusFlameSpellDamage, StatusFlameWeaponDamage)))*(1 + Skill.BurningDamage + FlameDamageDone + DotDamageDone + SingleTargetDamageDone + DamageDone)

ChilledDamage =
(floor(fround(0.008)*max(Magicka, Stamina)) + floor(fround(0.084)*max(StatusFrostSpellDamage, StatusFrostWeaponDamage)))*(1 + FrostDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone)

ConcussionDamage =
(floor(fround(0.008)*max(Magicka, Stamina)) + floor(fround(0.084)*max(StatusShockSpellDamage, StatusShockWeaponDamage)))*(1 + ShockDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone)

also looks like the same thing but with a type variable
Overcharged = MagicDamage
Sundered = PhysicalDamage
Hemorrhaging Damage / Tick = BleedDamage
Disease = DiseaseDamage
Poison = PoisonDamage

PoisonedDuration =
6.0

StatusDuration =
4.0 + Set.StatusEffectDuration

MagicalEnchantStatusChance =
(0.20)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MagicalStatusEffectChance)

MagicalAbilityStatusChance =
(0.10)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MagicalStatusEffectChance)

MagicalAOEStatusChance =
(0.05)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MagicalStatusEffectChance)

MagicalDOTStatusChance =
(0.03)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MagicalStatusEffectChance)

MagicalAOEDOTStatusChance =
(0.01)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MagicalStatusEffectChance)

MartialEnchantStatusChance =
(0.20)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MartialStatusEffectChance)

MartialAbilityStatusChance =
(0.10)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MartialStatusEffectChance)

MartialAOEStatusChance =
(0.05)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MartialStatusEffectChance)

MartialDOTStatusChance =
(0.03)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MartialStatusEffectChance)

MartialAOEDOTStatusChance =
(0.01)*(1 + Skill.StatusEffectChance + Set.StatusEffectChance + Item.StatusEffectChance + CP.MartialStatusEffectChance)

LAFlameSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Flame + Skill2.LASpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)


LAFlameStaff =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAFlameSpellDamage, LAFlameWeaponDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + FlameDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone)

LAFlameWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Flame + Skill2.LAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

LAShockSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Shock + Skill2.LASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

LAShockWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Shock + Skill2.LAWeaponDamage + Item.ChannelWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

LAFrostSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Frost + Skill2.LASpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

LAFrostWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Frost + Skill2.LAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

LAMagicSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Magic + Skill2.LASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

LAPhysicalWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Physical + Skill2.LAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

LAMagicSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Magic + Skill2.LASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

LAMagicSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Magic + Skill2.LASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

LAFrostStaff =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAFrostSpellDamage, LAFrostWeaponDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + FrostDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone)

LAShockStaff =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAShockSpellDamage, LAShockWeaponDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.HADamage + Set.HADamage + Buff.Empower + ShockDamageDone + SingleTargetDamageDone + DotDamageDone + DamageDone)

LAShockStaff =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAShockSpellDamage, LAShockWeaponDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.HADamage + Set.HADamage + Buff.Empower + ShockDamageDone + SingleTargetDamageDone + DotDamageDone + DamageDone)

LAUnarmed =
(min(floor(fround(0.05)*max(Magicka, Stamina)) + floor(fround(0.550)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3850) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + Set.LAMeleeDamage + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone)

LAOneHand =
(min(floor(fround(0.05)*max(Magicka, Stamina)) + floor(fround(0.550)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3850) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + Set.LAMeleeDamage + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone)

LATwoHand =
(min(floor(fround(0.05)*max(Magicka, Stamina)) + floor(fround(0.550)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3850) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + Set.LAMeleeDamage + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone)

LABow =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + BowDamageDone + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone + SkillLineDamage.Bow)

LABow =
(min(floor(fround(0.045)*max(Magicka, Stamina)) + floor(fround(0.4725)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3465) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + BowDamageDone + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone + SkillLineDamage.Bow)

LAWerewolf =
(min(floor(fround(0.05)*max(Magicka, Stamina)) + floor(fround(0.550)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)), 3850) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + Set.LAMeleeDamage + PhysicalDamageDone + DamageDone + DirectDamageDone + SingleTargetDamageDone)

OverloadDamage =
CP.OverloadDamage + Skill.OverloadDamage + Set.OverloadDamage + Buff.OverloadDamage

LAOverload =
(floor(fround(0.100)*max(Magicka, Stamina)) + floor(fround(1.050)*max(LAPhysicalWeaponDamage, LAPhysicalSpellDamage)) + Skill2.LADamage)*(1 + CP.LADamage + Skill.LADamage + Set.LADamage + ShockDamageDone + SingleTargetDamageDone + DirectDamageDone + DamageDone + OverloadDamage)

LASpeed =
1 + Set.LASpeed

LAMeleeSpeed =
1 + Set.LASpeed + Set.LAMeleeSpeed

Divines =
Item.Divines

Sturdy =
Item.Sturdy

Training =
Item.Training

Bloodthirsty =
Item.Bloodthirsty

BloodthirstySpellDamage =
(1 - min(0.9, Target.PercentHealth)/0.9)*(Item.Bloodthirsty)

BloodthirstyWeaponDamage =
(1 - min(0.9, Target.PercentHealth)/0.9)*(Item.Bloodthirsty)

UltimateRestore =
Item.UltimateRestore + Set.UltimateRestore

PotionDuration =
Item.PotionDuration + Skill.PotionDuration

PotionCooldown =
Item.PotionDuration + Skill.PotionDuration + Set.PotionDuration

SneakCost =
(133)*(1 + CP.SneakCost)*(1 + Skill.SneakCost)*(1 + Item.SneakCost)*(1 + Set.SneakCost)*(1 + Buff.SneakCost)

SneakRange =
(max(0, 6.5 + Skill2.SneakRange + CP.SneakRange))*(Skill.SneakRange + Set.SneakRange + 1)

SneakDetectRange =
(max(0, 6.5 + Skill2.SneakDetectRange + CP.SneakDetectRange))*(1 + Item.SneakDetectRange + Skill.SneakDetectRange + Set.SneakDetectRange)

SprintCost =
(500 + Skill2.SprintCost)*(1 + CP.SprintCost)*(1 + Buff.SprintCost)*(1 + Set.SprintCost)*(1 + Skill.SprintCost)*(1 + Item.SprintCost)

WalkSpeed =
((BaseWalkSpeed)*(0.3))*(1 + Buff.MovementSpeed + Skill.MovementSpeed + Item.MovementSpeed + Set.MovementSpeed + Mundus.MovementSpeed)*(1 + CP.MovementSpeed)

RunSpeed =
(BaseWalkSpeed)*(1 + Buff.MovementSpeed + Skill.MovementSpeed + Item.MovementSpeed + Set.MovementSpeed + Mundus.MovementSpeed)*(1 + CP.MovementSpeed)

SprintSpeed =
(BaseWalkSpeed)*(min(2, 1 + 0.40 + Set.SprintSpeed + Buff.MovementSpeed + Item.MovementSpeed + Set.MovementSpeed + Buff.SprintSpeed + Skill.MovementSpeed + Skill.SprintSpeed + CP.SprintSpeed + Mundus.MovementSpeed))*(1 + CP.MovementSpeed)

SwimSpeed =
((BaseWalkSpeed)*(1 - 0.40)*(1 + Skill.SwimSpeed))*(1 + Buff.MovementSpeed + Mundus.MovementSpeed + Item.MovementSpeed + Set.MovementSpeed + CP.MovementSpeed)

SneakSpeed =
((BaseWalkSpeed)*(1 + (-0.40)*(max(0, (1 - Skill.NormalSneakSpeed - CP.SneakSpeed)*(1 - Skill.SneakSpeed))) + Buff.MovementSpeed + Skill.MovementSpeed + Mundus.MovementSpeed + Item.MovementSpeed + Set.MovementSpeed))*(1 + Skill2.SneakSpeed + CP.MovementSpeed)

BlockSpeed =
(BaseWalkSpeed)*(1 - Skill.BlockSpeedPenalty)*(1 + Skill.BlockSpeed)*(1 + CP.BlockSpeed)

MountWalkSpeed =
((BaseWalkSpeed)*(1 + 0.15 + MountSpeedBonus + Skill.MountSpeed + CP.MountSpeed))*(1 + Set.MountSpeed + Buff.MountSpeed)

MountRunSpeed =
((BaseWalkSpeed)*(1 + 0.45 + MountSpeedBonus + Skill.MountSpeed + CP.MountSpeed))*(1 + Set.MountSpeed + Buff.MountSpeed)

FrostResist =
Item.FrostResist + Skill.FrostResist

FlameResist =
Item.FlameResist + Skill.FlameResist

ShockResist =
Item.ShockResist + Skill.ShockResist

PoisonResist =
Item.PoisonResist + Skill.PoisonResist

DiseaseResist =
Item.DiseaseResist + Skill.DiseaseResist

DotDamageTaken =
CP.DotDamageTaken + Set.DotDamageTaken + Skill.DotDamageTaken

DirectDamageTaken =
1 + CP.DirectDamageTaken + Set.DirectDamageTaken + Set.DirectDamageTaken

SingleTargetDamageTaken =
CP.SingleTargetDamageTaken + Skill.SingleTargetDamageTaken + Set.SingleTargetDamageTaken

AOEDamageTaken =
CP.AOEDamageTaken + Skill.AOEDamageTaken + Set.AOEDamageTaken

MagicDamageTaken =
(1 + CP.MagicDamageTaken)*(1 + Skill.MagicDamageTaken) - 1

PhysicalDamageTaken =
(1 + CP.PhysicalDamageTaken)*(1 + Skill.PhysicalDamageTaken) - 1

HADamageTaken =
1 + CP.HADamageTaken

LADamageTaken =
1 + CP.LADamageTaken

FallDamageTaken =
1 + CP.FallDamageTaken + Set.FallDamageTaken

DamageTaken =
(1 - 0.15)*(1 + CP.DamageTaken)*(1 + Skill.DamageTaken)*(1 + Buff.DamageTaken)*(1 + Item.DamageTaken)*(1 + Set.DamageTaken) + Buff.Vulnerability - 1

HARestoreBow =
(2772)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)

HARestoreDW =
(2095)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)

HARestore2H =
(2425)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)

HARestore1HS =
(2293)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)

HARestoreFireFrostStaff =
(2838 + Skill2.HAMagRestore)*(1 + CP.HAMagRestore)*(1 + Skill.HAMagRestore + Set.HAMagRestore + Buff.HAMagRestore)

HARestoreShockStaff =
(2970 + Skill2.HAMagRestore)*(1 + CP.HAMagRestore)*(1 + Skill.HAMagRestore + Set.HAMagRestore + Buff.HAMagRestore)

HARestoreRestStaff =
(2970 + Skill2.HAMagRestore)*(1 + CP.HAMagRestore)*(1 + Skill.HAMagRestore + Set.HAMagRestore + Buff.HAMagRestore)*(1 + Skill.HAMagRestoreRestStaff)

HARestoreUnarmed =
(2095)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)

HARestoreWerewolf =
(3235)*(1 + CP.HAStaRestore)*(1 + Skill.HAStaRestore + Set.HAStaRestore + Buff.HAStaRestore)*(1 + Skill.HAStaRestoreWerewolf)

Constitution =
(108)*(ArmorHeavy)*(1 + Set.Constitution)

HAFlameSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Flame + Skill2.HASpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

HAFlameWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Flame + Skill2.HAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

HAShockSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Shock + Skill2.HASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

HAShockWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Shock + Skill2.HAWeaponDamage + Item.ChannelWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

HAFrostSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Frost + Skill2.LASpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

HAFrostWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Frost + Skill2.LAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

HAMagicSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Magic + Skill2.HASpellDamage + Item.ChannelSpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

HAMagicWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Magic + Skill2.HAWeaponDamage + Item.ChannelWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

HAPhysicalWeaponDamage =
WeaponDamage + (SkillBonusWeaponDmg.Physical + Skill2.HAWeaponDamage)*(1 + Buff.WeaponDamage + Skill.WeaponDamage)

HAPhysicalSpellDamage =
SpellDamage + (SkillBonusSpellDmg.Physical + Skill2.HASpellDamage)*(1 + Buff.SpellDamage + Skill.SpellDamage)

HAFlameStaff =
(floor(fround(0.071429)*max(Magicka, Stamina)) + floor(fround(0.750)*max(HAFlameSpellDamage, HAFlameWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + FlameDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HAFrostStaff =
(floor(fround(0.071429)*max(Magicka, Stamina)) + floor(fround(0.750)*max(HAFrostSpellDamage, HAFrostWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + FrostDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HAShockStaffFinal =
(floor(fround(0.065714)*max(Magicka, Stamina)) + floor(fround(0.690)*max(HAShockSpellDamage, HAShockWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + ShockDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HAShockStaff =
(floor(fround(0.021905)*max(Magicka, Stamina)) + floor(fround(0.23)*max(LAMagicSpellDamage, LAMagicWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + ShockDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)*(2) + HAShockStaffFinal

HARestorationFinal =
(floor(fround(0.071429 )*max(Magicka, Stamina)) + floor(fround(0.75)*max(LAMagicSpellDamage, LAMagicWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + MagicDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HARestoration =
(floor(fround(0.01369)*max(Magicka, Stamina)) + floor(fround(0.14375)*max(LAMagicSpellDamage, LAMagicWeaponDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + MagicDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)*(2) + HARestorationFinal

HAUnarmed =
(floor(fround(0.0700)*max(Magicka, Stamina)) + floor(fround(0.7350)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + PhysicalDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HAOneHand =
(floor(fround(0.066667)*max(Magicka, Stamina)) + floor(fround(0.700)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + PhysicalDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HATwoHand =
(floor(fround(0.071429)*max(Magicka, Stamina)) + floor(fround(0.750)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + PhysicalDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HADualWield =
(floor(fround(0.023810)*max(Magicka, Stamina)) + floor(fround(0.250)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + floor(fround(0.023810)*max(Magicka, Stamina)) + floor(fround(0.250)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + PhysicalDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower + SkillLineDamage.Dual_Wield)

HAWerewolf =
(floor(fround(0.071429)*max(Magicka, Stamina)) + floor(fround(0.750)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + PhysicalDamageDone + DirectDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower)

HAOverload =
(floor(fround(0.0900)*max(Magicka, Stamina)) + floor(fround(0.945)*max(HAPhysicalWeaponDamage, HAPhysicalSpellDamage)) + Skill2.HADamage)*(1 + CP.HADamage + Skill.HADamage + Set.HADamage + ShockDamageDone + AOEDamageDone + SingleTargetDamageDone + DamageDone + Buff.Empower + OverloadDamage)

HASpeed =
1

AttackSpellMitigation =
(((min(33000, Target.SpellResist) + Target.SpellDebuff)*(1 - Skill2.SpellPenetration) - SpellPenetration)*(-1/(Target.EffectiveLevel * 1000)) + 1)*(1 - Target.DefenseBonus)*(-1) + 1

AttackPhysicalMitigation =
(((min(33000, Target.PhysicalResist) + Target.PhysicalDebuff)*(1 - Skill2.PhysicalPenetration) - PhysicalPenetration)*(-1/(Target.EffectiveLevel * 1000)) + 1)*(1 - Target.DefenseBonus)*(-1) + 1

AttackSpellCritDamage =
SpellCritDamage - (Target.CritResist)*(0.035/250)

AttackWeaponCritDamage =
WeaponCritDamage - (Target.CritResist)*(0.035/250)

DefenseSpellMitigation =
(((min(33000, SpellResist))*(1 - Target.PenetrationFactor) - Target.PenetrationFlat)*(-1/(EffectiveLevel * 1000)) + 1)*(1 + Target.AttackBonus)*(1 + MagicDamageTaken)*(1 + DamageTaken)*(-1) + 1

DefensePhysicalMitigation =
(((min(33000, PhysicalResist))*(1 - Target.PenetrationFactor) - Target.PenetrationFlat)*(-1/(EffectiveLevel * 1000)) + 1)*(1 + Target.AttackBonus)*(1 + PhysicalDamageTaken)*(1 + DamageTaken)*(-1) + 1

DefenseSpellAoEMitigation =
(1 + AOEDamageTaken)*(1 - DefensePhysicalMitigation)*(-1) + 1

DefensePhysicalAoeMitigation =
(1 + AOEDamageTaken)*(1 - DefensePhysicalMitigation)*(-1) + 1

DefenseSpellDDMitigation =
(1 + DirectDamageTaken)*(1 - DefensePhysicalMitigation)*(-1) + 1

DefensePhysicalDDMitigation =
(1 + DirectDamageTaken)*(1 - DefensePhysicalMitigation)*(-1) + 1

DefenseCritDmg =
Target.CritDamage - (CritResist)*(0.035/250)




