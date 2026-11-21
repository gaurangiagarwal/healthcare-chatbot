"""Small, curated public first-aid guides with explicit sources and review dates."""
from datetime import date

REVIEWED = date(2026, 11, 21)

GUIDES = {
    "burns": {
        "title": "Burns and scalds", "category": "Injury", "situation": "A thermal burn or scald has occurred.",
        "warning_signs": ["Deep or large burn", "Burn to face, hands, feet or genitals", "Electrical or chemical burn", "Possible smoke inhalation"],
        "immediate_actions": ["Make sure the area is safe and stop exposure to the heat source.", "For a small thermal burn, cool the area with cool running water while keeping the rest of the person warm.", "Remove jewellery and clothing near the burn only if it is not stuck.", "Cover loosely with a clean, non-fluffy dressing or cloth."],
        "avoid": ["Do not use ice, butter, oils, toothpaste or household pastes.", "Do not pull away material stuck to skin or break blisters.", "Do not delay emergency care for a serious burn."],
        "when_emergency": "Call 112 for a large, deep, electrical or chemical burn, a burn to a sensitive area, or possible inhalation injury.",
        "source_name": "World Health Organization — Burns", "source_url": "https://www.who.int/news-room/fact-sheets/detail/burns",
    },
    "bleeding": {
        "title": "Severe external bleeding", "category": "Injury", "situation": "Blood is flowing continuously, spurting, or the amount appears life-threatening.",
        "warning_signs": ["Continuous or spurting blood", "A large amount of blood", "Faintness, confusion, pale/cold skin or collapse"],
        "immediate_actions": ["Check that the scene is safe; use gloves or a barrier if available.", "Call 112 for severe bleeding.", "Apply firm, direct pressure over the wound with clean gauze or cloth and keep pressure on it.", "Stay with the person and watch their breathing and responsiveness until help arrives."],
        "avoid": ["Do not remove an object embedded in the wound.", "Do not lift the dressing repeatedly to check; maintain pressure.", "Do not use a tourniquet or pack a wound unless trained and using appropriate equipment."],
        "when_emergency": "Call 112 immediately for severe, uncontrolled or spurting bleeding, or if the person becomes faint or unresponsive.",
        "source_name": "American Red Cross — Life-threatening external bleeding", "source_url": "https://www.redcross.org/take-a-class/resources/learn-first-aid/bleeding-life-threatening-external",
    },
    "choking": {
        "title": "Choking (adult)", "category": "Emergency", "situation": "An adult suddenly has trouble breathing while eating or after an object enters the airway.",
        "warning_signs": ["Unable to speak or breathe", "Ineffective or silent cough", "Blue/grey colour or becoming unresponsive"],
        "immediate_actions": ["If the person can cough effectively, encourage them to keep coughing and watch closely.", "If they cannot breathe or cough effectively, call 112 and use speakerphone if possible.", "If trained, follow the current adult choking first-aid steps while emergency help is coming."],
        "avoid": ["Do not perform blind finger sweeps.", "Do not use adult choking manoeuvres on an infant.", "Do not delay calling 112 when obstruction is severe."],
        "when_emergency": "Call 112 immediately for severe choking, loss of consciousness or breathing difficulty. A person who becomes unresponsive needs emergency care.",
        "source_name": "Resuscitation Council UK — First Aid Guidelines 2025", "source_url": "https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/first-aid-guidelines",
    },
    "fractures": {
        "title": "Suspected fracture", "category": "Injury", "situation": "A bone injury is suspected after a fall, impact or accident.",
        "warning_signs": ["Severe pain, swelling or deformity", "Bone visible through a wound", "Numbness, coldness or colour change beyond the injury", "Possible neck, back, hip or major leg injury"],
        "immediate_actions": ["Keep the injured area as still as possible in the position found.", "Support it with nearby soft padding if this can be done without moving it.", "For an open wound, cover it loosely with a clean dressing; seek urgent care."],
        "avoid": ["Do not try to straighten the limb or push a bone back in.", "Do not move someone with a possible spine, hip or severe leg injury unless there is immediate danger."],
        "when_emergency": "Call 112 for a severe injury, visible bone, suspected spine/hip injury, severe pain, shock or inability to move the person safely.",
        "source_name": "NHS — Broken leg and emergency guidance", "source_url": "https://www.nhs.uk/conditions/broken-leg/",
    },
    "seizures": {
        "title": "Seizure", "category": "Emergency", "situation": "Someone is having a seizure or convulsion.",
        "warning_signs": ["First known seizure", "Seizure lasting over five minutes or longer than usual", "Repeated seizures without recovery", "Injury, breathing difficulty or failure to regain consciousness"],
        "immediate_actions": ["Move nearby hazards away and protect the person's head with something soft.", "Note when the seizure starts and stay with the person.", "When movements stop, check breathing and follow emergency call-handler instructions."],
        "avoid": ["Do not restrain the person.", "Do not put anything in their mouth or give food, drink or medicine during the seizure.", "Do not move them unless they are in immediate danger."],
        "when_emergency": "Call 112 for a first seizure, a prolonged or repeated seizure, serious injury, breathing difficulty or failure to regain consciousness.",
        "source_name": "NHS — What to do if someone has a seizure", "source_url": "https://www.nhs.uk/symptoms/what-to-do-if-someone-has-a-seizure-fit/",
    },
    "stroke": {
        "title": "Stroke warning signs (FAST)", "category": "Emergency", "situation": "A person may suddenly have face, arm, speech, vision or balance changes.",
        "warning_signs": ["Face drooping", "Weakness or numbness in one arm or one side", "Slurred or confused speech", "Sudden vision, balance or severe headache changes"],
        "immediate_actions": ["Call 112 immediately and note the time symptoms began or when the person was last well.", "Stay with the person and monitor breathing and responsiveness.", "Tell the emergency operator what changed and when."],
        "avoid": ["Do not wait to see if symptoms pass.", "Do not give food, drink or medication unless instructed by a clinician or emergency operator.", "Do not drive the person yourself if emergency services advise otherwise."],
        "when_emergency": "Any sudden stroke warning sign needs emergency assessment now, even if it improves.",
        "source_name": "NHS — Symptoms of a stroke", "source_url": "https://www.nhs.uk/conditions/stroke/symptoms/",
    },
    "cardiac": {
        "title": "Possible cardiac emergency", "category": "Emergency", "situation": "A person has sudden chest pressure/pain or related serious symptoms.",
        "warning_signs": ["Chest pressure, squeezing or pain", "Pain spreading to arm, neck or jaw", "Severe breathlessness, sweating, collapse or unresponsiveness"],
        "immediate_actions": ["Call 112 and follow the operator's instructions.", "Help the person rest in a comfortable position and stay with them.", "Watch breathing and responsiveness while help is coming."],
        "avoid": ["Do not leave the person alone or drive them yourself during a severe event.", "Do not give medication unless it is their own prescribed medicine or an emergency professional directs it."],
        "when_emergency": "Call 112 immediately for sudden chest pain/pressure, severe breathing trouble, collapse or unresponsiveness.",
        "source_name": "NHS — Heart attack", "source_url": "https://www.nhs.uk/conditions/heart-attack/",
    },
    "allergic-reaction": {
        "title": "Severe allergic reaction", "category": "Emergency", "situation": "A reaction includes breathing difficulty, throat/tongue swelling or collapse.",
        "warning_signs": ["Difficulty breathing or wheezing", "Swelling of tongue or throat", "Collapse, faintness or rapidly worsening symptoms"],
        "immediate_actions": ["Call 112 immediately.", "If the person has their own prescribed auto-injector, help them use it according to its instructions if they ask or you are trained.", "Stay with them, monitor breathing and follow the emergency operator's directions."],
        "avoid": ["Do not delay emergency care even if symptoms improve.", "Do not give someone else's medication."],
        "when_emergency": "Breathing difficulty, throat/tongue swelling or collapse needs emergency help now.",
        "source_name": "American Red Cross — Allergic reaction/anaphylaxis", "source_url": "https://www.redcross.org/take-a-class/resources/learn-first-aid/allergic-reaction-anaphylaxis",
    },
}

for guide in GUIDES.values():
    guide["last_reviewed"] = REVIEWED.isoformat()
    guide["disclaimer"] = "General public first-aid information, not a diagnosis or a substitute for emergency services or professional training. In India, call 112 for emergencies."


def get_first_aid_guide(category):
    key = category.lower().replace(" ", "-").strip()
    aliases = {"burn": "burns", "bleed": "bleeding", "fracture": "fractures", "seizure": "seizures", "stroke-warning-signs": "stroke", "cardiac-emergency": "cardiac", "allergy": "allergic-reaction"}
    key = aliases.get(key, key)
    guide = GUIDES.get(key)
    return {**guide, "slug": key} if guide else None


def list_first_aid_guides():
    return [{"slug": slug, "title": guide["title"], "category": guide["category"], "situation": guide["situation"], "last_reviewed": guide["last_reviewed"]} for slug, guide in GUIDES.items()]
