"""
Match Scoring

function that takes two profiles + weights + match_type and returns a float
in [0, 1.15]. 1.0 = perfect alignment on everything the user cares about.
0.15 extra for the "candidate already liked you" bonus.

"""

from __future__ import annotations
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
        return 1.0 if a.strip().lower() == b.strip().lower() else 0.0
    return 1.0 if a == b else 0.0

def jaccard(a: Iterable[str] | None, b: Iterable[str] | None) -> float:
    '''Returns 0.0 if either collection is empty or None. Empty n empty = 0, not 1
    because we dont want to reward two userrs w/ no club as "highly similar'''
    #Jaacard similarity: intersection / union
    
    if not a or not b:
        return 0.0
    set_a = {s.strip().lower() for s in a if s and s.strip()}
    set_b = {s.strip().lower() for s in b if s and s.strip()}
    
    if not set_a or not set_b:
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
    b_lo = b_min if b_min is not None else float("-inf")
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

_SELF_TO_PREFERENCE: dict [str, str] = {
    "woman": "women",
    "man": "men",
    "nonbinary": "nonbinary/queer identities",
    "queer/other": "nonbinary/queer identities"
}
    

def _gender_satisfies(
    preferences: list[str] |  str | None,
    self_gender_val: str | None) -> bool:
    """
    Does a user w/ self_gender_val satisfy someone else's preference?
    """
    if not preferences:
        return True
    
    pref_list = preferences if isinstance(preferences, list) else [preferences]
    
    if "everyone" in pref_list:
        return True
    if self_gender_val is None:
        return False
    
    mapped = _SELF_TO_PREFERENCE.get(self_gender_val)
    if mapped is None:
        return False
    return mapped in pref_list

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
        '''User has no non-zero weights. Return 0. Cannot rank candidates
        if the user hasn't said to us what they want. Caller should detect this conditon
        and prompt the user to set preferences'''
        return 0.0
    
    return weighted_sum / total_weight

'''
 ---------------------------------------------------------------------------
 Per match type scorers:
 
    receiver = user whose queue we are populating.
    candidate = the person being scored as a potential match for the receiver
 ---------------------------------------------------------------------------
 '''
 
 
def score_romantic(
    receiver: dict,
    receiver_prefs: dict, 
    candidate: dict,
    candidate_prefs: dict,
    weights: dict[str, float]) -> float:
    '''romantic compatability score'''

    #hard filter: gender preference
    receiver_gender = receiver.get("gender")
    candidate_gender = candidate.get("gender")
    
    if not _gender_satisfies(
        receiver_prefs.get("interested_in_genders"),
        candidate_gender,
    ):
        return 0.0
    if not _gender_satisfies(
        candidate_prefs.get("interested_in_genders"),
        receiver_gender,
    ):
        return 0.0
    #hard filter: graduation year (reciever specifys min/max grad year)
    
    candidate_grad = candidate.get("graduation_year")
    if candidate_grad is not None:
        r_min = receiver_prefs.get("min_grad_year")
        r_max = receiver_prefs.get("max_grad_year")
        if r_min is not None and candidate_grad < r_min:
            return 0.0
        if r_max is not None and candidate_grad > r_max:
            return 0.0
    receiver_grad = receiver.get("graduation_year")
    if receiver_grad is not None:
        c_min = candidate_prefs.get("min_grad_year")
        c_max = candidate_prefs.get("max_grad_year")
        if c_min is not None and receiver_grad < c_min:
            return 0.0
        if c_max is not None and receiver_grad > c_max:
            return 0.0
    
    #hard filter: height (SYMEMETRIC), stores as inches
    
    candidate_height = candidate.get("height")
    if candidate_height is not None:
        r_h_min = receiver_prefs.get("min_preferred_height")
        r_h_max = receiver_prefs.get("max_preferred_height")
        
        if r_h_min is not None and candidate_height < r_h_min:
            return 0.0
        if r_h_max is not None and candidate_height > r_h_max:
            return 0.0
    receiver_height = receiver.get("height")
    if receiver_height is not None:
        c_h_min = candidate_prefs.get("min_preferred_height")
        c_h_max = candidate_prefs.get("max_preferred_height")
        if c_h_min is not None and receiver_height < c_h_min:
            return 0.0
        if c_h_max is not None and receiver_height > c_h_max:
            return 0.0
    
    field_scores = {
        "major": exact_match(receiver.get("major"), candidate.get("major")),
        "clubs": jaccard(receiver.get("clubs"), candidate.get("clubs")),
        "interests": jaccard(receiver.get("interests"), candidate.get("interests")),
        "varsity_sports": jaccard(
            receiver.get("varsity_sports"), candidate.get("varsity_sports")
        ),
        "bar": exact_match(receiver.get("favorite_bar"), candidate.get("favorite_bar")),
        "going_out": bool_match(
            receiver.get("likes_going_out"), candidate.get("likes_going_out")
        ),
        "smoking": bool_match(receiver.get("smokes"), candidate.get("smokes")),
        "nicotine": bool_match(
            receiver.get("nicotine_lover"), candidate.get("nicotine_lover")
        ),
        "searching_for": exact_match(
            receiver.get("romantically_searching_for"),
            candidate.get("romantically_searching_for"),
        )
    }
    return _weighted_score(field_scores, weights)

