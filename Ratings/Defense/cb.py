import pandas as pd

def rate_cb(cb_row, adv_row=None, snap_count=None, target_rate=None, bonus=True, verbose=False):
    import pandas as pd

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
            print(f"📥 rate_cb() received snap_count = {snap_count}")
            print(f"📥 rate_cb() cb_row['def_num'] = {cb_row.get('def_num', 'N/A')}")

        if snap_count is None:
            snap_count = get_val(cb_row, "def_num")
        if target_rate is None:
            target_rate = get_val(cb_row, "target_rate")

        snap_count = float(snap_count)
        target_rate = float(target_rate)

        if verbose:
            print(f"🔍 Clean snap_count = {snap_count}, target_rate = {target_rate}")

        lockdown_bonus = 0
        suppression_score = 0

        if snap_count >= 500 and target_rate < 10:
            rounded_target = int(round(target_rate))
            if verbose:
                print(f"🛡️ Lockdown mode active: Rounded Target Rate = {rounded_target}")

            if rounded_target <= 6:
                lockdown_bonus = 40
            elif rounded_target == 9:
                lockdown_bonus = 25
            elif rounded_target == 10:
                lockdown_bonus = 15

            if verbose:
                print(f"✨ Lockdown bonus = {lockdown_bonus}")

            suppression_score = (1 - target_rate / 100) * (snap_count / 100) * 0.8  # scaled version

        ints = get_val(cb_row, "Int")
        if ints >= 10:
            ballhawk_bonus = (ints - 3) * 1.5

            if verbose:
                print(f"🏈 Ballhawk bonus = {ballhawk_bonus}")

        pd_def = get_val(cb_row, "PD")
        tackles = get_val(cb_row, "Comb")
        missed_tackles = get_val(cb_row, "MTkl")

        if tackles > 60:
            tackle_score = 60 * 0.5 + (tackles - 60) * 0.2
        else:
            tackle_score = tackles * 0.5

        base_score = (
            ints * 2 +
            pd_def * 1.5 +
            tackle_score -
            missed_tackles * 1.0
        )

        total_score = base_score + lockdown_bonus + suppression_score

        if verbose:
            print(f"🧮 Base Score = {base_score}, Suppression = {suppression_score:.2f}, Total = {total_score}")

        return round(total_score, 2)

    except Exception as e:
        if verbose:
            print(f"❌ Error in rate_cb: {e}")
        return 0.0
