"""Differentiation suggestions: "this pitch overlaps an existing story - how could it become more original?"

Three parts, all attached to a High/Medium candidate:
  1. rewrite_preview  - computed by the scorer itself: re-score the pitch with the overlapping beats REMOVED, one beat at a
                        time and all together. It is a what-if estimate (a floor: replacement beats could add other
                        similarities), not a promise. Tells the writer which beats matter most.
  2. beat_fixes / angles - hand-written writer prompts ("What if ...") chosen from the events that actually matched, plus
                        structural levers. Deterministic, offline, no model.
  3. model_ideas      - optional: the swappable model proposes fresh angles; every idea is validated (length, beat numbers in
                        range, not copied from the existing story). Mock-tested only.
Nothing here changes any score or tier.
"""
from __future__ import annotations

import hashlib
import json
import re

from .textproc import STOPWORDS, split_sentences

# ----------------------------------------------------------------------------------------- idea bank
IDEAS: dict[str, list[str]] = {
    "HIDDEN_IDENTITY": [
        "Keep a secret, but change what is hidden: not wealth or rank, but a talent, a past crime, a promise made to someone, or a skill the others would be shocked by.",
        "Let the audience know the secret from episode 1 and build the tension around who might find out, instead of saving it for a late reveal.",
        "Flip it: the person who looks down on the hero is the one hiding something bigger."],
    "PUBLIC_REVEAL": [
        "Let the truth come out privately (a one-to-one talk, a voice note, a letter) and make the cost slow and personal instead of a crowd moment.",
        "Have the truth come out through someone with nothing to gain, such as a child, a driver or an old servant, so it feels discovered rather than staged.",
        "Keep the public scene but take away the hero's control: someone else forces the reveal early and the hero has to deal with the mess."],
    "HUMILIATION": [
        "Replace the loud insult with quiet exclusion: forgotten invitations, a seat that is 'not available', a nickname that sticks.",
        "Make the humiliation come from someone the hero loves and who means well, so the pain is complicated instead of villain-versus-hero.",
        "Show the hero's response before the insult ends, so the scene is about their choice, not the bully's cruelty."],
    "BETRAYAL": [
        "Make the betrayal a hard choice, not greed: the betrayer is protecting someone, and the audience half understands them.",
        "Reveal that the 'betrayal' was a misunderstanding or a trap set by a third person, so the real enemy is somewhere else.",
        "Let the hero betray first, for a good reason, and watch the consequences come back."],
    "REJECTION_EXPULSION": [
        "Let the hero walk away on their own terms instead of being thrown out, so the opening is a decision, not a punishment.",
        "Make the rejection come from an institution (a college, a panchayat, a cricket board) rather than a family or a partner.",
        "Delay the expulsion: the hero knows it is coming and uses the last days to quietly set up what happens next."],
    "CONTRACT_ARRANGEMENT": [
        "Swap the paper marriage for another arrangement with a clock: a six-month business partnership, a guardian deal, or a joint caretaker promise.",
        "Make the contract the hero's idea, not the family's, and give the other person a reason to want out.",
        "Put the terms on screen early and let each episode break one of them."],
    "REBIRTH_TIME": [
        "Give the second chance a price: the hero can change one thing, but each change erases something they love.",
        "Make only a small piece of knowledge travel back (a name, a date, a smell) so the hero has to be clever, not all-knowing.",
        "Drop the rebirth and use the same theme with a pause instead: a coma, a long journey or a lost decade."],
    "AMNESIA": [
        "Let the hero remember everything except one person, and make that gap the mystery.",
        "Make the forgetting chosen: the hero agrees to forget something painful and slowly realises what was taken.",
        "Give the amnesia to the villain instead, and watch the hero decide whether to take revenge on someone who is genuinely changed."],
    "FAKED_DEATH": [
        "Keep the 'death' but make it the hero's secret exit from a family trap, with a living person quietly helping.",
        "Show who benefits from the death announcement, and make that the real story rather than the return.",
        "Replace the faked death with a faked disappearance that the family pretends not to notice."],
    "SECRET_CHILD": [
        "Make the child know the truth first, and let the child steer the adults.",
        "Move the secret from parentage to a different family bond: a hidden sibling, a hidden guardian, an adopted grandparent.",
        "Show the cost of keeping the secret for years (money, lies, a missed life) instead of focusing on the day it comes out."],
    "IDENTITY_SWAP": [
        "Make the swap partial: two people share one role (one job, one name) but not one life.",
        "Let the swapped person choose to stay swapped when the truth is offered.",
        "Move the swap from birth to adulthood: a stand-in at an exam, an interview or a wedding."],
    "DNA_TEST": [
        "Replace the lab proof with a human proof: a lullaby, a recipe, a scar story, someone's memory.",
        "Let the test result be ambiguous and force the family to decide what they believe.",
        "Have the hero refuse to take the test, and build the story on trust instead of proof."],
    "FRAMED": [
        "Let the hero be partly guilty, so clearing their name needs honesty, not only evidence.",
        "Make the framer someone with a sympathetic reason, and let the hero discover it halfway.",
        "Put the 'trial' in an unusual forum (a village meeting, a hostel council, an office HR panel) with its own rules."],
    "EVIDENCE": [
        "Replace the diary/recording/laptop with a person who knows the truth and has to be persuaded to speak.",
        "Make the evidence wrong or incomplete at first, so the hero must investigate further.",
        "Let the hero have no proof at all and win through patience and pressure on the right person."],
    "THEFT_FRAUD": [
        "Make what is stolen something that cannot be proved stolen: an idea, a style, a reputation, a friendship.",
        "Let the thief be the hero's mentor, so catching them means losing something personal.",
        "Turn it around: the hero 'steals' back what was theirs, and the audience has to decide if that is fair."],
    "BUSINESS_PRESSURE": [
        "Move the pressure from money to time or reputation: a deadline, a licence renewal, a viral accusation.",
        "Replace the rival firm with a system (a bank rule, a government scheme, an app algorithm) that the hero must outsmart.",
        "Let the family business be saved by something small and local, not a rescue investor."],
    "COMEBACK_BUILD": [
        "Make the new venture different from the old one (a different trade, a different city) so it is a fresh start, not a rival copy.",
        "Let the hero fail once in the rebuild before succeeding, with a lesson that comes from the failure.",
        "Share the comeback: the hero builds it with the people they once ignored."],
    "BEGGING_APOLOGY": [
        "Deny the satisfying apology. Let the wrongdoer do something useful instead of saying sorry.",
        "Let the hero be the one who has to apologise in the end.",
        "Make the apology arrive too late or to the wrong person, and let the story deal with that."],
    "SUPERNATURAL": [
        "Keep one supernatural rule and make it strict and inconvenient (it only works at night, or costs a memory).",
        "Move the supernatural idea into local folklore the audience knows (a village legend, a family curse) rather than a generic fantasy world.",
        "Make the 'magic' ambiguous so it could be psychological, and let the viewers argue."],
    "CRIME_VIOLENCE": [
        "Reduce the violence and raise the stakes of choice: a bribe offered, a witness who may speak, a lawyer's trap.",
        "Move the crime from the main plot to the background and let the hero's problem be the aftermath.",
        "Let the criminal be a friend of the family and make the hero's loyalty the real test."],
    "FIRE_ACCIDENT": [
        "Replace the fire/crash with a slow disaster, like a leak, a debt or an illness, so there is no single dramatic day.",
        "Make the accident an accident, and the cover-up the real crime.",
        "Open after the incident and reveal what happened in pieces."],
    "INHERITANCE": [
        "Make the inheritance a burden (a debt, a failing shop, a promise to look after someone) instead of a prize.",
        "Replace the will with a non-money inheritance: a recipe, a name, a land dispute or a song.",
        "Let the hero refuse the inheritance, and make the others fight over why."],
    "FAMILY_PRESSURE": [
        "Make the pressure come from one relative who is secretly on the hero's side.",
        "Show the in-laws' reasons so the conflict is two sets of values, not good versus bad.",
        "Replace the family dinner scenes with another recurring setting: a festival, a shared kitchen, a WhatsApp group."],
    "ROMANTIC_TURN": [
        "Delay or deny the romance and let the central bond be friendship, rivalry or mentorship.",
        "Make the turn come through a shared task (a trip, a rescue, a deadline) instead of a speech.",
        "Let the second lead notice before the first does, and make the triangle about timing, not villainy."],
    "SECRET_HELP": [
        "Let the secret helper be caught early and punished, so the help has a visible cost.",
        "Make the helper's reason selfish at first and change it slowly.",
        "Make the help something money cannot buy, like a name vouching for them or a seat saved."],
    "CONTEST_WIN": [
        "Let the hero lose the contest but gain something more important, and show that in the last scene.",
        "Change the contest's format (a team event, a long season, a lottery) so the finish cannot be a one-on-one comeback.",
        "Make the opponent a friend and the real fight the hero's own doubt."],
    "VIRAL_FAME": [
        "Make the fame arrive before the hero is ready and show the cost (privacy, family, truth getting twisted).",
        "Let the viral moment be a mistake that someone else turns into a brand.",
        "Keep the hero offline and let the story show a village or a school reacting."],
    "ILLNESS_MEDICAL": [
        "Make the illness belong to a side character and use it to change a decision, not to drive the whole plot.",
        "Move the medical setting to a place that is not a big hospital (a mobile clinic, a pharmacy, a village ANM post).",
        "Show the family's daily routine around the illness rather than the dramatic diagnosis."],
    "LOYALTY_TEST": [
        "Let the person being tested find out and flip the test back on the tester.",
        "Make the loyalty test unintentional: life gives it, nobody sets it.",
        "Have the tested person fail once, and make the second chance the real story."],
    "CONFRONTATION": [
        "Replace the shouting match with a quiet scene where the hero says almost nothing and acts.",
        "Delay the confrontation by one episode and let the audience suffer the wait.",
        "Have the villain confront the hero first, and make the hero's answer the surprise."],
    "COMEUPPANCE": [
        "Give the antagonist a consequence that is not humiliation: losing a choice, a job, a role, a belief.",
        "Let the consequence arrive from the antagonist's own side (their friend, their child), not the hero.",
        "End with the antagonist partly redeemed, and let the hero decide how much to forgive."],
}

