import pandas as pd

def rate_dl(dl_row, adv_row=None, snap_count=None, pressures=None, targets=None, completions=None, tfl=None, bonus=True, verbose=False):
    def get_val(row, col):
        try:
            val = row[col] if col in row else 0
            if isinstance(val, pd.Series):
                val = val.values[0]
            return float(val)
        except:
            return 0.0

    try:
        position = str(dl_row.get("Pos", "")).upper()
        if "EDGE" in position or "DE" in position or "DT" in position:
            position = "DL"

        if verbose:
            print(f"📥 rate_dl() received snap_count = {snap_count}, pressures = {pressures}, targets = {targets}, completions = {completions}, TFL = {tfl}")

        # Fallbacks with advanced row included
        snap_count = float(snap_count if snap_count is not None else get_val(dl_row, "def_num"))
        pressures = float(pressures if pressures is not None else get_val(dl_row, "Pressures") or get_val(adv_row, "Prss"))
        targets = float(targets if targets is not None else get_val(dl_row, "Tgt") or get_val(adv_row, "Tgt"))
        completions = float(completions if completions is not None else get_val(dl_row, "Cmp") or get_val(adv_row, "Cmp"))
        tfl = float(tfl if tfl is not None else get_val(dl_row, "TFL") or get_val(adv_row, "TFL"))

        completion_rate = (completions / targets) * 100 if targets > 0 else 0.0

        if verbose:
            print(f"🔍 Snap = {snap_count}, Pressures = {pressures}, Targets = {targets}, Completions = {completions}, TFL = {tfl}")
            print(f"📊 Completion Rate = {completion_rate:.1f}%")

        # Archetype assignment
        is_pass_rusher = pressures >= 5
        is_run_stopper = tfl >= 3

        archetype = "Balanced"
        if is_pass_rusher:
            archetype = "Pass Rusher"
        if is_run_stopper:
            archetype = "Run Stopper"
        if is_pass_rusher and is_run_stopper:
            archetype = "Dual Threat"

        if verbose:
            print(f"🧬 Archetype: {archetype}")

        # Stats used for scoring
        ints = get_val(dl_row, "Int")
        pd_def = get_val(dl_row, "PD")
        tackles = get_val(dl_row, "Comb")
        missed_tackles = get_val(dl_row, "MTkl") if "MTkl" in dl_row else 0.0
        sacks = get_val(dl_row, "Sk")

        # Base scoring system
        tackle_score = tackles * 0.5 - missed_tackles * 1.0
        sack_score = sacks * 2.5
        int_score = ints * 2
        pd_score = pd_def * 1.5
        tfl_score = tfl * 2.0

        base_score = tackle_score + sack_score + int_score + pd_score + tfl_score

        # Dual-threat bonus
        dual_bonus = 0
        if is_pass_rusher and is_run_stopper:
            dual_bonus = 10
            if verbose:
                print(f"✨ Dual Threat Bonus = {dual_bonus}")

        # Tackling penalty if total tackles are low
        tackle_penalty = 0
        if tackles < 20:
            tackle_penalty = 5
            if verbose:
                print(f"🚫 Low tackle count penalty = {tackle_penalty}")

        # Penalty for weak balanced DL
        tfl_penalty = 0
        if archetype == "Balanced" and tfl < 3:
            tfl_penalty = 10
            if verbose:
                print(f"⚠️ Ineffective Balanced DL penalty = {tfl_penalty}")

        total_score = base_score + dual_bonus - tackle_penalty - tfl_penalty

        if verbose:
            print(f"🧮 Final Score Breakdown: Base = {base_score:.2f}, Dual Bonus = {dual_bonus}, Tackle Penalty = {tackle_penalty}, TFL Penalty = {tfl_penalty}, Total = {total_score:.2f}")

        return round(total_score, 2)

    except Exception as e:
        if verbose:
            print(f"❌ Error in rate_dl: {e}")
        return 0.0