import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def get_archetype(pos, base_row, adv_row, snap_row=None):
    pos = pos.upper()
    row = adv_row.iloc[0] if not adv_row.empty else {}

    def val(r, col):
        try:
            return float(r.get(col, 0)) if col in r else 0.0
        except:
            return 0.0

    pressures = val(row, "Prss")
    targets = val(row, "Tgt")
    completions = val(row, "Cmp")
    tfl = val(row, "TFL")
    pd_def = val(row, "PD")
    ints = val(row, "Int")
    tackles = val(row, "Comb")
    completion_rate = (completions / targets) * 100 if targets > 0 else 0.0

    # --- Defensive Logic ---
    if any(x in pos for x in ["CB", "DB"]):
        snap_count = 0.0
        if "def_num" in row and val(row, "def_num") > 0:
            snap_count = val(row, "def_num")
        elif "Def_Num" in base_row and float(base_row.get("Def_Num", 0)) > 0:
            snap_count = float(base_row.get("Def_Num", 0))
        elif snap_row is not None and not snap_row.empty:
            try:
                snap_count = float(snap_row.iloc[0].get("Def_Num", 0) or 0)
            except:
                snap_count = 0.0
        target_rate = (targets / snap_count) * 100 if snap_count else 100.0

        if snap_count >= 500 and target_rate < 10:
            return {"archetype": "Lockdown Corner", "reason": "<10% target rate on 500+ snaps"}
        if targets >= 30 and completion_rate < 60:
            return {"archetype": "Coverage Corner", "reason": "high targets with low comp%"}
        if ints >= 3 and pd_def >= 10 and tackles >= 60:
            return {"archetype": "Elite Balanced Corner", "reason": "strong INTs, PDs, and tackle volume"}
        return {"archetype": "Balanced Corner", "reason": "no elite coverage or suppression profile"}

    if pos in ["S", "FS", "SS"]:
        if pressures >= 5:
            return {"archetype": "Blitzer Safety", "reason": "pressures >= 5"}
        if targets >= 10 and completion_rate < 65:
            return {"archetype": "Coverage Safety", "reason": "targeted 10+ with comp% under 65"}
        if pressures >= 3 and targets >= 10 and completion_rate < 70 and tfl >= 5:
            return {"archetype": "Elite Balanced Safety", "reason": "solid in all areas: pressures, TFL, coverage"}
        return {"archetype": "Balanced Safety", "reason": "no strong blitz or coverage lean"}

    if any(x in pos for x in ["MLB", "ILB", "OLB", "LB"]):

        if pressures >= 10:
            return {"archetype": "Blitzing Linebacker", "reason": "pressures >= 10"}
        if targets >= 20 and completion_rate < 60:
            return {"archetype": "Coverage Linebacker", "reason": "20+ targets with <60% comp"}
        if pressures >= 6 and tfl >= 6 and targets >= 15 and completion_rate < 65:
            return {"archetype": "Elite Balanced Linebacker", "reason": "balanced pressures, coverage, and run support"}
        return {"archetype": "Balanced Linebacker", "reason": "no heavy blitz or lockdown traits"}


    if any(x in pos for x in ["DL", "DE", "DT", "EDGE", "LE", "RE"]):

        if pressures >= 5 and tfl >= 3:
            return {"archetype": "Dual Threat Lineman", "reason": "pressure >= 5 and TFL >= 3"}
        if pressures >= 5:
            return {"archetype": "Pass Rush Specialist", "reason": "pressures >= 5"}
        if tfl >= 3:
            return {"archetype": "Run Stopper", "reason": "TFL >= 3"}
        if pressures >= 3 and tfl >= 2:
            return {"archetype": "Elite Balanced Lineman", "reason": "moderate pressures and run stops"}
        return {"archetype": "Balanced Lineman", "reason": "not enough pressure or TFL for role specialization"}

    # --- Offensive Logic (Threshold-Based) ---
    if pos == "QB":
        td = val(base_row, "TD")
        int_ = val(base_row, "Int")
        yds = val(base_row, "Yds")
        comp = val(base_row, "Cmp")
        att = val(base_row, "Att")
        cmp_pct = (comp / att) * 100 if att else 0.0

        if yds >= 4000 and cmp_pct >= 66 and td >= 30 and int_ <= 7:
            return {"archetype": "All-Around Elite QB", "reason": "4000+ yds, 66%+, 30+ TDs, low INTs"}
        if cmp_pct >= 68 and td / (int_ or 1) >= 4:
            return {"archetype": "Efficient Passer", "reason": "68%+ comp and TD/INT >= 4"}
        if yds >= 3000 and cmp_pct >= 64:
            return {"archetype": "Volume Distributor", "reason": "3000+ yds with high efficiency"}
        return {"archetype": "Balanced QB", "reason": "no elite scoring or efficiency traits"}

    if pos == "RB":
        rush_yds = val(adv_row, "Yds")
        brk_tkl = val(adv_row, "BrkTkl")

        # Pull from rushing_and_receiving base_row
        ypc = val(base_row, "Rushing - Y/A")
        rec = val(base_row, "Receiving - Rec")
        rec_yds = val(base_row, "Receiving - Yds")

        is_receiving_back = rec >= 15 and rec_yds >= 250
        is_power_runner = rush_yds >= 800 and ypc >= 4.2

        if is_receiving_back and is_power_runner:
            return {"archetype": "All-Around Elite RB", "reason": "strong rushing + receiving profile"}
        if is_receiving_back:
            return {"archetype": "Receiving Back", "reason": "15+ Rec, 250+ Rec Yds"}
        if is_power_runner:
            return {"archetype": "Power Runner", "reason": "800+ yds, 4.2+ YPC"}
        return {"archetype": "Balanced RB", "reason": "no dominant rush or receive profile"}

    if pos == "WR":
        rec = val(adv_row, "Rec")
        yds = val(adv_row, "Yds")
        tgt = val(adv_row, "Tgt")
        adot = val(adv_row, "ADOT")
        yac = val(adv_row, "YAC")
        one_d = val(adv_row, "1D")
        drop = val(adv_row, "Drop%")
        catch_pct = rec / tgt if tgt else 0

        if rec >= 70 and yds >= 1000 and catch_pct >= 0.65 and yac / rec >= 3 and adot >= 8:
            return {"archetype": "All-Around Elite WR", "reason": "70+ rec, 1000+ yds, elite traits"}
        if catch_pct >= 75 and adot <= 9:
            return {"archetype": "Possession WR", "reason": "75%+ catch, low ADOT"}
        if rec and yac / rec >= 6.0:
            return {"archetype": "YAC Specialist", "reason": "YAC per catch >= 6.0"}
        if adot >= 12:
            return {"archetype": "Deep Threat", "reason": "ADOT >= 12"}
        return {"archetype": "Balanced WR", "reason": "no dominant depth or YAC profile"}

    if pos == "TE":
        rec = val(adv_row, "Rec")
        yds = val(adv_row, "Yds")
        tgt = val(adv_row, "Tgt")
        one_d = val(adv_row, "1D")
        yac_r = val(adv_row, "YAC/R")
        drop = val(adv_row, "Drop%")
        catch_pct = rec / tgt if tgt else 0

        if rec >= 60 and yds >= 800 and catch_pct >= 0.65 and yac_r >= 3 and one_d >= 40:
            return {"archetype": "All-Around Elite TE", "reason": "high volume, 800+ yds, YAC and 1D"}
        if catch_pct >= 75 and yds / tgt >= 7:
            return {"archetype": "Possession TE", "reason": "75%+ catch, 7+ YPT"}
        if rec / rec >= 6.0:
            return {"archetype": "YAC Specialist", "reason": "YAC per catch >= 6.0"}

        if one_d / rec >= 0.6:
            return {"archetype": "Red Zone Threat", "reason": "60% 1D rate"}
        return {"archetype": "Balanced TE", "reason": "no elite YAC or scoring efficiency"}

    return {"archetype": "Unknown", "reason": "position logic not matched"}