LEVERS = [
    ("Change who it happens to", "What if the same emotional situation happens between {rel} instead of a couple or boss and employee? The feelings stay, the beats cannot copy."),
    ("Change the world", "What if the story moves into {setting}? Keep the emotion, but the rules, props and people become new, and so do the scenes."),
    ("Change what is at stake", "What if the stake is not money or status but a promise, a reputation, a child's future or someone's health?"),
    ("Change the villain's reason", "What if the antagonist is not greedy or cruel but scared, loyal to the wrong person, or sure they are protecting the family?"),
    ("Change the shape of the ending", "What if the hero does not win in public? Try a quiet win, a win with a visible cost, or an ending where forgiveness (not revenge) is the twist."),
    ("Change the order", "What if you open with the biggest reveal and spend the series on how it happened, or let the audience know the secret from episode 1 while the hero does not?"),
    ("Add a constraint", "What if the hero cannot use the thing that wins in the other story (money, proof, a witness)? Force a smarter, stranger route."),
    ("Cross the genre", "What if one genre is added, like a mystery, a sports comeback or a folk-legend layer, so the middle of the story cannot follow the same path?"),
]
RELATIONSHIPS = ["siblings", "two childhood friends", "a mother and her grown daughter", "rival colleagues", "a teacher and a student",
                 "a grandparent and a grandchild", "business partners"]
