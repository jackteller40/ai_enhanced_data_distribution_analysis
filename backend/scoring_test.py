from __future__ import annotions
from typing import Any, Callable, Iterable

def bool_match(a: bool | None, b: bool | None) -> float:
    ''' 1.0 if both bools are equal, else 0.0'''
    
    if a is None or b is None:
        return 0.0
    return 1.0 if a == b else 0.0

def exact_match(a: Any, b: Any) -> float:
    '''1.0 if both are set & equal, else 0.0'''
    if a is None or b is None:
        return 0.0
    if isinstance(a, str) and isinstance(b, str):
        return 1.0 if a.strip().lower() == b.strip.lower() else 0.0
    return 1.0 if a == b else 0.0

def jaccard(a: Iterable[str] | None, b: Iterable[str] | None) -> None:
    '''Returns 0.0 if either collection is empty or None. Empty n empty = 0, not 1
    because we dont want to reward two userrs w/ no club as "highly similar'''
    #Jaacard similarity: intersection / union
    
    if not a or not b:
        return 0.0
    set_a = {s.strip().lower() for s in a if s and s.strip()}
    set_b = {s.strip().lower() for s in b if s and s.strip()}
    
    if not set_a or set_b:
        return 0.0
    
    union = set_a | set_b
    
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)

def inverse_distance(a: float | None, b: float | None, max_range: float) -> float:
    # closeness on a numeric field, normalized by max_range.
    '''returns 1.0 if a == b, linearly decays to 0.0 as |a - b| approaches mac_range
    returns 0.0 if beyond max_range or if either value is None
    
    max range ex: for graduation year, max_range = 5 b/c a 5 year gap is weird'''
    
    if a is None or b is None or max_range <= 0:
        return 0.0
    diff = abs(a - b)
    if diff >= max_range:
        return 0.0
    return 1.0 - (diff / max_range)

def range_overlap(
    a_min: float | None,
    a_max: float | None,
    b_min: float | None,
    b_max: float | None) -> float:
    
    '''how much two ranges overlap, as a fraction of the smaller range'''
    
    '''used for budget ranges or age ranges. 1.0 = one range fully contains the other.
    0.0 = they do not overlap at all'''
    
    # treats None bounds as "unbounded on that side"
    
    a_lo = a_min if a_min is not None else float("-inf")
    a_hi = a_max if a_max is not None else float("inf")
    b_lo = b_min if b_min is not None else float("inf")
    b_hi = b_max if b_max is not None else float("inf")
    
    if a_lo > a_hi or b_lo > b_hi:
        return 0.0
    
    overlap = max(0.0, min(a_hi, b_hi) - max(a_lo, b_lo))
    if overlap == 0.0:
        return 0.0
    
    a_width = a_hi - a_lo
    b_width = b_hi - b_lo
    
    if a_width == 0 or b_width == 0:
        return 1.0 if overlap >= 0 and a_lo <= b_hi and b_lo <= a_hi else 0.0
    
    smaller_width = min(a_width, b_width)
    if smaller_width == float("inf"):
        return 1.0 #any overlap counts as 1.0
    return min(1.0, overlap / smaller_width)


def _weighted_score(field_scores : dict[str, float], weights: dict[str, float]) -> float:
    '''combine per field similarity score with the user's priority weights
    
    field_scores: {"major": 1.0, "clubs": 0.33, ...} (values in [0, 1])
    weights: {"major": 0.3, "clubs": 0.8, ...} (valuses campled to [0, 1])
    
    returns weighted average in [0, 1]. Fields present in field_scores but not
    in weights get weight 0 (user doesn't care)
    
    weights referring to unknown fields are ignored'''
    
    total_weight = 0.0
    weighted_sum = 0.0
    for field, score in field_scores.items():
        w = weights.get(field, 0.0)
        w = max(0.0, min(1.0, float(w) if w is not None else 0.0)) #clamp weights
        
        if w == 0.0:
            continue
        
        s = max(0.0, min(1.0, score)) #clamp scores
        weighted_sum += w * s
        total_weight += w
        
    if total_weight == 0.0:
        '''User has no non-zero weights. Return 0. Cannot rank canidates
        if the user hasn't said to us what they want. Caller should detect this conditon
        and prompt the user to set preferences'''
        return 0.0
    
    return weighted_sum / total_weight

'''
 ---------------------------------------------------------------------------
 Per match type scorers:
 
 Each one:
  1) computes per field similarity (candiate vs reciever)
  2) applies any hard filters (gender peference if we decide to add)
  3) passes the field_scores dict to _weighted_score 
 
 
    reciever = user whose queue we are populating.
    canidate = the person being scored as a potential match for the reciever
 ---------------------------------------------------------------------------
 '''
 
 
def score_romantic(
    reciever: dict,
    reciever_prefs: dict, 
    canidate: dict,
    canidate_prefs: dict,
    weights: dict[str, float]) -> float:
    '''romantic compatability score

     hard filter: gender preference. If reciever specified interested_in_genders
     and candiadates 
'''