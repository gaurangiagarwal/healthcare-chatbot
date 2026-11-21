"""Educational rule-based replies; never diagnose or prescribe."""
EMERGENCY_TERMS = ("chest pain", "can't breathe", "cannot breathe", "difficulty breathing", "unconscious", "severe bleeding", "stroke", "suicidal")
TOPICS = {
    "fever": "For a fever, rest, drink fluids, and monitor how you feel. Seek medical advice if it is high, persistent, worsening, or concerning. How long have you had it?",
    "cough": "For a cough, fluids and rest may help. Avoid smoke and seek care for breathing difficulty, blood, worsening symptoms, or a cough that persists. How long has it been present?",
    "headache": "For a mild headache, rest, hydration, and a quiet environment may help. Sudden severe headache, confusion, weakness, or vision changes need urgent medical attention. When did it start?",
    "stomach": "Stomach discomfort has many possible causes. Sip fluids and note where and when it hurts. Severe or worsening pain, fainting, persistent vomiting, or blood needs urgent medical care. How long has it been present?",
    "sore throat": "Warm fluids and rest may soothe a sore throat. Seek care if you have trouble breathing or swallowing, a high fever, or symptoms that persist. How long have you had it?",
}
def reply(message):
    text = message.lower()
    if any(term in text for term in EMERGENCY_TERMS):
        return "This may be an emergency. Contact your local emergency number or go to the nearest emergency department now. Do not wait for a chatbot response."
    for key, response in TOPICS.items():
        if key in text: return response
    if any(word in text for word in ("prevent", "prevention", "healthy")):
        return "General wellness includes regular sleep, balanced meals, movement, and preventive checkups. A clinician can tailor advice to your needs."
    if any(word in text for word in ("hello", "hi", "help")):
        return "Hello! Tell me what general health information you are looking for. I can share safe next steps for fever, cough, headache, stomach pain, or sore throat."
    return "I don't have reliable guidance for that question. Please contact a qualified healthcare professional. I can help with general information about fever, cough, headache, stomach pain, or sore throat."