SETTINGS = ["a village panchayat", "a film set", "a night ward in a small hospital", "a cricket academy", "a wedding-catering business",
            "a railway station", "a coaching institute", "a small-town newspaper", "a boarding school", "a fishing harbour",
            "a tailoring shop", "a truck-drivers' dhaba", "a radio station"]


def _h(s: str, n: int) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16) % n


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOPWORDS and len(w) > 2}


# ----------------------------------------------------------------------------------------- impact preview
def _rescore(index, beats: list[str], cand_idx: int):
    """Score `beats` as a pitch; return (candidate's entry or None, best entry)."""
    if len(beats) < 3:
        return None, None
    _q, _top, allr, _ = index.score("\n".join(beats), top_k=3)
    mine = next((r for r in allr if r["idx"] == cand_idx), None)
    return mine, (allr[0] if allr else None)


def rewrite_preview(index, pitch_beats: list[str], candidate: dict) -> dict | None:
    cand_idx = next(i for i, c in enumerate(index.cards) if c.story_id == candidate["candidate_id"])
    drop = [m["pitch_beat_index"] for m in candidate["matched_plot_beats"]
            if (m["events"] and not m["generic_trope_only"]) or m["beat_similarity"] >= 0.35]
    drop = sorted(set(i for i in drop if 0 <= i < len(pitch_beats)))[:5]
    if not drop:
        return None
    before = candidate["retrieval_score"]
    tiers = index.calib["tiers"] if index.calib else {"high": 0.8, "medium": 0.3}
    per_beat = []
    for i in drop:
        mine, _best = _rescore(index, [b for k, b in enumerate(pitch_beats) if k != i], cand_idx)
        if mine is not None:
            per_beat.append({"beat_index": i, "text": pitch_beats[i], "score_if_rewritten": mine["review_score"],
                             "drop": round(before - mine["review_score"], 4)})
    per_beat.sort(key=lambda x: -x["drop"])
    mine, best = _rescore(index, [b for k, b in enumerate(pitch_beats) if k not in set(drop)], cand_idx)
    if mine is None:
        return {"beats_to_rewrite": drop, "per_beat": per_beat, "note": "Too few beats would remain to estimate the effect."}
    return {
        "beats_to_rewrite": drop, "per_beat": per_beat,
        "before": {"score": before, "tier": candidate["review_priority"]},
        "after": {"score": mine["review_score"], "tier": mine["tier"]},
        "closest_after": {"id": index.cards[best["idx"]].story_id, "title": index.cards[best["idx"]].title,
                          "score": best["review_score"], "tier": best["tier"]},
        "tier_thresholds": tiers,
        "note": ("What-if estimate: the scorer re-run with these beats removed. Replacement beats could add new overlaps, so "
                 "re-check your rewrite in StoryDNA. Different words are not enough; the events and their order must change."),
    }


