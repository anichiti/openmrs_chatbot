"""Central Warning Engine - Role-Specific Clinical Alerts"""
from utils.logger import setup_logger
logger = setup_logger(__name__)

def warning_allergy_match(allergy_info, drug_name, role="doctor"):
    allergy_type = allergy_info.get("allergy_type", "unknown allergen")
    severity = allergy_info.get("severity", "unknown").upper()
    if role.lower() == "doctor":
        return ("ALERT: CONTRAINDICATION\nPatient has documented {} allergy to {}.\nProposed medication {} may contain cross-reactive ingredient.\nReview before administration.".format(severity, allergy_type, drug_name))
    else:
        return ("ALLERGY ALERT\nYou have a {} allergy to {}.\nThe medication {} may contain a related substance.\nPlease consult your doctor or pharmacist.".format(severity.lower(), allergy_type, drug_name))

def warning_abnormal_vital(vital_name, value, normal_range, role="doctor"):
    if role.lower() == "doctor":
        return ("ABNORMAL VITAL SIGN\n{}: {} (normal: {})\nPatient requires clinical assessment.\nConsider appropriate interventions.".format(vital_name, value, normal_range))
    else:
        vital_lower = vital_name.lower()
        return ("VITAL SIGN ALERT\nYour {} is {} (normal range: {}).\nThis reading is outside the expected range.\nPlease contact your doctor.".format(vital_lower, value, normal_range))

def warning_abnormal_lab(lab_name, value, normal_range, role="doctor"):
    if role.lower() == "doctor":
        return ("ABNORMAL LAB VALUE\n{}: {} (normal: {})\nResult is outside reference range.\nRecommend clinical correlation and follow-up testing.".format(lab_name, value, normal_range))
    else:
        lab_lower = lab_name.lower()
        return ("LAB ALERT\nYour {} result is {} (normal range: {}).\nThis result is outside the expected range.\nPlease consult your doctor.".format(lab_lower, value, normal_range))

def warning_milestone_not_recorded(milestone_name, expected_age, role="doctor"):
    if role.lower() == "doctor":
        return ("DEVELOPMENTAL CONCERN\nMilestone {} (expected: {}) has not been documented.\nRecommend formal developmental screening and assessment.\nConsider specialist referral if indicated.".format(milestone_name, expected_age))
    else:
        return ("DEVELOPMENT ALERT\nYour child has not achieved the {} milestone.\nThis is typically expected by age {}.\nPlease discuss with your pediatrician.".format(milestone_name, expected_age))

def warning_vaccine_not_recorded(vaccine_name, age_due, role="doctor"):
    if role.lower() == "doctor":
        return ("IMMUNIZATION ALERT\nVaccine {} (due at: {}) is not recorded in immunization history.\nVerify vaccine status and update records.\nIf overdue, schedule vaccination.".format(vaccine_name, age_due))
    else:
        return ("VACCINE ALERT\nYour child is due for the {} vaccine (typically given at {}).\nThere is no record of this vaccine being given yet.\nPlease contact your health provider to schedule.".format(vaccine_name, age_due))

def generate_warning(warning_type, context, role="doctor"):
    warning_type = warning_type.lower().strip()
    if warning_type == "allergy":
        return warning_allergy_match(context.get("allergy_info", {}), context.get("drug_name", "medication"), role)
    elif warning_type == "vital":
        return warning_abnormal_vital(context.get("vital_name", "Vital Sign"), context.get("value", "N/A"), context.get("normal_range", "unknown"), role)
    elif warning_type == "lab":
        return warning_abnormal_lab(context.get("lab_name", "Lab Test"), context.get("value", "N/A"), context.get("normal_range", "unknown"), role)
    elif warning_type == "milestone":
        return warning_milestone_not_recorded(context.get("milestone_name", "Milestone"), context.get("expected_age", "unknown"), role)
    elif warning_type == "vaccine":
        return warning_vaccine_not_recorded(context.get("vaccine_name", "Vaccine"), context.get("age_due", "unknown"), role)
    else:
        logger.warning("Unknown warning type: {}".format(warning_type))
        return ""

