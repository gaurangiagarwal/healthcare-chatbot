from django.test import SimpleTestCase

from .chatbot import (
    TEMPERATURE_PLAUSIBLE_RANGES,
    detect_symptoms,
    parse_duration,
    parse_temperature,
    parse_temperature_unit,
    process_message,
)


class TemperatureFollowupRegressionTests(SimpleTestCase):
    def test_fever_and_headache_are_both_retained(self):
        response, state = process_message("I have fever and headache", {})
        self.assertEqual(state["symptoms"], ["fever", "headache"])
        self.assertIn("How long", response)

    def test_duration_and_punctuated_temperature_without_unit(self):
        _, state = process_message("I have fever and headache", {})
        response, state = process_message("since yesterday,the temperature is 101", state)
        self.assertEqual(parse_duration("since yesterday"), "since yesterday")
        self.assertEqual(state["duration"], "since yesterday")
        self.assertEqual(state["reported_temperature"], 101.0)
        self.assertIsNone(state["temperature_unit"])
        self.assertIn("Fahrenheit or Celsius", response)

    def test_explicit_fahrenheit_formats(self):
        degree = chr(176)
        for phrase in (
            f"101{degree}F", "101 F", "101 degree Fahrenheit", "temperature is 101 F",
            "my temperature is 100.5 F", "yes 101 degree Fahrenheit",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_temperature(phrase)["unit"], "F")
        self.assertEqual(parse_temperature(f"101{degree}F")["celsius"], 38.3)

    def test_explicit_celsius_formats_and_unrealistic_value(self):
        self.assertIn(101.0, range(int(TEMPERATURE_PLAUSIBLE_RANGES["F"][0]), int(TEMPERATURE_PLAUSIBLE_RANGES["F"][1]) + 1))
        self.assertFalse(TEMPERATURE_PLAUSIBLE_RANGES["C"][0] <= 101.0 <= TEMPERATURE_PLAUSIBLE_RANGES["C"][1])
        degree = chr(176)
        for phrase in (f"38{degree}C", "38 degree Celsius", "yes 101 degree Celsius"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_temperature(phrase)["unit"], "C")
        impossible = parse_temperature("101 degree Celsius")
        self.assertFalse(impossible["plausible"])
        self.assertNotIn("fahrenheit", impossible)

    def test_unit_is_combined_from_the_next_turn(self):
        _, state = process_message("I have fever and headache", {})
        response, state = process_message("Since yesterday, temperature 101", state)
        self.assertIn("Fahrenheit or Celsius", response)
        response, state = process_message("Fahrenheit", state)
        self.assertIn("101°F is approximately 38.3°C", response)
        self.assertEqual(state["temperature_unit"], "F")
        self.assertEqual(state["pending_information"], ["other_symptoms"])

    def test_yes_to_temperature_question_asks_for_the_reading(self):
        _, state = process_message("I have fever", {})
        response, state = process_message("Since yesterday", state)
        self.assertEqual(state["last_question"], "temperature")
        response, state = process_message("Yes", state)
        self.assertIn("What temperature reading", response)
        self.assertEqual(state["last_question"], "temperature_reading")

    def test_unrealistic_temperature_gets_exact_safety_guidance(self):
        _, state = process_message("I have fever and headache", {})
        _, state = process_message("Since yesterday, the temperature is 101", state)
        response, state = process_message("yes 101 degree Celsius", state)
        self.assertIn(
            "A body temperature of 101°C is not a plausible human body-temperature reading.",
            response,
        )
        self.assertIn("check your thermometer", response)
        self.assertIn("seek urgent medical care", response)
        self.assertIn("temperature_implausible", state["emergency_warning_signs"])

    def test_repeated_implausible_reading_does_not_replay_the_same_answer(self):
        _, state = process_message("I have fever", {})
        first, state = process_message("Since yesterday, temperature is 101 degree Celsius", state)
        repeated, state = process_message("I genuinely have 101 degree Celsius temp", state)
        self.assertNotEqual(repeated, first)
        self.assertIn("reading displayed", repeated)
        self.assertIn("urgent medical care", repeated)

    def test_doctor_contact_request_after_implausible_reading_gets_a_useful_answer(self):
        _, state = process_message("I have fever", {})
        _, state = process_message("Since yesterday, temperature is 101 degree Celsius", state)
        response, state = process_message("give me doctor name and number i should contact to", state)
        self.assertIn("Find a doctor", response)
        self.assertIn("phone number", response)
        self.assertNotIn("101°C is not a plausible", response)

    def test_answered_information_is_not_asked_again(self):
        _, state = process_message("I have fever and headache", {})
        _, state = process_message("Since yesterday, 101", state)
        response, state = process_message("Fahrenheit", state)
        self.assertNotIn("How long", response)
        self.assertNotIn("Have you measured", response)
        self.assertEqual(state["last_question"], "other_symptoms")

    def test_new_symptom_is_added_during_the_same_conversation(self):
        _, state = process_message("I have fever and headache", {})
        response, state = process_message("Since yesterday", state)
        response, state = process_message("I also have a sore throat", state)
        self.assertEqual(state["symptoms"], ["fever", "headache", "sore throat"])
        self.assertNotIn("How long", response)

    def test_negative_cough_does_not_add_cough(self):
        self.assertEqual(detect_symptoms("I don't have a cough"), [])

    def test_unit_parser_does_not_guess(self):
        self.assertIsNone(parse_temperature_unit("yes"))
        self.assertEqual(parse_temperature_unit("Fahrenheit"), "F")

