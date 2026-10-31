"""Evidence support score calibration against independently labeled incidents."""
from statistics import mean

def fit_bins(records: list[dict], bins: int = 5) -> dict:
    if not records or bins < 2:
        raise ValueError("Calibration needs labeled records and at least two bins")
    groups = [[] for _ in range(bins)]
    for r in records:
        s = float(r["score"])
        if not 0 <= s <= 1 or not isinstance(r["correct"], bool):
            raise ValueError("Expected score in [0,1] and boolean correct")
        groups[min(int(s*bins),bins-1)].append(r)
    result=[]
    for i,g in enumerate(groups):
        correct=sum(x["correct"] for x in g)
        result.append({"lower":i/bins,"upper":(i+1)/bins,"count":len(g),
                       "empirical_accuracy":correct/len(g) if g else None,
                       "smoothed_accuracy":(correct+1)/(len(g)+2) if g else None})
    return {"method":"binned_laplace_v1","sample_count":len(records),
            "brier_score_uncalibrated":round(mean((x["score"]-float(x["correct"]))**2 for x in records),5),
            "bins":result,"warning":"Real calibration requires independent representative labeled incidents; generated scenarios are insufficient."}

def calibrated_probability(score:float, model:dict, minimum_bin_samples:int=20)->float|None:
    if not 0 <= score <= 1:
        raise ValueError("Invalid support score")
    for entry in model["bins"]:
        if entry["lower"] <= score < entry["upper"] or score==1 and entry["upper"]==1:
            return entry["smoothed_accuracy"] if entry["count"] >= minimum_bin_samples else None
    return None


def load_calibration(path):
    import json
    from pathlib import Path
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('method')!='binned_laplace_v1':
        raise ValueError('Unknown calibration model')
    return data
