"""
Milestone PDF Extractor - Reads CDC milestone checklists from PDF
Extracts developmental milestones for ages 3 months to 60 months
"""

import os
import re
from typing import Dict, List, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False
        logger.warning("PyPDF not available - PDF milestone extraction will be disabled")


class MilestonePDFExtractor:
    """Extract and search developmental milestones from CDC PDF"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.milestones_data = {}
        self.is_loaded = False
        
        if PDF_AVAILABLE and os.path.exists(pdf_path):
            self._load_pdf()
        else:
            if not PDF_AVAILABLE:
                logger.warning("PyPDF not available for milestone PDF extraction")
            elif not os.path.exists(pdf_path):
                logger.warning(f"Milestone PDF not found at: {pdf_path}")
    
    def _load_pdf(self):
        """Load and parse the PDF file"""
        try:
            reader = PdfReader(self.pdf_path)
            text = ""
            
            # Extract text from all pages
            for page_num, page in enumerate(reader.pages):
                try:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page.extract_text() or ""
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
            
            # Parse the extracted text
            self._parse_milestone_text(text)
            self.is_loaded = True
            logger.info(f"CDC Milestone PDF loaded successfully with {len(self.milestones_data)} age groups")
            
        except Exception as e:
            logger.error(f"Error loading milestone PDF from {self.pdf_path}: {e}")
            self.is_loaded = False
    
    def _parse_milestone_text(self, text: str):
        """
        Parse milestone text and organize by age groups.
        CDC PDF format: "Your baby at X months" OR "Your child at X years"
        Separates milestones into Motor, Cognitive, and Language categories.
        """
        # Map text to consistent age in months
        age_mapping = {
            '2 months': 2, '2 month': 2,
            '4 months': 4, '4 month': 4,
            '6 months': 6, '6 month': 6,
            '9 months': 9, '9 month': 9,
            '12 months': 12, '12 month': 12,
            '15 months': 15, '15 month': 15,
            '18 months': 18, '18 month': 18,
            '30 months': 30, '30 month': 30,
            '2 years': 24, '2 year': 24,
            '3 years': 36, '3 year': 36,
            '4 years': 48, '4 year': 48,
            '5 years': 60, '5 year': 60,
        }
        
        # Split by "Your baby at" or "Your child at" to isolate each age group
        sections = []
        current_age = None
        current_milestones = ""
        
        # Find all section headers
        import re as regex
        header_pattern = r'Your (?:baby|child) at (\d+)\s+(month|year)s?\s*\*?'
        
        for match in regex.finditer(header_pattern, text, regex.IGNORECASE):
            age_str = match.group(1)
            unit = match.group(2).lower()
            
            # Calculate age in months
            age_value = int(age_str)
            if unit.startswith('year'):
                age_months = age_value * 12
            else:
                age_months = age_value
            
            # Get the text between this header and the next
            start_pos = match.end()
            # Find the next header or end of text
            next_match = regex.search(header_pattern, text[start_pos:], regex.IGNORECASE)
            if next_match:
                end_pos = start_pos + next_match.start()
                section_text = text[start_pos:end_pos]
            else:
                section_text = text[start_pos:]
            
            sections.append((age_months, section_text))
        
        # Process each section and extract milestones by category
        for age_months, section_text in sections:
            # Categorize milestones by keywords
            motor_milestones = []
            cognitive_milestones = []
            language_milestones = []
            social_milestones = []
            
            # Keywords for categorization
            motor_keywords = [
                'roll', 'sit', 'crawl', 'stand', 'walk', 'run', 'jump', 'climb',
                'kick', 'throw', 'hold', 'reach', 'grasp', 'balance', 'pedal',
                'lift', 'pull', 'push', 'arm', 'leg', 'muscle', 'movement',
                'physical', 'develops'
            ]
            cognitive_keywords = [
                'look', 'watch', 'point', 'find', 'understand', 'sort', 'play',
                'pretend', 'help', 'follow', 'object perm', 'puzzle', 'match',
                'learn', 'think', 'problem', 'solve', 'remember', 'count',
                'learning', 'cognitive', 'explore'
            ]
            language_keywords = [
                'coo', 'babble', 'laugh', 'smile', 'word', 'say', 'speak', 'talk',
                'sing', 'name', 'listen', 'call', 'sound', 'voice', 'language',
                'communication', 'understand word'
            ]
            social_keywords = [
                'smile', 'laugh', 'happy', 'social', 'emotional', 'interact',
                'friendly', 'play', 'peek', 'familiar', 'stranger', 'shy',
                'fear', 'affection', 'attention', 'respond'
            ]
            
            # Extract individual milestones (lines starting with •, ◦, or -)
            lines = section_text.split('\n')
            for line in lines:
                line_clean = line.strip()
                if not line_clean or len(line_clean) < 5:
                    continue
                
                # Remove bullet points and markers
                line_clean = regex.sub(r'^[\s•◦\-\*□✓\d.]+\s*', '', line_clean)
                line_clean = regex.sub(r'[\t\s]+', ' ', line_clean).strip()
                
                if not line_clean or len(line_clean) < 3:
                    continue
                
                # Skip metadata/instructions
                if any(skip in line_clean.lower() for skip in [
                    'important thing', 'share with doctor', 'concerned',
                    'cdc.gov', 'learn the sign', 'act early', '1-800',
                    'talk with your', 'see a doctor', 'professional', 'screening'
                ]):
                    continue
                
                # Categorize by keywords
                line_lower = line_clean.lower()
                
                if any(kw in line_lower for kw in motor_keywords):
                    motor_milestones.append(line_clean)
                elif any(kw in line_lower for kw in language_keywords):
                    language_milestones.append(line_clean)
                elif any(kw in line_lower for kw in cognitive_keywords):
                    cognitive_milestones.append(line_clean)
                elif any(kw in line_lower for kw in social_keywords):
                    social_milestones.append(line_clean)
                else:
                    # If no category matched, default to social/emotional
                    social_milestones.append(line_clean)
            
            # Store the milestones for this age group
            if any([motor_milestones, cognitive_milestones, language_milestones, social_milestones]):
                self.milestones_data[age_months] = {
                    'age_months': age_months,
                    'age_label': self._get_age_label(age_months),
                    'motor': self._clean_milestones(motor_milestones),
                    'cognitive': self._clean_milestones(cognitive_milestones),
                    'language': self._clean_milestones(language_milestones),
                    'social': self._clean_milestones(social_milestones),
                }
    
    def _clean_milestones(self, milestones: List[str]) -> List[str]:
        """Clean and deduplicate milestone text, removing instructions and metadata"""
        cleaned = []
        seen = set()
        
        for m in milestones:
            # Remove bullets, numbers, checkboxes, and various unicode symbols
            m = re.sub(r'^[\s•\-\*□✓\d.◦]+\s*', '', m)
            # Remove tabs and excessive whitespace
            m = re.sub(r'[\t\s]+', ' ', m)
            # Remove trailing commas and parentheses
            m = re.sub(r'[,;)]+\s*$', '', m)
            m = m.strip()
            
            # Skip empty or too short
            if len(m) < 5:
                continue
            
            # Skip lines starting with lowercase (likely continuation from previous line)
            if m and m[0].islower():
                continue
            
            m_lower = m.lower()
            
            # Skip instruction/metadata lines
            skip_patterns = [
                # Headers and metadata
                'milestones matter', 'important thing', 'share with doctor',
                'cdc.gov', 'learn the sign', 'act early', '1-800', 'call your',
                'contact your', 'talk to a', 'see a doctor', 'professional',
                'screening', 'date', "baby's name", "child's name",
                'reached by age', 'well-child visit', 'evaluation',
                
                # Instructions starting with common verbs
                'help your', 'talk with your', 'read with', 'ask him', 'ask her',
                'let your', 'respond', 'provide', 'allow', 'encourage your',
                'use positive', 'give attention', 'teach', 'show him',
                'put', 'join', 'listen', 'play with', 'take time',
                'limit screen', 'read stories', 'talk to your',
                
                # Category headers and descriptions
                'communication milestones', 'physical development',
                'social/emotional', 'cognitive milestones',
                'social milestones', 'movement/physical',
                'learning, thinking', '(learning,', 'what most',
                'by this age', 'other important', 'milestones)',
                '(for', '(ages', '(like',
                
                # Garbled or incomplete fragments
                "ou can't", ", such as", 'the playground',
                'worship,', 'library,', 'park or',
                'pre-school', 'public elementary', ' and ',
            ]
            
            if any(pattern in m_lower for pattern in skip_patterns):
                continue
            
            # Skip lines that end with incomplete markers
            if m.endswith(' at') or m.endswith(' like') or m.endswith(' or or') or m.endswith(' to'):
                continue
            
            # Skip lines that are too long (likely full instructions)
            if len(m) > 120:
                continue
            
            # Skip duplicates
            if m_lower not in seen:
                cleaned.append(m)
                seen.add(m_lower)
        
        return cleaned
    
    def _get_age_label(self, age_months: int) -> str:
        """Get human-readable age label"""
        if age_months < 12:
            return f"{age_months} months"
        else:
            years = age_months / 12
            if years == int(years):
                return f"{int(years)} years"
            else:
                return f"{age_months} months"
    
    def search_milestones(self, age_months: Optional[int] = None, 
                         milestone_type: Optional[str] = None) -> Dict:
        """
        Search for milestones by age and/or type
        
        Args:
            age_months: Patient age in months
            milestone_type: 'motor', 'cognitive', 'language', or None for all
            
        Returns:
            Dict with formatted milestone data
        """
        if not self.is_loaded:
            return {"results": [], "count": 0, "source": "PDF"}
        
        results = []
        
        # If age specified, find closest match
        if age_months is not None:
            # Find closest age in the database
            available_ages = sorted(self.milestones_data.keys())
            closest_age = min(available_ages, key=lambda x: abs(x - age_months))
            
            if abs(closest_age - age_months) > 12:
                # Age is too far from available data
                logger.info(f"Age {age_months} months is beyond available milestone data (max: {max(available_ages)} months)")
                return {
                    "results": [],
                    "count": 0,
                    "note": f"Milestone data available for ages 3-60 months. Patient age ({age_months} months) is outside this range.",
                    "source": "PDF"
                }
            
            age_data = self.milestones_data[closest_age]
            
            # Format the result
            if milestone_type:
                milestone_type_lower = milestone_type.lower()
                if milestone_type_lower in age_data:
                    milestones = age_data[milestone_type_lower]
                    if milestones:
                        results.append({
                            "age_months": closest_age,
                            "age_label": age_data['age_label'],
                            "type": milestone_type_lower.capitalize(),
                            "milestones": milestones
                        })
            else:
                # Return all types
                for mtype in ['motor', 'cognitive', 'language']:
                    milestones = age_data.get(mtype, [])
                    if milestones:
                        results.append({
                            "age_months": closest_age,
                            "age_label": age_data['age_label'],
                            "type": mtype.capitalize(),
                            "milestones": milestones
                        })
        else:
            # No specific age - return all available milestones
            for age_months in sorted(self.milestones_data.keys()):
                age_data = self.milestones_data[age_months]
                for mtype in ['motor', 'cognitive', 'language']:
                    milestones = age_data.get(mtype, [])
                    if milestones:
                        results.append({
                            "age_months": age_months,
                            "age_label": age_data['age_label'],
                            "type": mtype.capitalize(),
                            "milestones": milestones
                        })
        
        return {
            "results": results,
            "count": len(results),
            "source": "CDC Milestone Checklist PDF"
        }
    
    def get_available_ages(self) -> List[int]:
        """Get list of available age months in the database"""
        return sorted(self.milestones_data.keys())
