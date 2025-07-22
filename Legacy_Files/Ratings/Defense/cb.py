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
            print(f"📅 rate_cb() received snap_count = {snap_count}")

        if snap_count is None:
            snap_count = 0.0  # default to 0.0 but should always be passed

        if target_rate is None:
            targets = get_val(adv_row, "Tgt")
            target_rate = (targets / snap_count * 100) if snap_count else 0.0

        snap_count = float(snap_count)
        target_rate = float(target_rate)
        qb_rating = get_val(adv_row, "Rat")

        if verbose:
            print(f"🔍 Clean snap_count = {snap_count}, target_rate = {target_rate}, QB Rating = {qb_rating}")

        lockdown_bonus = 0
        suppression_score = 0
        elite_penalty = 0

        if snap_count >= 500 and target_rate < 10:
            rounded_target = int(round(target_rate))
            if verbose:
                print(f"🛡️ Lockdown mode active: Rounded Target Rate = {rounded_target}")

            if rounded_target <= 6:
                lockdown_bonus = 40
            elif rounded_target == 7:
                lockdown_bonus = 25
            elif rounded_target == 10:
                lockdown_bonus = 15

            suppression_score = (1 - target_rate / 100) * (snap_count / 100) * 0.8

        # Elite corner penalty if QB rating allowed is too high
        if lockdown_bonus > 0 and qb_rating > 80:
            elite_penalty = (qb_rating - 80) * 0.5
            if verbose:
                print(f"⛔️ Elite CB penalty = {elite_penalty:.2f} due to QB Rating > 80")

        ints = get_val(cb_row, "Int")
        if ints >= 10:
            ballhawk_bonus = (ints - 3) * 1.5
            if verbose:
                print(f"🏈 Ballhawk bonus = {ballhawk_bonus}")
        else:
            ballhawk_bonus = 0

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
            missed_tackles * 1.0 +
            ballhawk_bonus
        )

        total_score = base_score + lockdown_bonus + suppression_score - elite_penalty

        if verbose:
            print(f"🧲 Base = {base_score:.2f}, Lockdown = {lockdown_bonus}, Suppression = {suppression_score:.2f}, Elite Penalty = {elite_penalty:.2f}, Total = {total_score:.2f}")

        return round(total_score, 2)

    except Exception as e:
        if verbose:
            print(f"❌ Error in rate_cb: {e}")
        return 0.0
