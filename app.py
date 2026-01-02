import streamlit as st
import docx
import json
import csv
import io
import re
from datetime import datetime
import google.generativeai as genai
import os
from typing import List, Dict, Any

# Page config
st.set_page_config(
    page_title="Test Case Generator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'test_case_groups' not in st.session_state:
    st.session_state.test_case_groups = []
if 'prd_file_name' not in st.session_state:
    st.session_state.prd_file_name = ''

# Categories
CATEGORIES = [
    'Positive',
    'Negative',
    'Edge Cases',
    'Boundary',
    'Integration',
    'Performance',
    'Security',
    'Usability',
]

PROMPT_TEMPLATE = """You are an expert QA engineer. Your task is to thoroughly analyze the following Product Requirements Document (PRD) and generate comprehensive, detailed test cases that cover ALL features, functionalities, and requirements mentioned in the document.

PRD Content:
{PRD_TEXT}

IMPORTANT INSTRUCTIONS:
1. Read the ENTIRE PRD carefully and identify ALL features, user stories, requirements, and functionalities
2. For EACH feature/requirement identified, generate multiple test cases across different categories
3. Ensure you cover every aspect mentioned in the PRD - nothing should be missed
4. Generate a MINIMUM of 8-12 test cases per category (not just 5)
5. Be thorough - if a feature has multiple scenarios, create test cases for each

Generate test cases for each of the following categories:
1. Positive - Test cases for valid inputs, happy paths, and expected successful behavior
2. Negative - Test cases for invalid inputs, error conditions, and failure scenarios
3. Edge Cases - Test cases for boundary conditions, unusual inputs, and corner cases
4. Boundary - Test cases for limit values, maximums, minimums, and thresholds
5. Integration - Test cases for component interactions, API integrations, and system integration
6. Performance - Test cases for load, stress, response time, and performance requirements
7. Security - Test cases for authentication, authorization, data protection, and security vulnerabilities
8. Usability - Test cases for user experience, interface usability, accessibility, and user workflows

For each test case, provide:
- A clear, descriptive title that identifies the specific feature/requirement being tested
- A detailed description explaining what is being tested and why
- Step-by-step test steps (be specific and detailed)
- Expected result (what should happen when the test passes)
- Priority (High for critical features, Medium for important features, Low for nice-to-have)

Return the response as a JSON array with the following structure:
[
  {{
    "category": "Positive",
    "testCases": [
      {{
        "title": "Test case title",
        "description": "Detailed description",
        "steps": ["Step 1", "Step 2", "Step 3"],
        "expectedResult": "What should happen",
        "priority": "High"
      }}
    ]
  }}
]

CRITICAL REQUIREMENTS:
- Generate MINIMUM 8-12 test cases per category (more if the PRD is complex)
- Cover EVERY feature and requirement mentioned in the PRD
- Ensure test cases are specific to the features described in the PRD
- Be comprehensive - don't miss any functionality
- Always return valid JSON only, no additional text or markdown formatting"""

def extract_text_from_docx(file) -> str:
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def generate_test_cases(prd_text: str) -> List[Dict[str, Any]]:
    """Generate test cases using Gemini API"""
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except:
        pass
    
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise Exception("GEMINI_API_KEY not found. Please enter your API key in the sidebar or set it as an environment variable.")
    
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise Exception(f"Failed to configure Gemini API: {str(e)}")
    
    # Try different models
    models_to_try = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-pro']
    
    prompt = PROMPT_TEMPLATE.replace("{PRD_TEXT}", prd_text)
    
    last_error = None
    for model_name in models_to_try:
        try:
            st.info(f"🔄 Trying model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            
            # Add generation config for better reliability
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini API")
            
            response_text = response.text
            st.info("✅ Response received, parsing JSON...")
            
            # Parse JSON from response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                test_cases = json.loads(json_match.group())
            else:
                # Try to find JSON in the response
                test_cases = json.loads(response_text)
            
            if not test_cases or not isinstance(test_cases, list):
                raise Exception("Invalid response format from AI")
            
            return test_cases
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ JSON parsing error with {model_name}, trying next model...")
            last_error = f"JSON parsing error: {str(e)}. Response preview: {response_text[:200] if 'response_text' in locals() else 'N/A'}"
            continue
        except Exception as e:
            st.warning(f"⚠️ Error with {model_name}: {str(e)[:100]}")
            last_error = e
            continue
    
    raise Exception(f"All Gemini models failed. Last error: {str(last_error)}")

def ensure_all_categories(test_case_groups: List[Dict]) -> List[Dict]:
    """Ensure all categories are present"""
    category_map = {group['category']: group for group in test_case_groups}
    
    # Add missing categories
    for category in CATEGORIES:
        if category not in category_map:
            category_map[category] = {
                'category': category,
                'testCases': []
            }
    
    # Add IDs to test cases
    result = []
    for category in CATEGORIES:
        group = category_map[category]
        for idx, tc in enumerate(group.get('testCases', [])):
            tc['id'] = f"{category}-{idx}-{int(datetime.now().timestamp() * 1000)}"
        result.append(group)
    
    return result

def export_to_json(test_case_groups: List[Dict]) -> str:
    """Export test cases to JSON"""
    return json.dumps(test_case_groups, indent=2)

def export_to_csv(test_case_groups: List[Dict]) -> str:
    """Export test cases to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Category', 'Title', 'Description', 'Steps', 'Expected Result', 'Priority'])
    
    # Data rows
    for group in test_case_groups:
        for tc in group.get('testCases', []):
            steps = ' | '.join(tc.get('steps', []))
            writer.writerow([
                group['category'],
                tc.get('title', ''),
                tc.get('description', ''),
                steps,
                tc.get('expectedResult', ''),
                tc.get('priority', 'Medium')
            ])
    
    return output.getvalue()

# Main UI
st.title("🧪 Test Case Generator")
st.markdown("Upload your PRD document and get comprehensive test cases generated by AI")

# Sidebar for API key configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        help="Get your free API key from https://makersuite.google.com/app/apikey",
        value=st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, 'secrets') else ""
    )
    
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
    
    st.markdown("---")
    st.markdown("### 📝 Instructions")
    st.markdown("""
    1. Upload a DOCX file containing your PRD
    2. Wait for AI to generate test cases
    3. Review and export test cases
    """)

# File upload
uploaded_file = st.file_uploader(
    "Upload PRD Document",
    type=['docx'],
    help="Only DOCX files are supported"
)

if uploaded_file is not None:
    if st.button("Generate Test Cases", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Extract text from DOCX
            status_text.text("📄 Step 1/3: Extracting text from DOCX file...")
            progress_bar.progress(10)
            
            prd_text = extract_text_from_docx(uploaded_file)
            
            if not prd_text or not prd_text.strip():
                st.error("The document appears to be empty or could not be read")
                st.stop()
            
            st.session_state.prd_file_name = uploaded_file.name
            progress_bar.progress(30)
            
            # Step 2: Generate test cases
            status_text.text("🤖 Step 2/3: Generating test cases with AI (this may take 30-60 seconds)...")
            progress_bar.progress(40)
            
            test_case_groups = generate_test_cases(prd_text)
            progress_bar.progress(80)
            
            # Step 3: Ensure all categories are present
            status_text.text("📋 Step 3/3: Organizing test cases by category...")
            test_case_groups = ensure_all_categories(test_case_groups)
            
            st.session_state.test_case_groups = test_case_groups
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            st.success("✅ Test cases generated successfully!")
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            error_msg = str(e)
            st.error(f"❌ Error: {error_msg}")
            
            # Provide helpful troubleshooting
            if "GEMINI_API_KEY" in error_msg:
                st.info("💡 **Tip:** Make sure you've entered your Gemini API key in the sidebar. Get a free key from: https://makersuite.google.com/app/apikey")
            elif "JSON" in error_msg or "parsing" in error_msg.lower():
                st.warning("⚠️ The AI response couldn't be parsed. This might be a temporary issue. Please try again.")
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                st.info("💡 **Tip:** You may have exceeded your API quota. Please check your Gemini API account or try again later.")
            else:
                st.info("💡 **Tip:** Check your internet connection and API key. If the problem persists, try uploading a smaller PRD file.")
            
            st.stop()

# Display test cases
if st.session_state.test_case_groups:
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📋 Generated Test Cases")
        if st.session_state.prd_file_name:
            st.caption(f"From: {st.session_state.prd_file_name}")
    
    with col2:
        st.markdown("### Export")
        json_data = export_to_json(st.session_state.test_case_groups)
        csv_data = export_to_csv(st.session_state.test_case_groups)
        
        st.download_button(
            "📥 JSON",
            json_data,
            file_name=f"test-cases-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
            mime="application/json"
        )
        
        st.download_button(
            "📥 CSV",
            csv_data,
            file_name=f"test-cases-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Display test cases by category
    for group in st.session_state.test_case_groups:
        with st.expander(f"📁 {group['category']} ({len(group.get('testCases', []))} test cases)", expanded=True):
            test_cases = group.get('testCases', [])
            
            if not test_cases:
                st.info("No test cases generated for this category")
            else:
                for idx, tc in enumerate(test_cases, 1):
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.subheader(f"{idx}. {tc.get('title', 'Untitled')}")
                        with col2:
                            priority = tc.get('priority', 'Medium')
                            priority_color = {
                                'High': '🔴',
                                'Medium': '🟡',
                                'Low': '🟢'
                            }.get(priority, '⚪')
                            st.markdown(f"**{priority_color} {priority}**")
                        
                        st.markdown(f"**Description:** {tc.get('description', 'N/A')}")
                        
                        st.markdown("**Test Steps:**")
                        steps = tc.get('steps', [])
                        for step_idx, step in enumerate(steps, 1):
                            st.markdown(f"{step_idx}. {step}")
                        
                        st.markdown(f"**Expected Result:** {tc.get('expectedResult', 'N/A')}")
                        st.divider()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Powered by Google Gemini AI | Free tier available</p>
</div>
""", unsafe_allow_html=True)
