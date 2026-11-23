"""Small, reviewable answers for common general-health questions."""
import re


GENERAL_LIMIT = " This is general information, not a diagnosis or a substitute for a clinician."


def answer_known_question(message):
    text = " ".join((message or "").casefold().split())
    if re.search(r"\b(cardiologist|cardiac physician)\b", text) and re.search(r"\b(cardiac surgeon|cardiothoracic surgeon)\b", text):
        return (
            "A cardiologist is a physician who evaluates and treats heart and blood-vessel conditions, usually with medicines, tests, and non-surgical procedures. A cardiac surgeon performs operations on the heart or nearby blood vessels. They often work together, and which specialist is appropriate depends on the individual concern."
            + GENERAL_LIMIT
        )
    if re.search(r"\bwhat (?:is|does) an? mri\b|\bmri (?:scan|test)\b", text):
        return (
            "MRI (magnetic resonance imaging) uses a strong magnetic field and radio waves to create detailed images inside the body. It does not use X-rays. A clinician decides whether it is appropriate and reviews the result with your symptoms and other information. Tell the imaging team about implants or metal in the body before a scan."
            + GENERAL_LIMIT
        )
    if re.search(r"\b(?:frequent|recurrent|often|regular) headaches?\b|\bwhat can cause headaches?\b", text):
        return (
            "Frequent headaches have many possible causes, including tension, migraine, sleep disruption, dehydration, eye strain, stress, or other health issues. A headache diary can help a clinician understand the pattern. Seek urgent care for a sudden severe headache, a new headache after a head injury, or headache with weakness, confusion, fainting, fever with a stiff neck, or vision/speech changes."
            + GENERAL_LIMIT
        )
    if re.search(r"\bwhat (?:is|does) blood pressure\b", text):
        return (
            "Blood pressure is the force of blood against artery walls, recorded as two numbers: pressure during a heartbeat and between beats. A single reading does not by itself establish a diagnosis; interpretation depends on repeat measurements and clinical context."
            + GENERAL_LIMIT
        )
    if re.search(r"\bwhat (?:is|does) (?:an? )?ecg\b|\belectrocardiogram\b", text):
        return (
            "An ECG (electrocardiogram) records the heart's electrical activity using sensors on the skin. It can provide information about rate and rhythm at the time of the test, but a clinician interprets it alongside symptoms and other findings."
            + GENERAL_LIMIT
        )
    if re.search(r"\bwhat (?:is|does) cholesterol\b", text):
        return (
            "Cholesterol is a waxy substance the body uses to build cells and make some hormones. Blood tests measure different cholesterol-related lipids; a clinician considers the pattern and a person's overall health when discussing results."
            + GENERAL_LIMIT
        )
    if re.search(r"\bwhat (?:is|does) a biopsy\b", text):
        return (
            "A biopsy is a procedure in which a small tissue or cell sample is collected so a laboratory can examine it. The reason for the test, how it is done, and what a result means depend on the body area and clinical question; the ordering clinician can explain those specifics."
            + GENERAL_LIMIT
        )
    if re.search(r"\b(?:causes?|reason) for chest pain\b|\bwhat can cause chest pain\b", text):
        return (
            "Chest pain has many possible causes, including problems involving the heart, lungs, muscles, digestion, or anxiety; an online assistant cannot determine the cause. New, severe, persistent chest pain, especially with breathlessness, sweating, faintness, or pain spreading to the arm or jaw, needs urgent assessment. Call 112 if it may be an emergency."
            + GENERAL_LIMIT
        )
    if re.search(r"\bhow (?:do i|can i) (?:request|book) an appointment\b|\bappointment request\b", text):
        return (
            "Open Find doctors, choose a profile, and select a future local slot if one is listed. Submitting records a request in MediReach; it does not contact the doctor or confirm an appointment. You can review or cancel an eligible local request from Appointments."
        )
    if re.search(r"\b(?:how do i use|how does) medireach\b|\bwhere can i find (?:a )?(?:doctor|hospital)\b", text):
        return (
            "Use Find doctors to search by specialty and area, or Find hospitals to search by area and optional facility type. Mapped OpenStreetMap results are separate and not independently verified. The assistant can provide general information, and Call 112 is available for emergencies."
        )
    return None