# ----------------------------------------------------------------------------------------- writer prompts
def _beat_fixes(index, candidate: dict, preview: dict | None) -> list[dict]:
    impact = {p["beat_index"]: p["drop"] for p in (preview or {}).get("per_beat", [])}
    ms = [m for m in candidate["matched_plot_beats"] if (m["events"] and not m["generic_trope_only"]) or m["beat_similarity"] >= 0.35]
    ms.sort(key=lambda m: -impact.get(m["pitch_beat_index"], 0))
    out = []
    for m in ms[:3]:
        events = [e for e in m["events"] if e in IDEAS] or [e for e in candidate["shared_distinctive_events"] if e in IDEAS]
        ideas = []
        for e in events[:2]:
            pool = IDEAS[e]
            k = _h(candidate["candidate_id"] + m["pitch_text"], len(pool))
            ideas.append({"event": e, "idea": pool[k]})
            if len(ideas) == 2:
                break
        if not ideas:
            ideas = [{"event": "", "idea": "Reach the same outcome by a different action in a different place, so neither the cause nor the setting matches the existing story."}]
        out.append({"pitch_beat_index": m["pitch_beat_index"], "pitch_text": m["pitch_text"],
                    "pitch_text_original": m.get("pitch_text_original", ""), "mirrors": m["candidate_text"],
                    "events": m["events"], "score_drop_if_rewritten": impact.get(m["pitch_beat_index"]), "ideas": ideas})
    return out


