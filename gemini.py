import google.generativeai as gemini
import os 
import dotenv
import json
dotenv.load_dotenv()

gemini.configure(os.getenv('API_KEY') or "") 
def response_LLM(temperature, humidity, moisture, soilType, soilPH, rainfall, season):
    #Few-shorts template for Gemini-2.5-Pro
    """
    Calls the Gemini model with the provided sensor data and returns the response.
    """
    try:
        system_prompt = "You are an expert agronomist and horticulture consultant. Your task is to analyze the provided environmental conditions and suggest 3-5 suitable plants that will thrive with minimal environmental adjustment. Respond ONLY with a JSON array that strictly adheres to the provided schema. Do not include any other text, markdown, or explanation."
        prompt = f"""
        
        Analyze the following sensor and contextual data to suggest the best suitable plants:
        - Temperature: {temperature} °C
        - Humidity: {humidity} %
        - Soil Moisture: {moisture}
        - Soil Type: {soilType}
        - Soil pH: {soilPH}
        - Rainfall: {rainfall}
        - Season: {season}

        Criteria for Suggestion:
        The suggested plants must maximize the probability of successful growth, requiring minimal adjustment to the existing conditions. Focus on plants that thrive within the *measured* ranges, not just tolerate them. The suggestions should be practical and commonly available.

        Output Format:
        "A list of 3 to 5 plants suitable for the given conditions.
        required: ["rank", "suggestedPlantName", "keyEnvironmentalNeeds", "rationaleForSuitability"]
        Example:
        [
            {
                "rank": 1,
                "suggestedPlantName": "Tomato",
                "keyEnvironmentalNeeds": {
                    "temperatureRange": "20-25°C",
                    "humidityRange": "50-70%",
                    "soilType": "Loamy",
                    "soilPHRange": "6.0-6.8",
                    "rainfall": "Moderate"
                },
                "rationaleForSuitability": "Tomatoes thrive in warm temperatures and moderate humidity, which align well with the provided conditions. The loamy soil type and slightly acidic pH are ideal for nutrient uptake."
            },
            {
                "rank": 2,
                "suggestedPlantName": "Basil",
                "keyEnvironmentalNeeds": {
                    "temperatureRange": "18-30°C",
                    "humidityRange": "40-60%",
                    "soilType": "Well-drained",
                    "soilPHRange": "5.5-6.5",
                    "rainfall": "Light to Moderate"
                },
                "rationaleForSuitability": "Basil prefers warm climates and can tolerate a range of humidity levels. The well-drained soil and slightly acidic pH make it a good match for the current environment."
            }
        ]
        """

        response = gemini.chat.completions.create(
            model="gemini-2.5-pro",
            system_instructions=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_output_tokens=500
        )

        return json.loads(response.choices[0].message.content.strip('///').strip())

    except Exception as e:
        print(f"Error calling Gemini model: {e}")
        return {"error": str(e)}