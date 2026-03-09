"""
Pediatric Dose Calculator
Calculates medication doses for children based on weight and age
"""


class DoseCalculator:
    """
    Calculate pediatric medication doses
    Supports: mg/kg, mg/kg ranges, frequency calculations, max dose checks
    """

    # -------------------------------------------------
    # AGE GROUP DETECTION
    # -------------------------------------------------
    def get_age_group(self, age_years):
        """Classify patient into age group based on age in years"""
        if age_years < (28 / 365):   # 28 days
            return "neonate"

        elif age_years < 1:
            return "infant"

        elif age_years < 12:
            return "child"

        else:
            return "adolescent"

    # -------------------------------------------------
    # GET BEST MATCHING DOSE BLOCK FROM JSON
    # -------------------------------------------------
    def get_dose_block(self, drug, age_group):
        """Get dose information for specific age group from drug data"""
        dose_data = drug.get("dose", {})

        # Try exact match first
        if age_group in dose_data:
            return dose_data[age_group]

        # Fallback for older JSON formats
        if "infant_child" in dose_data:
            return dose_data["infant_child"]

        return None

    # -------------------------------------------------
    # CALCULATE DOSE
    # -------------------------------------------------
    def calculate_dose(self, weight_kg, age_years, drug):
        """
        Calculate medication dose for pediatric patient
        
        Args:
            weight_kg: Patient weight in kilograms
            age_years: Patient age in years
            drug: Drug data dictionary with dose information
        
        Returns:
            Dictionary with dose calculation results
        """
        age_group = self.get_age_group(age_years)

        dose_block = self.get_dose_block(drug, age_group)

        if not dose_block:
            return {
                "error": "No dosing data found for age group"
            }

        result = {
            "age_group": age_group,
            "weight_kg": weight_kg
        }

        # -------------------------------------------------
        # CASE 1 — Fixed mg/kg
        # -------------------------------------------------
        if "mg_per_kg" in dose_block:

            dose = weight_kg * dose_block["mg_per_kg"]

            # Apply max single dose cap
            if "max_single_dose_mg" in dose_block:
                dose = min(dose, dose_block["max_single_dose_mg"])

            result["dose_per_admin_mg"] = round(dose, 2)

        # -------------------------------------------------
        # CASE 2 — mg/kg Range
        # -------------------------------------------------
        elif "mg_per_kg_range" in dose_block:

            low = weight_kg * dose_block["mg_per_kg_range"][0]
            high = weight_kg * dose_block["mg_per_kg_range"][1]

            result["dose_range_mg"] = {
                "low": round(low, 2),
                "high": round(high, 2)
            }

        else:
            return {
                "error": "Dose format not supported"
            }

        # -------------------------------------------------
        # FREQUENCY HANDLING
        # -------------------------------------------------
        if "frequency_hours_range" in dose_block:

            freq_low = dose_block["frequency_hours_range"][0]
            freq_high = dose_block["frequency_hours_range"][1]

            result["frequency"] = f"Every {freq_low}-{freq_high} hours"

            # Estimate doses per day
            result["estimated_doses_per_day"] = {
                "min": round(24 / freq_high),
                "max": round(24 / freq_low)
            }

        if "frequency_per_day_range" in dose_block:

            result["estimated_doses_per_day"] = {
                "min": dose_block["frequency_per_day_range"][0],
                "max": dose_block["frequency_per_day_range"][1]
            }

        # -------------------------------------------------
        # DAILY DOSE CHECK
        # -------------------------------------------------
        if "max_daily_dose_mg" in dose_block and "dose_per_admin_mg" in result:

            max_daily = dose_block["max_daily_dose_mg"]
            per_dose = result["dose_per_admin_mg"]

            est_doses = result.get("estimated_doses_per_day", {}).get("max", 1)

            total_daily = per_dose * est_doses

            result["estimated_daily_total_mg"] = round(total_daily, 2)

            if total_daily > max_daily:
                result["daily_dose_warning"] = (
                    f"Estimated daily dose exceeds max daily dose ({max_daily} mg)"
                )

        # -------------------------------------------------
        # MAX DAILY MG/KG CHECK
        # -------------------------------------------------
        if "max_daily_mg_per_kg" in dose_block:

            result["max_daily_total_mg"] = (
                weight_kg * dose_block["max_daily_mg_per_kg"]
            )

        return result
