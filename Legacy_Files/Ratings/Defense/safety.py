import pandas as pd

def rate_safety(row, adv_row=None, snap_count=None, pressures=None, targets=None, completions=None, target_rate=None, bonus=True, verbose=False):
    def get_val(r, col):
        try:
            val = r[col] if col in r else 0
            if isinstance(val, pd.Series):
                val = val.values[0]
            return float(val)
        except:
            return 0.0

    try:
        if verbose:
            print(f"📥 rate_safety() received snap_count = {snap_count}, pressures = {pressures}, targets = {targets}, completions = {completions}, target_rate = {target_rate}")

        # Fallbacks
        snap_count = float(snap_count if snap_count is not None else get_val(row, "def_num"))
        pressures = float(pressures if pressures is not None else get_val(row, "Pressures"))
        targets = float(targets if targets is not None else get_val(row, "Tgt"))
        completions = float(completions if completions is not None else get_val(row, "Cmp"))
        target_rate = float(target_rate if target_rate is not None else get_val(row, "target_rate"))
        tfl = get_val(row, "TFL")

        completion_rate = (completions / targets) * 100 if targets > 0 else 0.0

        # Archetype logic with **lower thresholds**
        archetype = "Balanced"
        if pressures >= 5:
            archetype = "Blitzer"
        elif targets >= 10 and completion_rate < 65:
            archetype = "Coverage"

        if verbose:
            print(f"🧬 Archetype: {archetype}")

        # Lockdown bonus (lowered thresholds)
        lockdown_bonus = 0
        suppression_score = 0
        if snap_count >= 500 and target_rate < 10:
            rounded_target = int(round(target_rate))
            if rounded_target <= 4:
                lockdown_bonus = 20
            elif rounded_target == 6:
                lockdown_bonus = 10
            elif rounded_target == 10:
                lockdown_bonus = 5

            suppression_score = (1 - target_rate / 100) * (snap_count / 100) * 0.5

        ints = get_val(row, "Int")
        pd_def = get_val(row, "PD")
        tackles = get_val(row, "Comb")
        missed_tackles = get_val(row, "MTkl")
        sacks = get_val(row, "Sk")

        tackle_score = tackles * 0.5 - missed_tackles * 1.0
        sack_score = sacks * 1.5
        int_score = ints * 2
        pd_score = pd_def * 1.5
        tfl_score = tfl * 1.2

        base_score = tackle_score + sack_score + int_score + pd_score + tfl_score

        # Coverage penalty if they're a liability
        coverage_penalty = 0
        if targets >= 10 and completion_rate > 65:
            coverage_penalty = (completion_rate - 65) * 0.4

        # Weak balance penalty
        tfl_penalty = 0
        if archetype == "Balanced" and tfl < 5:
            tfl_penalty = 7

        total_score = base_score + lockdown_bonus + suppression_score - coverage_penalty - tfl_penalty

        if verbose:
            print(f"🧮 Base = {base_score:.2f}, Lockdown = {lockdown_bonus}, Suppression = {suppression_score:.2f}, Coverage Penalty = {coverage_penalty:.2f}, TFL Penalty = {tfl_penalty}, Total = {total_score:.2f}")

        return round(total_score, 2)

    except Exception as e:
        if verbose:
            print(f"❌ Error in rate_safety: {e}")
        return 0.0