def score_roommate(
    receiver: dict,
    receiver_prefs: dict,
    candidate: dict,
    candidate_prefs: dict,
    weights: dict[str, float]) -> float:
    #roommate compatibility score
    
    #filter: gender preference
    
    receiver_gender = receiver.get("gender")
    candidate_gender = candidate.get("gender")
    
    if not _gender_satisfies(
        receiver_prefs.get("roommate_gender_preference"),
        candidate_gender,
    ):
        return 0.0
    if not _gender_satisfies(
        candidate_prefs.get("roommate_gender_preference"),
        receiver_gender,
    ):
        return 0.0
    
    #filter: pet incompatability
    r_ok_with_pets = receiver_prefs.get("ok_with_pets")
    c_has_pets = candidate_prefs.get("has_pets")
    if r_ok_with_pets is False and c_has_pets is True:
        return 0.0
    
    
    field_scores = {
        "major": exact_match(receiver.get("major"), candidate.get("major")),
        "clubs": jaccard(receiver.get("clubs"), candidate.get("clubs")),
        "interests": jaccard(receiver.get("interests"), candidate.get("interests")),
        "bar": exact_match(receiver.get("favorite_bar"), candidate.get("favorite_bar")),
        "going_out": bool_match(
            receiver.get("likes_going_out"), candidate.get("likes_going_out")
        ),
        "smoking": bool_match(receiver.get("smokes"), candidate.get("smokes")),
        "nicotine": bool_match(
            receiver.get("nicotine_lover"), candidate.get("nicotine_lover")
        ),
        "varsity_sports": jaccard(
            receiver.get("varsity_sports"), candidate.get("varsity_sports")
        ),
        "sleep_schedule": exact_match(
            receiver_prefs.get("sleep_schedule"),
            candidate_prefs.get("sleep_schedule"),
        ),
        "cleanliness": inverse_distance(
            receiver_prefs.get("cleanliness"),
            candidate_prefs.get("cleanliness"),
            max_range = 4 #scale is 1 - 5
        ),
        "noise_tolerance": inverse_distance(
            receiver_prefs.get("noise_tolerance"),
            candidate_prefs.get("noise_tolerance"),
            max_range = 4,
        ),
        "guests_frequency": exact_match(
            receiver_prefs.get("guests_frequency"),
            candidate_prefs.get("guests_frequency"),
        ),
        "on_campus": bool_match(
            receiver_prefs.get("on_campus"),
            candidate_prefs.get("on_campus"),
        )
    }
    return _weighted_score(field_scores, weights)

INBOUND_LIKE_BONUS = 0.15
"""
flat bonus if the candidate has already likes the reciever.

Max unboosted score is 1.0, with the bonus a perfect inbound like reaches 1.15
mediorce matches be boosted past perfect cold ones
"""

_SCORERS: dict[str, Callable] = {
    "romantic": score_romantic,
    "roommate": score_roommate,
}

def score(
    receiver: dict,
    receiver_prefs: dict,
    candidate: dict,
    candidate_prefs: dict,
    match_type: str,
    weights: dict[str, float],
    candidate_liked_receiver: bool = False) -> float:
    
    """
    scoring entry point
    
    expected shapes:
    receiver / candidate (from profiles):
    gender, graduation_year, major, clubs, favorite_bar, likes_going_out, smokes
    
    receiver_prefs / candidate_prefs for match_type = 'romantic':
    interested_in_genders, min_grad_year, max_grad_year, priority_weights
    
    receiver_prefs / candidate_prefs for match_type = 'roommate':
    roommate_gender_preference, sleep_schedule, cleanliness, noise_tolerance, has_pets,
    ok_with_pets, guests_frequency, on_campus, priority_weights
    
    returns float in [0, 1.15] . 0 = hard filter rejection or zero alignment
    """
    
    scorer = _SCORERS.get(match_type)
    if scorer is None:
        raise ValueError(f"Unknown match_type: {match_type!r}")
    
    base = scorer(receiver, receiver_prefs, candidate, candidate_prefs, weights)
    if candidate_liked_receiver:
        base += INBOUND_LIKE_BONUS
    return base
    
