import pandas as pd

def rate_lb(lb_row, adv_row=None, snap_count=None, pressures=None, targets=None, completions=None, tfl=None, bonus=True, verbose=False):
    def get_val(row, col):
        try:
            val = row[col] if col in row else 0
            if isinstance(val, pd.Series):
                val = val.values[0]
            return float(val)
        except:
            return 0.0

    try:
        if verbose:
            print(f"📅 rate_lb() received snap_count = {snap_count}, pressures = {pressures}, targets = {targets}, completions = {completions}, TFL = {tfl}")

        # Fallbacks if not passed — now prefer adv_row first
        snap_count = float(snap_count if snap_count is not None else get_val(lb_row, "def_num"))
        pressures = float(pressures if pressures is not None else get_val(adv_row, "Pressures"))
        targets = float(targets if targets is not None else get_val(adv_row, "Tgt"))
        completions = float(completions if completions is not None else get_val(adv_row, "Cmp"))
        tfl = float(tfl if tfl is not None else get_val(adv_row, "TFL"))

        completion_rate = (completions / targets) * 100 if targets > 0 else 0.0

        if verbose:
            print(f"🔍 Snap = {snap_count}, Pressures = {pressures}, Targets = {targets}, Completions = {completions}, TFL = {tfl}")
            print(f"📊 Completion Rate = {completion_rate:.1f}%")

        # Archetype assignment
        archetype = "Balanced"
        if pressures >= 10:
            archetype = "Blitzer"
        elif targets >= 20 and completion_rate < 60:
            archetype = "Coverage"

        if verbose:
            print(f"🧬 Archetype: {archetype}")

        # Stats used for scoring
        ints = get_val(lb_row, "Int")
        pd_def = get_val(lb_row, "PD")
        tackles = get_val(lb_row, "Comb")
        missed_tackles = get_val(lb_row, "MTkl")
        sacks = get_val(lb_row, "Sk")

        # Base scoring system
        tackle_score = tackles * 0.5 - missed_tackles * 1.0
        sack_score = sacks * 1.5
        int_score = ints * 2
        pd_score = pd_def * 1.5
        tfl_score = tfl * 1.2

        base_score = tackle_score + sack_score + int_score + pd_score + tfl_score

        # Coverage penalty if LB is bad in coverage
        coverage_penalty = 0
        if targets >= 20 and completion_rate > 60:
            coverage_penalty = (completion_rate - 60) * 0.5
            if verbose:
                print(f"🚫 Coverage penalty = {coverage_penalty:.2f}")

        # 🚩 Remove invalid penalty: if targets are actually tracked
        if targets == 0 and snap_count >= 300:
            coverage_penalty += 15
            if verbose:
                print(f"❌ No-target penalty = 15")

        # TFL penalty for ineffective balanced LBs
        tfl_penalty = 0
        if archetype == "Balanced" and tfl < 8:
            tfl_penalty = 10
            if verbose:
                print(f"⚠️ Ineffective Balanced LB penalty = {tfl_penalty}")

        total_score = base_score - coverage_penalty - tfl_penalty

        if verbose:
            print(f"🧲 Final Score Breakdown: Base = {base_score:.2f}, Coverage Penalty = {coverage_penalty:.2f}, TFL Penalty = {tfl_penalty}, Total = {total_score:.2f}")

        return round(total_score, 2)

    except Exception as e:
        if verbose:
            print(f"❌ Error in rate_lb: {e}")
        return 0.0