def _angles(candidate: dict, pitch_text: str, cand_text: str, n: int = 5) -> list[dict]:
    seen = _words(pitch_text) | _words(cand_text)
    rels = [r for r in RELATIONSHIPS if not (_words(r) & seen)] or RELATIONSHIPS
    sets = [s for s in SETTINGS if not (_words(s) & seen)] or SETTINGS
    base = _h(candidate["candidate_id"], len(LEVERS))
    out = []
    for k in range(len(LEVERS)):
        title, tpl = LEVERS[(base + k) % len(LEVERS)]
        idea = tpl.format(rel=rels[_h(candidate["candidate_id"] + title, len(rels))],
                          setting=sets[_h(candidate["candidate_id"] + title + "s", len(sets))])
        out.append({"title": title, "idea": idea})
        if len(out) == n:
            break
    return out


# ----------------------------------------------------------------------------------------- optional model
def llm_ideas(pitch_beats: list[str], cand_beats: list[str], events: list[str], adapter) -> dict:
    from .llm import AdapterError, _load_prompt, _numbered, _parse_json
    system, user_t = _load_prompt("differentiate.txt")
    user = (user_t.replace("{events}", ", ".join(events) or "none").replace("{pitch_beats}", _numbered(pitch_beats))
            .replace("{candidate_beats}", _numbered(cand_beats)))
    last = "unknown"
    for _ in range(2):
        try:
            raw = _parse_json(adapter.complete(system, user, max_tokens=1200))
        except AdapterError as e:
            return {"status": "error", "error": str(e), "ideas": []}
        except (ValueError, json.JSONDecodeError) as e:
            last = "unparseable model output (%s)" % e
            continue
        good, dropped = [], 0
        cand_sets = [_words(b) for b in cand_beats]
        for it in (raw.get("ideas") or [])[:8]:
            try:
                idea = str(it["idea"]).strip()
                why = str(it.get("why_less_similar", "")).strip()
                beats = [int(x) for x in (it.get("changes_beats") or []) if 0 <= int(x) < len(pitch_beats)]
            except (KeyError, TypeError, ValueError):
                dropped += 1
                continue
            iw = _words(idea)
            copied = any(cw and len(iw & cw) / max(1, len(cw)) >= 0.6 for cw in cand_sets)
            if not (6 <= len(idea.split()) <= 70) or copied or any(g["idea"].lower() == idea.lower() for g in good):
                dropped += 1
                continue
            good.append({"idea": idea, "changes_beats": beats, "why_less_similar": why})
        if len(good) >= 2:
            return {"status": "ok", "ideas": good[:5], "invalid_ideas_dropped": dropped}
        last = "fewer than 2 usable ideas (%d dropped)" % dropped
    return {"status": "error", "error": last, "ideas": []}


# ----------------------------------------------------------------------------------------- public
def suggest_for_candidate(index, candidate: dict, pitch_text: str, adapter=None) -> dict | None:
    """Return the differentiation block for a High/Medium candidate (None for Low / not assessed)."""
    if candidate["review_priority"] not in ("High", "Medium"):
        return None
    beats = split_sentences(pitch_text)
    card = index.by_id[candidate["candidate_id"]]
    preview = rewrite_preview(index, beats, candidate)
    fixes = _beat_fixes(index, candidate, preview)
    out = {
        "level": candidate["review_priority"],
        "headline": ("This pitch follows %s closely. Changing the beats below, not just the wording, is what lowers the overlap."
                     if candidate["review_priority"] == "High" else
                     "This pitch partly overlaps %s. A few changes to the beats below should make it clearly its own story.")
                    % ('"%s"' % card.title),
        "rewrite_preview": preview, "beat_fixes": fixes,
        "angles": _angles(candidate, pitch_text, card.synopsis),
        "model_ideas": None,
        "disclaimer": "Prompts for writers, not instructions. They are not guaranteed to make a pitch original; re-run StoryDNA on the rewrite.",
    }
    if adapter is not None and getattr(adapter, "name", "none") != "none":
        out["model_ideas"] = llm_ideas(beats, card.beats, candidate["shared_distinctive_events"], adapter)
    return out
