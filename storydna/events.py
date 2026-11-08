"""Rule-based narrative-event tagger.

Each beat (sentence) is tagged with zero or more *story events* (concealed identity, public
reveal, humiliation, ...). Comparing ORDERED sequences of rare events is what lets StoryDNA
separate "same chain of plot events" from "same genre trope".

The lexicon is hand-written and English-only. It is the main limitation of the no-LLM baseline:
a story whose events are not in the lexicon is only compared lexically. The LLM stage
(storydna.llm) exists to cover that gap.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FLAGS = re.IGNORECASE


@dataclass(frozen=True)
class EventRule:
    label: str
    patterns: tuple[str, ...]
    unless: tuple[str, ...] = ()
    description: str = ""


def _r(label: str, patterns: list[str], unless: list[str] | None = None, description: str = "") -> EventRule:
    return EventRule(label, tuple(patterns), tuple(unless or ()), description)


RULES: list[EventRule] = [
    _r("HIDDEN_IDENTITY", [
        r"\b(?:poses?|posing|posed|disguis\w+|masquerad\w+|incognito|undercover)\b",
        r"\bpretend\w*\b(?!.{0,40}\b(?:girlfriend|boyfriend|couple|confus\w*|still|lover|wife|husband)\b)",
        r"\b(?:conceal\w*|hides?|hid|hiding)\b.{0,40}\b(?:wealth|identity|status|fortune|heir\w*|real name)\b",
        r"\b(?:takes?|took|starts?|joins?|joined|accepts?)\b.{0,25}\b(?:job|work|position)\b.{0,50}\b(?:own (?:company|firm|business|tower)|to (?:test|see|find out|learn|check))\b",
        r"\bunder (?:a|an|her|his|their|another)\b.{0,12}\b(?:false|new|another|different|assumed|fake|maiden)\b.{0,10}\bname\b",
        r"\busing (?:her|his) .{0,15}maiden name\b",
        r"\bsecretly (?:is|was|owns?|holds?|runs?)\b",
        r"\bdeliver\w* food\b",
    ], unless=[r"\bclause\b"], description="a character conceals who they really are / how wealthy they are"),
    _r("PUBLIC_REVEAL", [
        r"\b(?:reveal\w*|announce\w*|unveil\w*|expos\w*|confess\w*|plays?|shows?|runs?|screens?|reads?|rips?|tears? up)\b.{0,90}\b(?:in front of|before|during|on (?:the )?(?:big|live|stage|screen)|to (?:everyone|the (?:whole )?(?:crowd|room|guests|board))|live|gala|ceremony|reception|wedding|party|meeting|launch|reunion|anniversary|dinner|stage|conference|concert|broadcast|studio|crowd|audience|guests|everyone|hall)\b",
        r"\bwalks? (?:in|on stage)\b",
        r"\bat (?:the|an|her|his|their)\b.{0,30}\b(?:gala|party|dinner|meeting|launch|ceremony|reception|concert|banquet|reopening|wedding|anniversary|reunion|reading)\b.{0,60}\b(?:reveal|expos|announce|plays?|shows?|walks?|sings?|reads?|confess|tears?|names?)\w*",
    ], description="secret / evidence / identity exposed in front of an audience"),
    _r("HUMILIATION", [
        r"\b(?:mock\w*|ridicul\w*|humiliat\w*|insult\w*|sneer\w*|shame[sd]?|belittl\w*|taunt\w*|bull(?:y|ied|ies)|laugh\w* at|looks? down on|look(?:ed)? down on|scold\w*|criticis\w*|disgrace|embarrass\w*|shout\w* at|useless|fault with|treats? (?:him|her|them) like|orders? (?:him|her) about|refuse[sd]? to let him eat)\b",
    ], description="a character is publicly belittled"),
    _r("BETRAYAL", [
        r"\b(?:affair|cheat\w*|betray\w*|elope\w*|runs? (?:away )?with|disappears? with|leaves? (?:her|him) for|sells? (?:her|his) .{0,25} behind|stab\w*|double[- ]cross\w*)\b",
        r"\bhaving an affair\b",
    ], description="partner or friend betrays the protagonist"),
    _r("REJECTION_EXPULSION", [
        r"\b(?:left at the (?:altar|mandap)|standing at the (?:altar|mandap)|jilted|divorc\w*|rejects?|rejected|banish\w*|exile\w*|thrown out|throws? (?:her|him) out|kicked out|fired|loses? (?:her|his) (?:job|licen[cs]e)|licen[cs]e (?:is )?cancel\w*|expelled|evict\w*|dumped|abandon\w*|leaves? (?:her|him) with nothing|banned)\b",
    ], description="protagonist is cast out, divorced, fired or rejected"),
    _r("CONTRACT_ARRANGEMENT", [
        r"\b(?:contract\w*|paper marriage|marriage on paper|fake (?:marriage|girlfriend|boyfriend|relationship)|hired .{0,40}pretend|pretend\w* .{0,30}(?:girlfriend|boyfriend|couple)|arranged marriage|agrees? to a (?:paper|fake|sham) )\b",
        r"\b(?:paper|sham) marriage\b|\bon paper\b",
    ], description="relationship or service governed by a contract / arrangement"),
    _r("REBIRTH_TIME", [
        r"\b(?:reborn|reincarnat\w*|rebirth|time[- ]loop|relives?|reliv\w+|transmigrat\w*|same \w+ day every)\b",
        r"\bwakes? (?:up )?(?:\w+ ){0,4}(?:years?|months?|days?) (?:earlier|before|in the past|ago)\b",
        r"\b(?:three|two|five|ten|\d+) years? (?:earlier|in the past)\b",
        r"\bopens? her eyes\b.{0,30}\bearlier\b",
        r"\bwakes? (?:up )?inside (?:it|the novel|a novel|the book)\b",
        r"\bfalls? asleep over a (?:web )?novel\b",
    ], description="rebirth / second chance / time loop / transmigration"),
    _r("AMNESIA", [
        r"\bamnesia\b",
        r"\b(?:erases?|loses?|lost|wipes?|recover\w*|regain\w*)\b.{0,20}\bmemory\b",
        r"\bmemory (?:returns?|loss)\b",
        r"\bno memory\b",
        r"\bhis own handwritten\b.{0,30}\bnotebook\b",
    ], unless=[r"memory of the (?:future|past)"], description="character loses and later regains memory"),
    _r("FAKED_DEATH", [
        r"\bfak(?:ed|es|ing)? (?:his|her|their) (?:own )?death\b",
        r"\bpretend\w* to be dead\b|\bpresumed dead\b|\bsupposedly dead\b",
    ], description="someone fakes their death"),
    _r("SECRET_CHILD", [
        r"\b(?:pregnan\w*|twins?|paternity|newborn|custody|baby(?:'s)? father|father of (?:her|his))\b",
    ], description="secret pregnancy / hidden children / paternity"),
    _r("IDENTITY_SWAP", [
        r"\b(?:swap\w*|switch\w*|exchang\w*)\b.{0,60}\b(?:birth|baby|babies|infants?|newborns?|nurses?|hospital)\b",
        r"\bstand(?:s|ing)? in for\b|\btakes? (?:her|his) place\b|\bimpersonat\w+|\bplays? the part\b|\bkeeps? up the act\b",
        r"\b(?:birth)\b.{0,40}\b(?:swap|switch)\w*",
    ], description="babies swapped at birth / one person takes another's place"),
    _r("DNA_TEST", [r"\b(?:dna|genetic test|paternity test|blood (?:test|matches)|birthmark)\b"],
       description="biological relationship proven by test or mark"),
    _r("FRAMED", [
        r"\b(?:fram(?:e|ed|es|ing)|scapegoat\w*|falsely accus\w*|blamed for|wrongly accused|blames?)\b",
    ], description="protagonist is blamed for someone else's act"),
    _r("EVIDENCE", [
        r"\b(?:record(?:s|ed|ing|ings|er)?|evidence|proof|diary|diaries|ledger|documents?|paperwork|footage|laptop|confession|tapes?|forged?)\b",
        r"\bhidden phone\b|\bdated (?:notes|sketch\w*)\b|\bkeeps? dated\b",
    ], description="documentary evidence is gathered"),
    _r("THEFT_FRAUD", [
        r"\b(?:steal\w*|stole\w*|stolen|siphon\w*|embezzl\w*|fraud\w*|bribe\w*|bribing|takes? (?:the )?credit|passes? off|as (?:his|her) own|drain\w*|sabotag\w*|swindl\w*|forg\w+)\b",
    ], description="theft of credit, money, recipes or property"),
    _r("BUSINESS_PRESSURE", [
        r"\b(?:rival|take ?over|buy(?:s|ing)? (?:up|out)|bankrupt\w*|collaps\w*|going under|failing|losing money|debts?|loans?|creditors?|loan shark|overdue|rent|mortgage|owes?|owing|struggling)\b",
    ], description="debt, rival firm, collapse or financial pressure"),
    _r("COMEBACK_BUILD", [
        r"\b(?:builds?|rebuilds?|opens?|launch\w*|founds?|sets? up|starts? (?:selling|her own|his own|a rival))\b.{0,50}\b(?:rival|own (?:restaurant|brand|company|business|eatery|firm|cart)|new (?:name|brand)|cart|stall|bakery|bookshop|brand|studio|eatery)\b",
        r"\bstarts? selling\b|\bselling \w+ from\b",
    ], description="protagonist rebuilds something of their own after a fall"),
    _r("BEGGING_APOLOGY", [
        r"\b(?:begs?|beg|begging|pleads?|pleaded|grovel\w*|apolog\w*|sorry|forgiv\w*|second chance|admit\w*|asks? (?:for )?(?:a )?(?:place|stall|job))\b",
    ], description="antagonist begs, apologises or must admit fault"),
    _r("SUPERNATURAL", [
        r"\b(?:werewol\w*|wolf|wolves|pack|alpha|vampire|moon goddess|full moon|goddess|rogue|castle|ghost|spirit|magic\w*|coronation|dragon)\b",
    ], description="supernatural / fantasy world"),
    _r("CRIME_VIOLENCE", [
        r"\b(?:mafia|gangster|crime boss|mob|loan shark|kidnap\w*|abduct\w*|ransom|murder\w*|kill\w*|poison\w*|arrest\w*|police|detective|smuggl\w*)\b",
    ], description="crime, violence or law enforcement"),
    _r("FIRE_ACCIDENT", [
        r"\b(?:fire|blaze|arson\w*|crash\w*|accident|lightning|meteor|explosion|landslide)\b",
    ], description="fire, crash or other accident"),
    _r("INHERITANCE", [
        r"\b(?:inherit\w*|testament|heirs?|heiress|trustee|trust fund|trust|clause|the will|a will|her will|his will|legacy|bequeath\w*)\b",
    ], description="inheritance or will"),
    _r("FAMILY_PRESSURE", [
        r"\b(?:mother-in-law|father-in-law|stepmother|stepbrother|aunts?|relatives|in-laws|sisters?-in-law|brothers?-in-law|family dinner)\b",
    ], description="in-laws or relatives pressure the protagonist"),
    _r("ROMANTIC_TURN", [
        r"\b(?:falls? (?:in love|for)|fell for|kiss\w*|real feelings|become real|grown into something real|marry (?:him|her) for real|asks? .{0,12}to marry|proposes?|stopped pretending|befriends?|starts? to trust|slowly trusts?|trusts? (?:him|her))\b",
    ], description="relationship deepens into real feelings"),
    _r("SECRET_HELP", [
        r"\b(?:quietly|secretly) (?:pays?|covers?|settles?|buys?|agrees?|donates?|helps?|sends?)\b",
        r"\bwithout a word\b",
    ], description="a character helps in secret"),
    _r("CONTEST_WIN", [
        r"\b(?:wins?|won|beats?|prevails?|champion\w*|contest|competition|tournament|olympiad|cook-off|cooking duel|showdown|final)\b",
    ], description="competition, contest or showdown"),
    _r("VIRAL_FAME", [r"\b(?:viral|blows? up|vlogger|blogger|posts? a clip)\b"], description="goes viral"),
    _r("ILLNESS_MEDICAL", [
        r"\b(?:dying|terminally|ill|sick|kidney|transplant|surgery|surgeon|hospital|patient|operating|operation|clinic|nurse)\b",
    ], description="illness or medical setting"),
    _r("LOYALTY_TEST", [
        r"\b(?:stands? by|stood by|refuses? to leave|tests? (?:whether|his|her)|to test|loyalty|whether (?:she|he) (?:loves|wants|can trust))\b",
    ], description="one character tests another's loyalty or love"),
    _r("CONFRONTATION", [r"\b(?:confronts?|confronted|demands?|challenges?|dares?|storms? into)\b"],
       description="direct confrontation"),
    _r("COMEUPPANCE", [
        r"\b(?:is|are) (?:arrested|removed|escorted out|thrown out|evicted)\b|\bsigns? over\b|\bforced to (?:share|admit|apolog)\w*|\bhas to (?:admit|apolog\w*|say sorry)\b|\bescorted out\b|\bevicted\b",
    ], description="antagonist faces consequences"),
]

_COMPILED = [
    (r.label, [re.compile(p, _FLAGS) for p in r.patterns], [re.compile(u, _FLAGS) for u in r.unless])
    for r in RULES
]
EVENT_LABELS = [r.label for r in RULES]
EVENT_DESCRIPTIONS = {r.label: r.description for r in RULES}


def tag_beat(sentence: str, max_events: int = 7) -> list[str]:
    """Return event labels found in one beat, ordered by first position in the sentence."""
    found: list[tuple[int, str]] = []
    for label, pats, unless in _COMPILED:
        if any(u.search(sentence) for u in unless):
            continue
        best = None
        for p in pats:
            m = p.search(sentence)
            if m and (best is None or m.start() < best):
                best = m.start()
        if best is not None:
            found.append((best, label))
    found.sort()
    return [lbl for _, lbl in found[:max_events]]
